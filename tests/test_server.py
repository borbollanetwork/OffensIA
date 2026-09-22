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
    assert "OFFENSIA_UNTRUSTED_DATA" in out["model_view"]
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
    # validation: attack reproduces, control does not
    monkeypatch.setattr(srv.execp, "run_command",
                        lambda t, c: {"ok": "attack" in c, "raw": c})
    checks = [{"name": "reproduction", "command": "attack req", "expect": "success"},
              {"name": "negative_control", "command": "benign req", "expect": "failure"}]
    res = srv.offensia_validate_finding("example.com", fc["finding_id"], checks,
                                        target_status="VALIDATED")
    assert res["ok"] and res["status"] == "VALIDATED"


def test_validation_refuses_without_controls(srv, monkeypatch):
    srv.offensia_scope_add("example.com", "CONTRACT-1")
    monkeypatch.setattr(srv.reconp, "fetch",
                        lambda target, mode="md": srv.reconp.result(
                            True, target, "recon", raw="content body here long enough", summary="r"))
    rec = srv.offensia_recon_crawl("https://example.com")
    fc = srv.offensia_finding_create("example.com", "SQLi", rec["evidence_id"], status="SUSPECTED")
    monkeypatch.setattr(srv.execp, "run_command", lambda t, c: {"ok": True, "raw": c})
    checks = [{"name": "reproduction", "command": "x", "expect": "success"}]
    res = srv.offensia_validate_finding("example.com", fc["finding_id"], checks,
                                        target_status="VALIDATED")
    assert res["ok"] is False and res["error"] == "NOT_PROMOTED"
