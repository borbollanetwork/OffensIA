# tests/test_oracle_authorization.py
from offensia.core.oracles import base
from offensia.core.oracles.authorization import AuthorizationOracle

ORACLE = AuthorizationOracle()


def _r(body, ok=True): return {"ok": ok, "raw": body}


def test_confirms_cross_identity_access():
    ctx = base.OracleContext(
        target="t", identity={"marker": "ssn=999-b"},
        candidate=_r("HTTP/1.1 200 OK\n\n{'owner':'B', ssn=999-b}"),
        negative_control=_r("HTTP/1.1 403 Forbidden\n\naccess denied"))
    v = ORACLE.evaluate(ctx)
    assert v.verdict == "confirmed" and v.negative_control_used


def test_no_marker_means_not_confirmed():
    ctx = base.OracleContext(
        target="t", identity={"marker": "ssn=999-b"},
        candidate=_r("HTTP/1.1 200 OK\n\n{}"),
        negative_control=_r("HTTP/1.1 403 Forbidden"))
    assert ORACLE.evaluate(ctx).verdict != "confirmed"


def test_control_also_grants_is_inconclusive():
    # if the boundary grants access even in the control, nothing is proven
    ctx = base.OracleContext(
        target="t", identity={"marker": "ssn=999-b"},
        candidate=_r("HTTP/1.1 200 OK\n\nssn=999-b"),
        negative_control=_r("HTTP/1.1 200 OK\n\nssn=999-b"))
    assert ORACLE.evaluate(ctx).verdict == "inconclusive"
