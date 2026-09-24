from offensia.core import executor, scope
from offensia.core.executor import acquire_lock
from offensia.core.jobs import ExecutionJob


def _scope(tmp_path):
    f = tmp_path / "scope.json"
    scope.add_entry("a.example", "LAB", f, "")
    return f


def _job():
    return ExecutionJob(capability="network.port_scan", tool_id="nmap",
                        argv=["-sV"], targets=["a.example"])


def test_passed_lock_is_not_released_by_run_job(tmp_path):
    adir = tmp_path / "a"
    lock = acquire_lock(adir)
    executor.run_job(adir, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"},
                     health_probe=lambda t: True, lock=lock)
    # lock still held: a fresh run_job (own lock) must be refused BUSY
    res = executor.run_job(adir, _job(), scope_file=_scope(tmp_path),
                           runner=lambda job, budget: {"ok": True, "raw": "x"},
                           health_probe=lambda t: True)
    assert res["status"] == "refused" and res["reason"] == "BUSY"
    lock.release()


def test_own_lock_released_on_success(tmp_path):
    adir = tmp_path / "b"
    executor.run_job(adir, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"},
                     health_probe=lambda t: True)
    # released → a second call succeeds (not BUSY)
    res = executor.run_job(adir, _job(), scope_file=_scope(tmp_path),
                           runner=lambda job, budget: {"ok": True, "raw": "x"},
                           health_probe=lambda t: True)
    assert res["status"] == "completed"
