import os

import pytest

from offensia.core import executor as ex


def test_lock_is_exclusive(tmp_path):
    lock = ex.acquire_lock(tmp_path)
    with pytest.raises(ex.LockHeld):
        ex.acquire_lock(tmp_path)
    lock.release()
    ex.acquire_lock(tmp_path).release()  # free again


def test_actions_are_monotonic(tmp_path):
    a = ex.record_action(tmp_path, ex.next_seq(tmp_path), "intent", {"job_id": "j1"})
    b = ex.record_action(tmp_path, ex.next_seq(tmp_path), "running", {"job_id": "j1"})
    assert a["seq"] == 1 and b["seq"] == 2
    assert [r["phase"] for r in ex.read_actions(tmp_path)] == ["intent", "running"]


def test_resume_marks_running_without_terminal_as_interrupted(tmp_path):
    ex.record_action(tmp_path, ex.next_seq(tmp_path), "intent", {"job_id": "j1"})
    ex.record_action(tmp_path, ex.next_seq(tmp_path), "running", {"job_id": "j1"})
    # no terminal event -> simulate crash
    interrupted = ex.resume(tmp_path)
    assert any(r["job_id"] == "j1" and r["phase"] == "interrupted" for r in interrupted)
    # a completed job is not touched
    ex.record_action(tmp_path, ex.next_seq(tmp_path), "intent", {"job_id": "j2"})
    ex.record_action(tmp_path, ex.next_seq(tmp_path), "completed", {"job_id": "j2"})
    assert all(r["job_id"] != "j2" for r in ex.resume(tmp_path))


def test_stale_lock_takeover(tmp_path):
    """Regression test: stale lock with dead PID should be taken over."""
    lock_file = tmp_path / ".lock"
    # Write a definitely-dead PID (use 99999 which is unlikely to be running)
    dead_pid = 99999
    lock_file.write_text(str(dead_pid))
    # Verify the dead PID is actually not alive
    assert not ex._pid_alive(dead_pid)
    # Should successfully take over the stale lock
    lock = ex.acquire_lock(tmp_path)
    assert lock is not None
    lock.release()


def test_live_lock_cannot_be_stolen(tmp_path):
    """Regression test: live lock with current process PID should not be stolen."""
    lock_file = tmp_path / ".lock"
    # Write the current process PID
    lock_file.write_text(str(os.getpid()))
    # Verify the current PID is alive
    assert ex._pid_alive(os.getpid())
    # Should raise LockHeld when trying to acquire
    with pytest.raises(ex.LockHeld):
        ex.acquire_lock(tmp_path)
