from offensia.core.oracles import base


def test_registry_round_trip():
    class Dummy(base.Oracle):
        name = "dummy"
        def evaluate(self, ctx): return base.inconclusive("x")
    base.register(Dummy())
    assert "dummy" in base.available()
    assert isinstance(base.get("dummy"), Dummy)


def test_block_page_detected():
    assert base.looks_like_block_page("Access Denied — Request blocked by WAF")
    assert not base.looks_like_block_page("{'user':'b','email':'b@x'}")


def test_is_error_on_failed_result():
    assert base.is_error({"ok": False, "error": "Timeout"})
    assert not base.is_error({"ok": True, "raw": "hello"})


def test_verdict_helpers():
    v = base.confirmed("got it", "high", nc_used=True)
    assert v.reproduced and v.verdict == "confirmed" and v.negative_control_used
    assert base.disproven("nope").verdict == "disproven"
    assert base.inconclusive("meh").verdict == "inconclusive"
