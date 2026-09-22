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
              "escalates_to", "authenticates_as", "reaches", "pivots_to"}


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


def paths(assessment_dir: Path, src: str, dst: str, max_depth: int = 8) -> list[list[str]]:
    """Enumerate simple directed paths src->dst (DFS, bounded)."""
    with _db(assessment_dir) as conn:
        edges = conn.execute("SELECT src, dst FROM edges").fetchall()
    adj: dict[str, list[str]] = {}
    for s, d in edges:
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
