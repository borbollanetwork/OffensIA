from offensia.core import server


def _authorize(monkeypatch):
    monkeypatch.setattr(server.scope_mod, "in_scope", lambda *a, **k: True)


def _fake_assessment_dir(monkeypatch, tmp_path):
    # PATHS is a frozen dataclass instance; patch the bound method at the class
    # level so setattr succeeds and doesn't disturb the frozen instance.
    monkeypatch.setattr(type(server.PATHS), "assessment_dir",
                        lambda self, a: tmp_path / a)


def test_run_experiment_confirms_via_authorization_oracle(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    _fake_assessment_dir(monkeypatch, tmp_path)

    # deterministic runner: candidate leaks B's marker; control is denied
    def fake_run_job(adir, job, **kw):
        from offensia.core import evidence as ev
        role = job.identity_context.get("role")
        body = ("HTTP/1.1 200 OK\n\nssn=999-b" if role == "attacker"
                else "HTTP/1.1 403 Forbidden")
        ref = ev.store(adir, body, kind=job.capability)
        return {"status": "completed", "evidence_id": ref.evidence_id,
                "ledger_ref": "l", "ok": True}

    monkeypatch.setattr(server._executor, "run_job", fake_run_job)

    exp = {
        "capability": "web.http_probe", "tool_id": "generic_http",
        "target": "api.example.com",
        "candidate_argv": ["https://api.example.com/orders/B", "-X", "GET"],
        "negative_argv": ["https://api.example.com/orders/B", "-X", "GET"],
        "expected_oracle": "authorization",
        "identity": {"marker": "ssn=999-b"},
        # role tags let the fake runner differentiate; real jobs carry identity_context
        "candidate_identity": {"role": "attacker"},
        "negative_identity": {"role": "victim_denied"},
    }
    res = server.offensia_run_experiment(exp, assessment="t")
    assert res["ok"] and res["oracle_verdict"] == "confirmed"
    assert res["evidence_refs"]


def test_unknown_oracle_refused(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    _fake_assessment_dir(monkeypatch, tmp_path)
    res = server.offensia_run_experiment(
        {"capability": "web.http_probe", "tool_id": "generic_http",
         "target": "api.example.com", "candidate_argv": ["https://api.example.com/"],
         "expected_oracle": "nope"}, assessment="t")
    assert res["ok"] is False and res["error"] == "UNKNOWN_ORACLE"


def test_run_experiment_missing_candidate_argv_returns_bad_experiment(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    _fake_assessment_dir(monkeypatch, tmp_path)
    res = server.offensia_run_experiment(
        {"capability": "web.http_probe", "tool_id": "generic_http",
         "target": "api.example.com", "expected_oracle": "authorization"},
        assessment="t")
    assert res["ok"] is False and res["error"] == "BAD_EXPERIMENT"
    assert res["detail"] == "candidate_argv"


def test_run_experiment_oast_confirms_via_collector_callback(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    _fake_assessment_dir(monkeypatch, tmp_path)

    correlation_id = "corr-oast-1"

    def fake_run_job(adir, job, **kw):
        from offensia.core import evidence as ev
        from offensia.core.oracles.oast import OASTCollector
        # simulate an out-of-band callback landing while the candidate leg runs
        OASTCollector(adir).record(correlation_id, {"source": "candidate"})
        ref = ev.store(adir, "HTTP/1.1 200 OK\n\ntriggered", kind=job.capability)
        return {"status": "completed", "evidence_id": ref.evidence_id,
                "ledger_ref": "l", "ok": True}

    monkeypatch.setattr(server._executor, "run_job", fake_run_job)

    exp = {
        "capability": "web.http_probe", "tool_id": "generic_http",
        "target": "api.example.com",
        "candidate_argv": ["https://api.example.com/ssrf", "-X", "GET"],
        "expected_oracle": "oast",
        "correlation_id": correlation_id,
    }
    res = server.offensia_run_experiment(exp, assessment="t")
    assert res["ok"] and res["oracle_verdict"] == "confirmed"
    assert res["correlation_id"] == correlation_id


def test_run_experiment_oast_no_callback_not_confirmed(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    _fake_assessment_dir(monkeypatch, tmp_path)

    def fake_run_job(adir, job, **kw):
        from offensia.core import evidence as ev
        ref = ev.store(adir, "HTTP/1.1 200 OK\n\nno callback", kind=job.capability)
        return {"status": "completed", "evidence_id": ref.evidence_id,
                "ledger_ref": "l", "ok": True}

    monkeypatch.setattr(server._executor, "run_job", fake_run_job)

    exp = {
        "capability": "web.http_probe", "tool_id": "generic_http",
        "target": "api.example.com",
        "candidate_argv": ["https://api.example.com/safe", "-X", "GET"],
        "expected_oracle": "oast",
    }
    res = server.offensia_run_experiment(exp, assessment="t")
    assert res["ok"]
    assert res["oracle_verdict"] != "confirmed"
    # a correlation id is always minted, even without an explicit one
    assert res["correlation_id"]
