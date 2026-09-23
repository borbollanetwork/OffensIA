from offensia.core import server


def test_port_scan_goes_through_executor(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(server, "_executor",
                        _Spy(calls))  # see helper below
    monkeypatch.setattr(server.scope_mod, "in_scope", lambda *a, **k: True)
    server.offensia_port_scan("scanme.example", ports="80,443", assessment="t")
    assert calls["ran"] is True
    job = calls["job"]
    assert job.capability == "network.port_scan" and job.tool_id == "nmap"
    assert "-p" in job.argv and "80,443" in job.argv
    # host is NOT baked into argv by the tool; it is appended from the scoped target
    assert "scanme.example" not in job.argv


class _Spy:
    def __init__(self, calls): self.calls = calls
    def run_job(self, adir, job, **kw):
        self.calls["ran"] = True; self.calls["job"] = job
        return {"status": "completed", "evidence_id": "e", "ledger_ref": "l"}
