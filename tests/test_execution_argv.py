from offensia.adapters.execution import primary


def test_run_argv_posts_list_and_never_joins(monkeypatch):
    captured = {}

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"stdout": "ok", "return_code": 0, "success": True}

    def fake_post(url, json, timeout):
        captured["json"] = json
        return Resp()

    monkeypatch.setattr(primary.requests, "post", fake_post)
    res = primary.run_argv("host", ["nmap", "-sV", "host"])
    assert captured["json"]["argv"] == ["nmap", "-sV", "host"]
    assert "command" not in captured["json"]     # no shell string built
    assert res["ok"] is True


def test_argv_metachars_pass_as_inert_elements(monkeypatch):
    captured = {}

    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"stdout": "", "return_code": 0, "success": True}

    monkeypatch.setattr(primary.requests, "post",
                        lambda url, json, timeout: captured.setdefault("j", json) or Resp())
    primary.run_argv("host", ["nmap", "-sV; rm -rf /"])
    # the metachar payload is ONE argv element, not split or joined into a shell line
    assert captured["j"]["argv"] == ["nmap", "-sV; rm -rf /"]


def test_engine_execs_argv_without_shell(tmp_path, monkeypatch):
    # exec `printf %s SAFE` list-form; shell metachars in a later element stay inert
    from offensia.engines import reference_engine as eng
    out = eng._exec_argv(["printf", "%s", "A&&B"])   # helper the handler calls
    assert out["stdout"] == "A&&B"
    assert out["return_code"] == 0
    assert out["success"] is True
