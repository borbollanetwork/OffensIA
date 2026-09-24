import pytest

from offensia.core import scope
from offensia.core.jobs import ExecutionJob, JobRejected, validate_job


def _scope(tmp_path):
    f = tmp_path / "scope.json"
    scope.add_entry("api.example.com", "LAB", f, "")
    return f


def test_read_only_http_get_allowed(tmp_path):
    f = _scope(tmp_path)
    ok = ExecutionJob(capability="web.http_probe", tool_id="generic_http",
                      argv=["https://api.example.com/x", "-X", "GET"], targets=["api.example.com"])
    validate_job(ok, f)   # no raise


def test_mutating_method_without_declared_effect_refused(tmp_path):
    f = _scope(tmp_path)
    bad = ExecutionJob(capability="web.http_probe", tool_id="generic_http",
                       argv=["https://api.example.com/x", "-X", "DELETE"], targets=["api.example.com"])
    with pytest.raises(JobRejected) as e:
        validate_job(bad, f)
    assert e.value.reason == "METHOD_EFFECT_MISMATCH"
