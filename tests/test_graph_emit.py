from offensia.core import attack_graph as ag
from offensia.core import finding as fnd
from offensia.core import graph_emit


def _f(status):
    f = fnd.new_finding("t", "IDOR", status=fnd.SUSPECTED, evidence_refs=["e1"])
    f.requires = ["auth.session:userA"]
    f.grants = ["read:orders/B"]
    f.status = status
    return f


def test_validated_finding_emits_validated_edges(tmp_path):
    adir = tmp_path / "a"
    graph_emit.emit_from_finding(adir, _f(fnd.VALIDATED))
    es = ag.edges(adir)
    assert any(e["kind"] == "requires" and e["validation"] == "validated" for e in es)
    assert any(e["kind"] == "grants" and e["validation"] == "validated" for e in es)


def test_non_gated_finding_emits_unvalidated(tmp_path):
    adir = tmp_path / "b"
    graph_emit.emit_from_finding(adir, _f(fnd.SUSPECTED))
    assert all(e["validation"] == "unvalidated" for e in ag.edges(adir))


def test_emit_is_idempotent(tmp_path):
    adir = tmp_path / "c"
    f = _f(fnd.VALIDATED)
    graph_emit.emit_from_finding(adir, f)
    n1, e1 = len(ag_nodes(adir)), len(ag.edges(adir))
    graph_emit.emit_from_finding(adir, f)              # same finding again
    assert (len(ag_nodes(adir)), len(ag.edges(adir))) == (n1, e1)


def test_emit_never_raises_on_bad_shape(tmp_path):
    adir = tmp_path / "d"
    f = _f(fnd.VALIDATED)
    f.requires = [123, None]      # malformed tokens
    res = graph_emit.emit_from_finding(adir, f)   # must not raise
    assert isinstance(res, dict)


def ag_nodes(adir):
    import sqlite3
    with sqlite3.connect(adir / "attack_graph.sqlite") as c:
        return c.execute("SELECT id FROM nodes").fetchall()
