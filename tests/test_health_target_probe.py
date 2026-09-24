"""F1/F2: health probes must observe the TARGET (not OffensIA's own execution
engine), keyed by target so degradation on one target never contaminates
another."""
import importlib

import pytest


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFENSIA_BASE", str(tmp_path))
    import offensia.core.config as cfg
    importlib.reload(cfg)
    import offensia.core.server as s
    importlib.reload(s)
    s._HEALTH_PROBES.clear()
    return s


def test_probe_target_used_not_adapter_health(srv, monkeypatch):
    """_probe_sample must call health.probe_target(target), never the
    adapter's own execution-engine health() check."""
    calls = []
    monkeypatch.setattr(srv.health_mod, "probe_target",
                        lambda target, **kw: calls.append(target) or
                        {"ok": True, "status": 200, "latency_ms": 5})

    def boom_health():
        raise AssertionError("adapter.health() must not be used for target liveness")

    monkeypatch.setattr(srv.execp, "health", boom_health, raising=False)
    sample = srv._probe_sample("example.com")
    assert calls == ["example.com"]
    assert sample["ok"] is True


def test_health_probe_keyed_by_target_not_capability(srv):
    p1 = srv._health_probe_for("a.example.com")
    p2 = srv._health_probe_for("b.example.com")
    p1_again = srv._health_probe_for("a.example.com")
    assert p1 is p1_again
    assert p1 is not p2
    assert set(srv._HEALTH_PROBES) == {"a.example.com", "b.example.com"}


def test_target_down_across_jobs_halts_second_job_run_job(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "LAB")
    monkeypatch.setattr(srv, "_run_via_registry",
                        lambda job, budget: {"ok": True, "raw": "HTTP/1.1 200 OK body"})
    samples = iter([
        {"ok": True, "status": 200, "latency_ms": 10},
        {"ok": False, "status": 500, "latency_ms": None},
    ])
    monkeypatch.setattr(srv.health_mod, "probe_target",
                        lambda target, **kw: next(samples))
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["http://example.com"], "targets": ["example.com"]}
    first = srv.offensia_run_job(job, assessment="a")
    assert first["status"] == "completed"
    second = srv.offensia_run_job(job, assessment="a")
    assert second["status"] == "interrupted"


def test_unmeasurable_target_does_not_halt(srv, monkeypatch):
    """An exception measuring health (DNS, conn refused, timeout) is
    UNMEASURABLE, not down — must never halt a run."""
    srv.offensia_scope_add("example.com", "LAB")
    monkeypatch.setattr(srv, "_run_via_registry",
                        lambda job, budget: {"ok": True, "raw": "HTTP/1.1 200 OK body"})

    def boom(target, **kw):
        raise ConnectionError("dns failure")

    monkeypatch.setattr(srv.health_mod, "probe_target", boom)
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["http://example.com"], "targets": ["example.com"]}
    first = srv.offensia_run_job(job, assessment="a")
    second = srv.offensia_run_job(job, assessment="a")
    assert first["status"] == "completed"
    assert second["status"] == "completed"


def test_port_scan_uses_target_keyed_health_probe(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "LAB")
    monkeypatch.setattr(srv, "_run_via_registry",
                        lambda job, budget: {"ok": True, "raw": "PORT 80/tcp open"})
    monkeypatch.setattr(srv.health_mod, "probe_target",
                        lambda target, **kw: {"ok": True, "status": 200, "latency_ms": 5})
    out = srv.offensia_port_scan("example.com", assessment="a")
    assert out["status"] == "completed"
    assert "example.com" in srv._HEALTH_PROBES
