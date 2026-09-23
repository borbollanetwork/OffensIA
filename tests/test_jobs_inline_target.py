
import pytest

from offensia.core import scope
from offensia.core.jobs import ExecutionJob, JobRejected, validate_job


def _scope(tmp_path):
    f = tmp_path / "scope.json"
    scope.add_entry("api.example.com", "LAB", f, "")
    return f


def test_inline_url_host_must_be_in_scope(tmp_path):
    f = _scope(tmp_path)
    ok = ExecutionJob(capability="web.http_probe", tool_id="generic_http",
                      argv=["https://api.example.com/x", "-X", "GET"],
                      targets=["api.example.com"])
    validate_job(ok, f)   # in scope: no raise
    bad = ExecutionJob(capability="web.http_probe", tool_id="generic_http",
                       argv=["https://evil.example.net/x", "-X", "GET"],
                       targets=["api.example.com"])
    with pytest.raises(JobRejected) as e:
        validate_job(bad, f)
    assert e.value.reason == "OUT_OF_SCOPE_URL"
