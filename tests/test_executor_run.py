import pytest

from offensia.core import executor as ex
from offensia.core.jobs import ExecutionJob


def _job(**kw):
    base = dict(capability="web.http_probe", tool_id="generic_http",
                argv=["http://example.com"], targets=["example.com"],
                risk_class="active", timeout=30, request_cap=10, rate=5)
    base.update(kw); return ExecutionJob(**base)


def _scope(tmp_path):
    f = tmp_path / "scope.allow"; f.write_text("example.com\n"); return f


def test_happy_path_records_and_stores(tmp_path):
    res = ex.run_job(tmp_path, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "HTTP/1.1 200 OK body"},
                     health_probe=lambda t: True)
    assert res["status"] == "completed" and res["evidence_id"]
    phases = [a["phase"] for a in ex.read_actions(tmp_path)]
    assert phases[0] == "intent" and phases[-1] == "completed"


def test_out_of_scope_job_refused_and_recorded(tmp_path):
    res = ex.run_job(tmp_path, _job(targets=["evil.com"]), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"})
    assert res["status"] == "refused"
    assert any(a["phase"] == "refused" for a in ex.read_actions(tmp_path))


def test_unhealthy_target_halts(tmp_path):
    res = ex.run_job(tmp_path, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"},
                     health_probe=lambda t: False)
    assert res["status"] == "interrupted"


def test_checkpoint_written(tmp_path):
    ex.run_job(tmp_path, _job(), scope_file=_scope(tmp_path),
               runner=lambda job, budget: {"ok": True, "raw": "ok"}, health_probe=lambda t: True)
    assert (tmp_path / "executor-checkpoint.json").exists()


def test_run_job_refused_when_lock_held(tmp_path):
    lock = ex.acquire_lock(tmp_path)
    called = []
    try:
        res = ex.run_job(tmp_path, _job(), scope_file=_scope(tmp_path),
                         runner=lambda job, budget: called.append(job) or {"ok": True, "raw": "x"},
                         health_probe=lambda t: True)
    finally:
        lock.release()
    assert res["status"] == "refused"
    assert res["reason"] == "BUSY"
    assert called == []


@pytest.mark.parametrize("kw", [
    dict(argv=123),
    dict(targets=123),
    dict(cleanup_plan=[123]),
])
def test_run_job_malformed_fields_return_structured_refusal(tmp_path, kw):
    res = ex.run_job(tmp_path, _job(**kw), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"},
                     health_probe=lambda t: True)
    assert res["status"] == "refused"
    assert res["reason"] == "BAD_JOB"
