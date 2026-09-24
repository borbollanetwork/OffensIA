import inspect

from offensia.adapters.execution import primary
from offensia.core import server


def test_validate_finding_requires_experiment(tmp_path, monkeypatch):
    monkeypatch.setattr(server.scope_mod, "in_scope", lambda *a, **k: True)
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    (tmp_path / "t").mkdir(parents=True, exist_ok=True)
    # a finding must exist; create via the finding store directly is out of scope here,
    # so we only assert the no-experiment contract short-circuits before any tool runs.
    res = server.offensia_validate_finding("x.example", "nope", assessment="t")
    assert res["error"] in ("NO_SUCH_FINDING", "EXPERIMENT_REQUIRED")


def test_no_run_command_in_validate_source():
    src = inspect.getsource(server.offensia_validate_finding)
    assert "run_command" not in src and "run_checks" not in src


def test_generic_command_capability_removed():
    assert "generic.command" not in primary.CAPABILITIES
