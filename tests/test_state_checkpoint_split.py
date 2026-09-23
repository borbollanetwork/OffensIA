import json

from offensia.core import executor, scope, state
from offensia.core.config import get_paths
from offensia.core.jobs import ExecutionJob


def _scope(tmp_path):
    f = tmp_path / "scope.json"
    scope.add_entry("scanme.example", "LAB", f, "")
    return f


def _job():
    return ExecutionJob(capability="network.port_scan", tool_id="nmap",
                        argv=["-sV"], targets=["scanme.example"])


def test_run_job_does_not_clobber_assessment_state(tmp_path):
    base = str(tmp_path)
    st = state.create("eng-1", base=base)      # seeds discoveries/hypotheses/pending
    st["discoveries"]["hosts"].append("scanme.example")
    st["hypotheses"].append({"id": "H-1", "text": "test"})
    state.save("eng-1", st, base=base)
    adir = get_paths(base).assessment_dir("eng-1")

    executor.run_job(adir, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"},
                     health_probe=lambda t: True)

    reloaded = state.load("eng-1", base=base)
    assert reloaded["discoveries"]["hosts"] == ["scanme.example"]
    assert reloaded["hypotheses"] == [{"id": "H-1", "text": "test"}]


def test_checkpoint_written_to_its_own_file(tmp_path):
    base = str(tmp_path)
    state.create("eng-2", base=base)
    adir = get_paths(base).assessment_dir("eng-2")
    executor.run_job(adir, _job(), scope_file=_scope(tmp_path),
                     runner=lambda job, budget: {"ok": True, "raw": "x"},
                     health_probe=lambda t: True)
    ckpt = json.loads((adir / "executor-checkpoint.json").read_text())
    assert ckpt["last_status"] == "completed"
    assert ckpt["last_action_seq"] >= 1
    # terminal seq points at the terminal action, not the intent (seq 1)
    acts = executor.read_actions(adir)
    terminal = [a for a in acts if a["phase"] == "completed"][-1]
    assert ckpt["last_action_seq"] == terminal["seq"]


def test_load_tolerates_clobbered_legacy_state(tmp_path):
    base = str(tmp_path)
    adir = get_paths(base).assessment_dir("eng-3")
    adir.mkdir(parents=True, exist_ok=True)
    # simulate a state.json previously overwritten by the old executor checkpoint
    (adir / "state.json").write_text(json.dumps(
        {"last_job_id": "abc", "last_action_seq": 3, "last_status": "completed"}))
    st = state.load("eng-3", base=base)        # must not raise
    assert st is not None
    assert st["discoveries"] == {"technologies": [], "hosts": []}
    assert st["hypotheses"] == []
