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
                     runner=lambda job: {"ok": True, "raw": "HTTP/1.1 200 OK body"},
                     health_probe=lambda t: True)
    assert res["status"] == "completed" and res["evidence_id"]
    phases = [a["phase"] for a in ex.read_actions(tmp_path)]
    assert phases[0] == "intent" and phases[-1] == "completed"


def test_out_of_scope_job_refused_and_recorded(tmp_path):
    res = ex.run_job(tmp_path, _job(targets=["evil.com"]), scope_file=_scope(tmp_path),
                     runner=lambda job: {"ok": True, "raw": "x"})
    assert res["status"] == "refused"
    assert any(a["phase"] == "refused" for a in ex.read_actions(tmp_path))


def test_unhealthy_target_halts(tmp_path):
    res = ex.run_job(tmp_path, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job: {"ok": True, "raw": "x"},
                     health_probe=lambda t: False)
    assert res["status"] == "interrupted"


def test_checkpoint_written(tmp_path):
    ex.run_job(tmp_path, _job(), scope_file=_scope(tmp_path),
               runner=lambda job: {"ok": True, "raw": "ok"}, health_probe=lambda t: True)
    assert (tmp_path / "state.json").exists()
