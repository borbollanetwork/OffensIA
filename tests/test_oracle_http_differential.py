# tests/test_oracle_http_differential.py
from offensia.core.oracles.http_differential import HTTPDifferentialOracle
from offensia.core.oracles import base

O = HTTPDifferentialOracle()


def _r(body, ok=True): return {"ok": ok, "raw": body}


def test_confirms_on_stable_difference_with_holding_control():
    ctx = base.OracleContext(
        target="t", baseline=_r("id=1 name=alice"),
        candidate=_r("id=1 name=alice SQL syntax error near"),
        negative_control=_r("id=1 name=alice"),
        attempts=[_r("id=1 name=alice SQL syntax error near")])
    v = O.evaluate(ctx)
    assert v.verdict == "confirmed" and v.confidence == "high" and v.negative_control_used


def test_block_page_candidate_never_confirms():
    ctx = base.OracleContext(
        target="t", baseline=_r("ok"),
        candidate=_r("Request blocked by WAF"),
        negative_control=_r("ok"))
    assert O.evaluate(ctx).verdict == "inconclusive"


def test_control_also_changed_is_not_confirmed():
    # both candidate and negative control differ from baseline -> boundary not shown
    ctx = base.OracleContext(
        target="t", baseline=_r("A"), candidate=_r("B"), negative_control=_r("C"))
    assert O.evaluate(ctx).verdict != "confirmed"


def test_missing_negative_control_is_inconclusive():
    ctx = base.OracleContext(target="t", baseline=_r("A"), candidate=_r("B"))
    assert O.evaluate(ctx).verdict == "inconclusive"
