"""Attack Graph (Evidence Plane) — local SQLite store of nodes and edges.

Used for reasoning about chaining and attack paths, not decoration. Every edge
carries evidence references, confidence, preconditions, and validation status.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

NODE_KINDS = {"asset", "identity", "privilege", "finding", "credential", "role",
              "session", "resource", "trust", "cloud_principal"}
EDGE_KINDS = {"can_access", "can_assume", "exposes", "leaks", "enables", "requires",
              "escalates_to", "authenticates_as", "reaches", "pivots_to", "grants"}


def _db(assessment_dir: Path) -> sqlite3.Connection:
    Path(assessment_dir).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(Path(assessment_dir) / "attack_graph.sqlite")
    conn.execute("CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT, "
                 "label TEXT, meta TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS edges (id TEXT PRIMARY KEY, src TEXT, "
                 "dst TEXT, kind TEXT, confidence TEXT, evidence TEXT, "
                 "preconditions TEXT, validation TEXT)")
    return conn


def add_node(assessment_dir: Path, kind: str, label: str, meta: dict | None = None) -> str:
    if kind not in NODE_KINDS:
        raise ValueError(f"unknown node kind {kind!r}")
    nid = uuid.uuid4().hex[:12]
    with _db(assessment_dir) as conn:
        conn.execute("INSERT INTO nodes VALUES (?,?,?,?)",
                     (nid, kind, label, json.dumps(meta or {})))
    return nid


def add_edge(assessment_dir: Path, src: str, dst: str, kind: str,
             confidence: str = "low", evidence: list | None = None,
             preconditions: list | None = None, validation: str = "unvalidated") -> str:
    if kind not in EDGE_KINDS:
        raise ValueError(f"unknown edge kind {kind!r}")
    eid = uuid.uuid4().hex[:12]
    with _db(assessment_dir) as conn:
        conn.execute("INSERT INTO edges VALUES (?,?,?,?,?,?,?,?)",
                     (eid, src, dst, kind, confidence,
                      json.dumps(evidence or []), json.dumps(preconditions or []),
                      validation))
    return eid


def neighbors(assessment_dir: Path, node_id: str) -> list[dict]:
    with _db(assessment_dir) as conn:
        rows = conn.execute("SELECT id, src, dst, kind, confidence, validation "
                            "FROM edges WHERE src=?", (node_id,)).fetchall()
    return [{"edge_id": r[0], "src": r[1], "dst": r[2], "kind": r[3],
             "confidence": r[4], "validation": r[5]} for r in rows]


def edges(assessment_dir: Path) -> list[dict]:
    with _db(assessment_dir) as conn:
        rows = conn.execute("SELECT id, src, dst, kind, confidence, validation "
                            "FROM edges").fetchall()
    return [{"edge_id": r[0], "src": r[1], "dst": r[2], "kind": r[3],
             "confidence": r[4], "validation": r[5]} for r in rows]


def paths(assessment_dir: Path, src: str, dst: str, max_depth: int = 8, *, validated_only: bool = False) -> list[list[str]]:
    """Enumerate simple directed paths src->dst (DFS, bounded)."""
    with _db(assessment_dir) as conn:
        rows = conn.execute("SELECT src, dst, validation FROM edges").fetchall()
    adj: dict[str, list[str]] = {}
    for s, d, val in rows:
        if validated_only and val != "validated":
            continue
        adj.setdefault(s, []).append(d)
    out: list[list[str]] = []

    def dfs(node, path):
        if len(path) > max_depth:
            return
        if node == dst:
            out.append(list(path))
            return
        for nxt in adj.get(node, []):
            if nxt not in path:
                dfs(nxt, path + [nxt])

    dfs(src, [src])
    return out


def set_crown_jewel(assessment_dir: Path, node_id: str, value: bool = True) -> None:
    """Mark (or unmark) a node as a crown jewel by setting meta['crown_jewel']."""
    with _db(assessment_dir) as conn:
        row = conn.execute("SELECT meta FROM nodes WHERE id=?", (node_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown node {node_id!r}")
        meta = json.loads(row[0]) if row[0] else {}
        meta["crown_jewel"] = value
        conn.execute("UPDATE nodes SET meta=? WHERE id=?", (json.dumps(meta), node_id))


def is_crown_jewel(assessment_dir: Path, node_id: str) -> bool:
    with _db(assessment_dir) as conn:
        row = conn.execute("SELECT meta FROM nodes WHERE id=?", (node_id,)).fetchone()
        if row is None:
            return False
        meta = json.loads(row[0]) if row[0] else {}
    return bool(meta.get("crown_jewel", False))


_CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def _conf_between(all_edges: list[dict], u: str, v: str) -> int:
    """Max-confidence weight among edges u->v; missing pair defaults to 1."""
    weights = [_CONFIDENCE_WEIGHT.get(e["confidence"], 1)
               for e in all_edges if e["src"] == u and e["dst"] == v]
    return max(weights) if weights else 1


def rank_paths(assessment_dir: Path, paths_in: list[list[str]]) -> list[dict]:
    """Score and rank candidate paths deterministically.

    Score = crown_jewel_bonus (10 if the path's dst node is a crown jewel else 0)
          + confidence_weight (min over consecutive-node edges of high=3/medium=2/low=1, missing=1)
          + shortness (1/len(path)).
    """
    all_edges = edges(assessment_dir)
    results: list[dict] = []
    for path in paths_in:
        reaches_cj = bool(path) and is_crown_jewel(assessment_dir, path[-1])
        crown_jewel_bonus = 10 if reaches_cj else 0
        if len(path) > 1:
            confidence_weight = min(
                _conf_between(all_edges, path[i], path[i + 1])
                for i in range(len(path) - 1)
            )
        else:
            confidence_weight = 1
        shortness = 1 / len(path) if path else 0
        score = crown_jewel_bonus + confidence_weight + shortness
        results.append({"path": path, "score": score, "reaches_crown_jewel": reaches_cj})
    results.sort(key=lambda r: (-r["score"], tuple(r["path"])))
    return results


def confirmed_paths(assessment_dir: Path, src: str, dst: str, max_depth: int = 8) -> list[list[str]]:
    """Paths using only validated edges."""
    return paths(assessment_dir, src, dst, max_depth, validated_only=True)


def candidate_paths(assessment_dir: Path, src: str, dst: str, max_depth: int = 8) -> list[list[str]]:
    """Paths using at least one non-validated edge."""
    conf = {tuple(p) for p in confirmed_paths(assessment_dir, src, dst, max_depth)}
    allp = paths(assessment_dir, src, dst, max_depth, validated_only=False)
    return [p for p in allp if tuple(p) not in conf]


def fix_ranking(assessment_dir: Path, confirmed_paths: list[list[str]]) -> list[dict]:
    """Rank remediation fixes by how many confirmed paths they would break.

    For each intermediate node appearing in the given confirmed paths, count how many
    of those paths it breaks if removed. Returns [{"node", "breaks"}] sorted by
    breaks desc then node id. Empty input → [].
    """
    counts: dict[str, int] = {}
    for p in confirmed_paths:
        # Count only intermediate nodes (indices 1 to len(p)-2, excluding endpoints)
        for i in range(1, len(p) - 1):
            node = p[i]
            counts[node] = counts.get(node, 0) + 1
    ranked: list[dict] = [{"node": n, "breaks": c} for n, c in counts.items()]
    ranked.sort(key=lambda r: (-int(r["breaks"]), r["node"]))
    return ranked
