import pytest

from offensia.core import scope
from offensia.core.jobs import ExecutionJob, JobRejected, validate_job


def _scope(tmp_path):
    f = tmp_path / "scope.json"
    scope.add_entry("a.example", "LAB", f, "")
    return f


def test_capability_must_match_tool(tmp_path):
    f = _scope(tmp_path)
    bad = ExecutionJob(capability="web.http_probe", tool_id="nmap",  # nmap => network.port_scan
                       argv=["-sV"], targets=["a.example"])
    with pytest.raises(JobRejected) as e:
        validate_job(bad, f)
    assert e.value.reason == "CAPABILITY_MISMATCH"


def test_exactly_one_target(tmp_path):
    f = _scope(tmp_path)
    scope.add_entry("b.example", "LAB", f, "")
    multi = ExecutionJob(capability="network.port_scan", tool_id="nmap",
                         argv=["-sV"], targets=["a.example", "b.example"])
    with pytest.raises(JobRejected) as e:
        validate_job(multi, f)
    assert e.value.reason == "MULTI_TARGET"
