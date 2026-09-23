from offensia.core import executor
from offensia.core.budget import CapExceeded
from offensia.core.jobs import ExecutionJob


def _job(**kw):
    base = dict(capability="network.port_scan", tool_id="nmap", argv=["-sV"],
               targets=["scanme.example"], request_cap=5, rate=10, timeout=30)
    base.update(kw)
    return ExecutionJob(**base)


def _scope(tmp_path):
    f = tmp_path / "scope.json"
    from offensia.core import scope
    scope.add_entry("scanme.example", "LAB-1", f, "")
    return f


def test_runner_receives_two_args_job_and_budget(tmp_path):
    seen = {}
    def runner(job, budget):
        seen["has_budget"] = budget is not None
        return {"ok": True, "raw": "x"}
    res = executor.run_job(tmp_path / "a", _job(), scope_file=_scope(tmp_path),
                           runner=runner, health_probe=lambda t: True)
    assert seen["has_budget"] is True
    assert res["status"] == "completed"


def test_cap_exceeded_becomes_terminal_state(tmp_path):
    def runner(job, budget):
        raise CapExceeded("budget_exhausted")
    res = executor.run_job(tmp_path / "a", _job(), scope_file=_scope(tmp_path),
                           runner=runner, health_probe=lambda t: True)
    assert res["status"] == "budget_exhausted"
    # a cap state is terminal: resume() must NOT reclassify it as interrupted
    interrupted = executor.resume(tmp_path / "a")
    assert interrupted == []


def test_budget_snapshot_persisted(tmp_path):
    def runner(job, budget):
        budget.charge("scanme.example")
        return {"ok": True, "raw": "x"}
    executor.run_job(tmp_path / "a", _job(), scope_file=_scope(tmp_path),
                     runner=runner, health_probe=lambda t: True)
    import json
    ckpt = json.loads((tmp_path / "a" / "executor-checkpoint.json").read_text())
    assert ckpt["budget_consumed"]["requests_made"] == 1
