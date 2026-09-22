import requests

from offensia.adapters.base import bound_output, result
from offensia.adapters.execution import primary as execp
from offensia.adapters.recon import primary as reconp


def test_result_shape():
    r = result(True, "example.com", "exec")
    assert set(r) == {"ok", "target", "action", "raw", "summary", "ledger_ref",
                      "error", "bounded"}


def test_bound_output_truncates():
    text, bounded = bound_output("x" * 100, 10)
    assert bounded is True and len(text) == 10


def test_exec_success(monkeypatch):
    class R:
        def raise_for_status(self): pass
        def json(self): return {"success": True, "stdout": "80/tcp open", "return_code": 0}
    monkeypatch.setattr(requests, "post", lambda *a, **k: R())
    r = execp.run_command("example.com", "nmap example.com")
    assert r["ok"] and "80/tcp open" in r["raw"]


def test_exec_engine_down(monkeypatch):
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError("refused")))
    r = execp.run_command("example.com", "nmap example.com")
    assert r["ok"] is False and "refused" in r["error"]


def test_recon_markdown(monkeypatch):
    class R:
        def raise_for_status(self): pass
        def json(self): return {"markdown": "# Title\nbody"}
    monkeypatch.setattr(requests, "post", lambda *a, **k: R())
    r = reconp.fetch("https://example.com", "md")
    assert r["ok"] and "# Title" in r["raw"]


def test_recon_engine_down(monkeypatch):
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: (_ for _ in ()).throw(requests.Timeout("timeout")))
    r = reconp.fetch("https://example.com")
    assert r["ok"] is False and "timeout" in r["error"]
