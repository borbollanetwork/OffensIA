from offensia.core import health


def test_degraded_on_ok_to_down():
    assert health.degraded({"ok": True, "latency_ms": 10}, {"ok": False, "latency_ms": None})
    assert not health.degraded({"ok": True, "latency_ms": 10}, {"ok": True, "latency_ms": 12})


def test_degraded_on_latency_blowup():
    assert health.degraded({"ok": True, "latency_ms": 20}, {"ok": True, "latency_ms": 200})


def test_probe_returns_false_after_degradation():
    samples = iter([{"ok": True, "status": 200, "latency_ms": 10},
                    {"ok": False, "status": None, "latency_ms": None}])
    probe = health.make_probe(lambda: next(samples))
    assert probe("t") is True     # baseline healthy
    assert probe("t") is False    # degraded → halt
