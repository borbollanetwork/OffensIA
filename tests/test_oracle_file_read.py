# tests/test_oracle_file_read.py
from offensia.core.oracles import base
from offensia.core.oracles.file_read import FileReadOracle

ORACLE = FileReadOracle()


def _r(body, ok=True): return {"ok": ok, "raw": body}


def test_confirms_when_canary_read_and_control_clean():
    ctx = base.OracleContext(
        target="t", canary="OFFENSIA-CANARY-7a1f",
        candidate=_r("root:x:0:0 ... OFFENSIA-CANARY-7a1f"),
        negative_control=_r("normal page, no canary"))
    v = ORACLE.evaluate(ctx)
    assert v.verdict == "confirmed" and v.negative_control_used


def test_no_canary_configured_is_inconclusive():
    ctx = base.OracleContext(target="t", candidate=_r("anything"))
    assert ORACLE.evaluate(ctx).verdict == "inconclusive"


def test_canary_also_in_control_is_inconclusive():
    ctx = base.OracleContext(
        target="t", canary="C",
        candidate=_r("...C..."), negative_control=_r("...C..."))
    assert ORACLE.evaluate(ctx).verdict == "inconclusive"
