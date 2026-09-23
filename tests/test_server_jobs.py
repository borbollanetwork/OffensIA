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
                        lambda job: {"ok": True, "raw": "HTTP/1.1 200 OK evidence body"})
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["http://example.com"], "targets": ["example.com"]}
    out = srv.offensia_run_job(job, assessment="a")
    assert out["status"] == "completed" and out["evidence_id"]
