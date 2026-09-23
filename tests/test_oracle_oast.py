# tests/test_oracle_oast.py
from offensia.core.oracles import base
from offensia.core.oracles.oast import OASTCollector, OASTOracle

ORACLE = OASTOracle()


def test_collector_correlates(tmp_path):
    c = OASTCollector(tmp_path)
    cid = c.token()
    c.record(cid, {"proto": "dns", "src": "1.2.3.4"})
    assert len(c.events(cid)) == 1
    assert c.events("other") == []


def test_oracle_confirms_on_matching_callback():
    ctx = base.OracleContext(
        target="t", correlation_id="abc",
        candidate={"ok": True, "raw": "", "oast_events": [{"correlation_id": "abc"}]})
    assert ORACLE.evaluate(ctx).verdict == "confirmed"


def test_no_callback_never_confirms():
    ctx = base.OracleContext(target="t", correlation_id="abc",
                             candidate={"ok": True, "raw": "", "oast_events": []})
    assert ORACLE.evaluate(ctx).verdict != "confirmed"


def test_unmatched_callback_never_confirms():
    ctx = base.OracleContext(
        target="t", correlation_id="abc",
        candidate={"ok": True, "raw": "", "oast_events": [{"correlation_id": "zzz"}]})
    assert ORACLE.evaluate(ctx).verdict != "confirmed"
