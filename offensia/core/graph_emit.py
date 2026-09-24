"""Finding -> attack-graph emitter. The finding lifecycle is the graph's single
writer: a promoted finding turns its requires/grants into nodes and edges whose
validation reflects the finding's state. Idempotent by finding_id; never raises."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from offensia.core import attack_graph as ag
from offensia.core import finding as fnd


def _find_node(adir: Path, kind: str, label: str) -> str | None:
    try:
        with sqlite3.connect(Path(adir) / "attack_graph.sqlite") as c:
            row = c.execute("SELECT id FROM nodes WHERE kind=? AND label=?",
                            (kind, label)).fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def _ensure_node(adir: Path, kind: str, label: str, meta: dict | None = None) -> str:
    existing = _find_node(adir, kind, label)
    return existing or ag.add_node(adir, kind, label, meta)


def _has_edge(adir: Path, src: str, dst: str, kind: str) -> bool:
    return any(e["src"] == src and e["dst"] == dst and e["kind"] == kind
               for e in ag.edges(adir))


def _count_nodes(adir: Path) -> int:
    try:
        with sqlite3.connect(Path(adir) / "attack_graph.sqlite") as c:
            return c.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    except sqlite3.Error:
        return 0


def emit_from_finding(assessment_dir, finding) -> dict:
    adir = Path(assessment_dir)
    try:
        validated = finding.status in fnd.VALIDATION_GATED
        val = "validated" if validated else "unvalidated"
        nodes_before = _count_nodes(adir)
        edges_before = len(ag.edges(adir))
        fnode = _ensure_node(adir, "finding", finding.finding_id,
                             {"title": finding.title, "status": finding.status})
        for req in list(getattr(finding, "requires", []) or []):
            if not isinstance(req, str):
                continue
            rn = _ensure_node(adir, "resource", req)
            if not _has_edge(adir, rn, fnode, "requires"):
                ag.add_edge(adir, rn, fnode, "requires", confidence=finding.confidence,
                            evidence=list(finding.evidence_refs), validation=val)
        for grant in list(getattr(finding, "grants", []) or []):
            if not isinstance(grant, str):
                continue
            gn = _ensure_node(adir, "resource", grant)
            if not _has_edge(adir, fnode, gn, "grants"):
                ag.add_edge(adir, fnode, gn, "grants", confidence=finding.confidence,
                            evidence=list(finding.evidence_refs), validation=val)
        return {"finding_node": fnode,
                "nodes_added": _count_nodes(adir) - nodes_before,
                "edges_added": len(ag.edges(adir)) - edges_before}
    except Exception:  # noqa: BLE001 — emitter never raises on malformed input
        return {"finding_node": None, "nodes_added": 0, "edges_added": 0}
