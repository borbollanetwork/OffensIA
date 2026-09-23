from offensia.core import jobs as jobs_mod
from offensia.core import server


def _authorize(monkeypatch):
    # Patch scope_mod.in_scope (server.py's own outer gate) *and* jobs.in_scope
    # (the executor's inner gate, bound via `from ... import in_scope` so it
    # does not see the scope_mod patch) so scope is authorized deterministically
    # regardless of any real scope.allow file on disk.
    monkeypatch.setattr(server.scope_mod, "in_scope", lambda *a, **k: True)
    monkeypatch.setattr(jobs_mod, "in_scope", lambda *a, **k: True)


def test_run_job_result_carries_digest_not_raw(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    monkeypatch.setattr(server, "_run_via_registry",
                        lambda job, budget=None: {"ok": True,
                                                  "raw": "HTTP/1.1 200 OK\r\nServer: nginx\r\n\r\n<title>Hi</title>"})
    job = {"capability": "web.http_probe", "tool_id": "generic_http",
           "argv": ["https://x.example/"], "targets": ["x.example"]}
    out = server.offensia_run_job(job, assessment="t")
    assert out["status"] == "completed"
    assert "digest" in out and 200 in out["digest"]["status_codes"]
    assert "raw" not in out                        # raw not dumped into context
    assert out["evidence_id"]                       # raw resolvable via evidence


def test_recon_returns_preview_and_digest_not_full_body(tmp_path, monkeypatch):
    _authorize(monkeypatch)
    monkeypatch.setattr(type(server.PATHS), "assessment_dir", lambda self, a: tmp_path / a)
    big = "<title>Big</title>" + ("A" * 100000)
    monkeypatch.setattr(server, "_run_via_registry",
                        lambda job, budget=None: {"ok": True, "raw": big})
    out = server.offensia_recon_crawl("https://x.example/", assessment="t")
    assert out["ok"] and out["evidence_id"]
    assert len(out["preview"]) <= 4096              # bounded preview only
    assert "Big" in out["digest"]["titles"]
    assert "OFFENSIA_UNTRUSTED_DATA" in out["preview"]  # still fenced as untrusted
