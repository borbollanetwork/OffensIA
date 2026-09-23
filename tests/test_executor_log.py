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
