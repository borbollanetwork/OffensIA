from offensia.core import attack_graph as ag


def test_fix_ranking_prioritizes_the_shared_choke_point(tmp_path):
    adir = tmp_path / "a"
    # two confirmed paths sharing node X
    paths = [["A", "X", "C"], ["B", "X", "D"], ["A", "Y", "C"]]
    ranked = ag.fix_ranking(adir, paths)
    assert ranked[0]["node"] == "X" and ranked[0]["breaks"] == 2


def test_fix_ranking_empty(tmp_path):
    assert ag.fix_ranking(tmp_path / "b", []) == []
