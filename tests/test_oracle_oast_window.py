# tests/test_oracle_oast_window.py
from offensia.core.oracles import base
from offensia.core.oracles.oast import OASTOracle

ORACLE = OASTOracle()


def test_no_callback_open_window_is_inconclusive():
    ctx = base.OracleContext(target="t", correlation_id="abc",
                             candidate={"ok": True, "raw": "", "oast_events": []},
                             oast_window_closed=False)
    assert ORACLE.evaluate(ctx).verdict == "inconclusive"


def test_no_callback_closed_window_is_disproven():
    ctx = base.OracleContext(target="t", correlation_id="abc",
                             candidate={"ok": True, "raw": "", "oast_events": []},
                             oast_window_closed=True)
    assert ORACLE.evaluate(ctx).verdict == "disproven"


def test_matching_callback_confirms_regardless_of_window():
    ctx = base.OracleContext(target="t", correlation_id="abc",
                             candidate={"ok": True, "raw": "", "oast_events": [{"correlation_id": "abc"}]},
                             oast_window_closed=False)
    assert ORACLE.evaluate(ctx).verdict == "confirmed"
