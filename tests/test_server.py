import importlib

import pytest


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFENSIA_BASE", str(tmp_path))
    import offensia.core.config as cfg
    importlib.reload(cfg)
    import offensia.core.server as s
    importlib.reload(s)
    return s


def test_out_of_scope_refused_and_logged(srv, monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(srv.reconp, "fetch",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {})
    out = srv.offensia_recon_crawl("evil.com")
    assert out["error"] == "OUT_OF_SCOPE" and called["n"] == 0
    # deny was recorded to the ledger
    events = srv.ledger_mod.read_all(srv._adir("default"))
    assert any(e["kind"] == "scope_denied" for e in events)


def test_recon_stores_evidence_and_ledger(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "CONTRACT-1")
    monkeypatch.setattr(srv.reconp, "fetch",
                        lambda target, mode="md": srv.reconp.result(
                            True, target, "recon", raw="# real page content here", summary="recon:md"))
    out = srv.offensia_recon_crawl("https://example.com")
    assert out["ok"] and out["evidence_id"] and out["ledger_ref"]
    assert "OFFENSIA_UNTRUSTED_DATA" in out["preview"]
    assert "model_view" not in out
    assert out["digest"]["kind"] == "recon"
    # full raw still resolvable via evidence store, not dumped into the result
    full = srv.ev_mod.load(srv._adir("default"),
                           srv._sha_for(srv._adir("default"), out["evidence_id"]))
    assert full.decode() == "# real page content here"
    v = srv.offensia_ledger_verify()["integrity"]
    assert v["ok"] is True


def test_full_finding_validation_flow(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "CONTRACT-1")
    # recon to produce evidence
    monkeypatch.setattr(srv.reconp, "fetch",
                        lambda target, mode="md": srv.reconp.result(
                            True, target, "recon", raw="baseline body content xyz", summary="r"))
    rec = srv.offensia_recon_crawl("https://example.com")
    ev_id = rec["evidence_id"]
    fc = srv.offensia_finding_create("example.com", "IDOR", ev_id, status="SUSPECTED")
    assert fc["ok"]

    # oracle-driven validation: attacker identity reproduces, victim (negative
    # control) does not -> authorization oracle confirms with a negative
    # control, satisfying VALIDATED's promotion requirements.
    def fake_run_job(adir, job, **kw):
        role = job.identity_context.get("role")
        body = ("HTTP/1.1 200 OK\n\nssn=999-b" if role == "attacker"
                else "HTTP/1.1 403 Forbidden")
        ref = srv.ev_mod.store(adir, body, kind=job.capability)
        return {"status": "completed", "evidence_id": ref.evidence_id,
                "ledger_ref": "l", "ok": True}

    monkeypatch.setattr(srv._executor, "run_job", fake_run_job)
    experiment = {
        "capability": "web.http_probe", "tool_id": "generic_http",
        "candidate_argv": ["https://example.com/orders/B", "-X", "GET"],
        "negative_argv": ["https://example.com/orders/B", "-X", "GET"],
        "expected_oracle": "authorization",
        "identity": {"marker": "ssn=999-b"},
        "candidate_identity": {"role": "attacker"},
        "negative_identity": {"role": "victim_denied"},
    }
    res = srv.offensia_validate_finding("example.com", fc["finding_id"],
                                        experiment=experiment, target_status="VALIDATED")
    assert res["ok"] and res["status"] == "VALIDATED"


def test_validation_refuses_without_controls(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "CONTRACT-1")
    monkeypatch.setattr(srv.reconp, "fetch",
                        lambda target, mode="md": srv.reconp.result(
                            True, target, "recon", raw="content body here long enough", summary="r"))
    rec = srv.offensia_recon_crawl("https://example.com")
    fc = srv.offensia_finding_create("example.com", "SQLi", rec["evidence_id"], status="SUSPECTED")

    # no negative_argv supplied -> authorization oracle can't discriminate a
    # boundary (requires a negative control) and returns inconclusive, so the
    # finding stays unpromoted regardless of target_status.
    def fake_run_job(adir, job, **kw):
        ref = srv.ev_mod.store(adir, "HTTP/1.1 200 OK\n\nssn=999-b", kind=job.capability)
        return {"status": "completed", "evidence_id": ref.evidence_id,
                "ledger_ref": "l", "ok": True}

    monkeypatch.setattr(srv._executor, "run_job", fake_run_job)
    experiment = {
        "capability": "web.http_probe", "tool_id": "generic_http",
        "candidate_argv": ["https://example.com/orders/B", "-X", "GET"],
        "expected_oracle": "authorization",
        "identity": {"marker": "ssn=999-b"},
    }
    res = srv.offensia_validate_finding("example.com", fc["finding_id"],
                                        experiment=experiment, target_status="VALIDATED")
    assert res["ok"] is False and res["error"] == "NOT_PROMOTED"
