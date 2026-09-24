from offensia.core import attack_graph as ag


def _graph(tmp_path):
    adir = tmp_path / "a"
    a = ag.add_node(adir, "asset", "A")
    b = ag.add_node(adir, "asset", "B")
    c = ag.add_node(adir, "asset", "C")
    ag.add_edge(adir, a, b, "reaches", validation="validated")
    ag.add_edge(adir, b, c, "reaches", validation="validated")   # A->B->C fully validated
    ag.add_edge(adir, a, c, "reaches", validation="unvalidated")  # A->C shortcut, unvalidated
    return adir, a, b, c


def test_confirmed_paths_exclude_unvalidated_edges(tmp_path):
    adir, a, b, c = _graph(tmp_path)
    conf = ag.confirmed_paths(adir, a, c)
    assert [a, b, c] in conf
    assert [a, c] not in conf          # the unvalidated shortcut is NOT confirmed


def test_candidate_paths_include_the_unvalidated_route(tmp_path):
    adir, a, b, c = _graph(tmp_path)
    cand = ag.candidate_paths(adir, a, c)
    assert [a, c] in cand              # shortcut surfaces only as candidate
    assert [a, b, c] not in cand       # a fully-validated route is confirmed, not candidate


def test_grants_edge_kind_allowed(tmp_path):
    adir = tmp_path / "g"
    x = ag.add_node(adir, "finding", "F")
    y = ag.add_node(adir, "privilege", "P")
    ag.add_edge(adir, x, y, "grants", validation="validated")   # no raise
    assert any(e["kind"] == "grants" for e in ag.edges(adir))
