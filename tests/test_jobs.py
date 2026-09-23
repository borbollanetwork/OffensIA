import pytest

from offensia.core.jobs import ExecutionJob, JobRejected, validate_job


def _job(**kw):
    base = dict(capability="network.port_scan", tool_id="nmap",
                argv=["-sV"], targets=["example.com"], risk_class="active",
                expected_oracle="none", negative_control=None,
                request_cap=100, rate=10, timeout=60, cleanup_plan=[],
                evidence_contract=["stdout"], identity_context={}, preconditions=[])
    base.update(kw)
    return ExecutionJob(**base)


def _scope(tmp_path, *entries):
    f = tmp_path / "scope.allow"
    f.write_text("\n".join(entries) + "\n")
    return f


def test_valid_job_passes(tmp_path):
    validate_job(_job(), _scope(tmp_path, "example.com"))  # no raise


def test_out_of_scope_target_refuses_whole_job(tmp_path):
    j = _job(targets=["example.com", "evil.com"])
    with pytest.raises(JobRejected) as e:
        validate_job(j, _scope(tmp_path, "example.com"))
    assert e.value.reason == "OUT_OF_SCOPE"


def test_unknown_tool_refused(tmp_path):
    with pytest.raises(JobRejected) as e:
        validate_job(_job(tool_id="totally-unknown"), _scope(tmp_path, "example.com"))
    assert e.value.reason == "UNKNOWN_TOOL"


def test_argv_not_allowed_refused(tmp_path):
    with pytest.raises(JobRejected) as e:
        validate_job(_job(argv=["--evil-flag"]), _scope(tmp_path, "example.com"))
    assert e.value.reason == "ARGV_NOT_ALLOWED"


@pytest.mark.parametrize("risk", ["dos", "availability_impact", "crash"])
def test_availability_risk_class_refused(tmp_path, risk):
    with pytest.raises(JobRejected) as e:
        validate_job(_job(risk_class=risk), _scope(tmp_path, "example.com"))
    assert e.value.reason == "AVAILABILITY_GUARD"


@pytest.mark.parametrize("bad", [["--Flood"], ["-flood"], ["--stress"]])
def test_disruptive_argv_denylist(tmp_path, bad):
    # nmap allows -sV; add a disruptive token to trip the denylist
    with pytest.raises(JobRejected) as e:
        validate_job(_job(tool_id="generic_http", argv=bad + ["http://example.com"]),
                     _scope(tmp_path, "example.com"))
    assert e.value.reason in ("AVAILABILITY_GUARD", "ARGV_NOT_ALLOWED")


def test_destruction_guard_refuses_preexisting_delete(tmp_path):
    j = _job(tool_id="generic_http", argv=["http://example.com"],
             cleanup_plan=[{"action": "delete", "path": "/etc/passwd", "origin": "target"}])
    with pytest.raises(JobRejected) as e:
        validate_job(j, _scope(tmp_path, "example.com"))
    assert e.value.reason == "DESTRUCTION_GUARD"


def test_destruction_guard_allows_self_canary(tmp_path):
    j = _job(tool_id="generic_http", argv=["http://example.com"],
             cleanup_plan=[{"action": "delete", "path": "/tmp/offensia-canary", "origin": "offensia"}])
    validate_job(j, _scope(tmp_path, "example.com"))  # no raise
