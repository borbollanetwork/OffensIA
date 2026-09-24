# tests/test_oracle_http_diff_normalized.py
from offensia.core.oracles import base
from offensia.core.oracles.http_differential import HTTPDifferentialOracle, _norm

ORACLE = HTTPDifferentialOracle()


def _r(body, ok=True): return {"ok": ok, "raw": body}


def test_dynamic_token_only_difference_not_confirmed():
    b = _r("<input name=csrf value=AAAA1111> welcome bob")
    c = _r("<input name=csrf value=BBBB2222> welcome bob")   # only CSRF differs
    n = _r("<input name=csrf value=CCCC3333> welcome bob")
    ctx = base.OracleContext(target="t", baseline=b, candidate=c, negative_control=n)
    assert ORACLE.evaluate(ctx).verdict != "confirmed"


def test_real_semantic_difference_confirmed():
    b = _r("<input name=csrf value=AAAA1111> balance: 100")
    c = _r("<input name=csrf value=BBBB2222> balance: 100 SQL syntax error near")
    n = _r("<input name=csrf value=CCCC3333> balance: 100")
    ctx = base.OracleContext(target="t", baseline=b, candidate=c, negative_control=n,
                             attempts=[c])
    v = ORACLE.evaluate(ctx)
    assert v.verdict == "confirmed"


def test_repeated_value_noise_does_not_swallow_trailing_content():
    # regression: the csrf normalizer must bound the "value" indirection to
    # AT MOST ONE occurrence, so adversarial/repeated "value value value..."
    # noise cannot mask a genuine post-csrf divergence.
    assert "REALDIFF" in _norm("csrf value value value REALDIFF")

    b = _r("csrf value value value BASELINE_ONLY")
    c = _r("csrf value value value REALDIFF")
    n = _r("csrf value value value BASELINE_ONLY")
    ctx = base.OracleContext(target="t", baseline=b, candidate=c, negative_control=n,
                             attempts=[c])
    v = ORACLE.evaluate(ctx)
    assert v.verdict == "confirmed"
