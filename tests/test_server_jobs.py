import importlib

import pytest


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFENSIA_BASE", str(tmp_path))
    import offensia.core.config as cfg
    importlib.reload(cfg)
    import offensia.core.server as s
    importlib.reload(s)
    return s


def test_exec_tool_removed(srv):
    assert not hasattr(srv, "offensia_exec")


def test_run_job_out_of_scope_refused(srv):
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["http://evil.com"], "targets": ["evil.com"]}
    out = srv.offensia_run_job(job, assessment="a")
    assert out["status"] == "refused" and out["reason"] == "OUT_OF_SCOPE"


def test_run_job_in_scope_runs(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "LAB")
    # make the resolved adapter deterministic
    monkeypatch.setattr(srv, "_run_via_registry",
                        lambda job, budget: {"ok": True, "raw": "HTTP/1.1 200 OK evidence body"})
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["http://example.com"], "targets": ["example.com"]}
    out = srv.offensia_run_job(job, assessment="a")
    assert out["status"] == "completed" and out["evidence_id"]


def test_run_job_halts_on_degradation_observed_across_calls(srv, monkeypatch):
    """The probe must persist per-capability across jobs so a baseline set on
    job N is compared against job N+1's sample — otherwise degraded() never
    runs and health-aware halting is inert."""
    srv.offensia_scope_add("example.com", "LAB")
    monkeypatch.setattr(srv, "_run_via_registry",
                        lambda job, budget: {"ok": True, "raw": "HTTP/1.1 200 OK evidence body"})
    srv._HEALTH_PROBES.clear()
    samples = iter([
        {"ok": True, "status": 200, "latency_ms": 10},
        {"ok": False, "status": None, "latency_ms": None},
    ])
    monkeypatch.setattr(srv, "_probe_sample", lambda capability: next(samples))
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["http://example.com"], "targets": ["example.com"]}
    first = srv.offensia_run_job(job, assessment="a")
    assert first["status"] == "completed"
    second = srv.offensia_run_job(job, assessment="a")
    assert second["status"] == "interrupted"
