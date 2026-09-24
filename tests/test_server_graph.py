from offensia.core import attack_graph as ag
from offensia.core import server


def test_graph_paths_splits_confirmed_and_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    adir = tmp_path / "g"
    a = ag.add_node(adir, "asset", "A"); b = ag.add_node(adir, "asset", "B")
    c = ag.add_node(adir, "asset", "C")
    ag.add_edge(adir, a, b, "reaches", validation="validated")
    ag.add_edge(adir, b, c, "reaches", validation="validated")
    ag.add_edge(adir, a, c, "reaches", validation="unvalidated")
    out = server.offensia_graph_paths("g", src=a, dst=c)
    assert [a, b, c] in out["confirmed"]
    assert [a, c] in out["candidate"] and [a, c] not in out["confirmed"]


def test_graph_paths_requires_src_dst(tmp_path, monkeypatch):
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    out = server.offensia_graph_paths("g")
    assert out["ok"] is False and out["error"] == "SRC_DST_REQUIRED"


def test_graph_crown_jewel_marks_node(tmp_path, monkeypatch):
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    adir = tmp_path / "g2"
    a = ag.add_node(adir, "asset", "A")
    out = server.offensia_graph_crown_jewel(a, assessment="g2")
    assert out == {"ok": True}
    assert ag.is_crown_jewel(adir, a) is True


def test_graph_crown_jewel_unknown_node(tmp_path, monkeypatch):
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    out = server.offensia_graph_crown_jewel("nope", assessment="g3")
    assert out == {"ok": False, "error": "NO_SUCH_NODE"}
