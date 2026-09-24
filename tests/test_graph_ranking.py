from offensia.core import attack_graph as ag


def test_crown_jewel_flag_roundtrip(tmp_path):
    adir = tmp_path / "a"
    n = ag.add_node(adir, "asset", "crown")
    assert ag.is_crown_jewel(adir, n) is False
    ag.set_crown_jewel(adir, n)
    assert ag.is_crown_jewel(adir, n) is True


def test_rank_prioritizes_crown_jewel_and_confidence(tmp_path):
    adir = tmp_path / "b"
    a = ag.add_node(adir, "asset", "A")
    cj = ag.add_node(adir, "asset", "CROWN"); ag.set_crown_jewel(adir, cj)
    other = ag.add_node(adir, "asset", "OTHER")
    ag.add_edge(adir, a, cj, "reaches", confidence="high", validation="validated")
    ag.add_edge(adir, a, other, "reaches", confidence="low", validation="validated")
    ranked = ag.rank_paths(adir, [[a, other], [a, cj]])
    assert ranked[0]["path"] == [a, cj]           # crown-jewel path ranks first
    assert ranked[0]["reaches_crown_jewel"] is True


def test_rank_is_deterministic(tmp_path):
    adir = tmp_path / "c"
    a = ag.add_node(adir, "asset", "A"); b = ag.add_node(adir, "asset", "B")
    ag.add_edge(adir, a, b, "reaches", confidence="low", validation="validated")
    r1 = ag.rank_paths(adir, [[a, b]]); r2 = ag.rank_paths(adir, [[a, b]])
    assert r1 == r2
