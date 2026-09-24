import pytest

from offensia.adapters.execution import primary
from offensia.core.budget import Budget, CapExceeded


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


def test_run_argv_pre_charges_baseline_request_even_when_probe_count_is_one(monkeypatch):
    """F4: the reference engine always reports probe_count == 1, so the ONLY
    thing that charges the budget on a normal exec job is the pre-charge —
    the post-run reconcile (`cost=pc-1`) is a no-op when pc==1. Prove the
    pre-charge actually fires: a budget with request_cap=1 must be exhausted
    by a single run_argv call, and a second call under the SAME budget must
    raise CapExceeded('budget_exhausted')."""
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"stdout": "ok", "return_code": 0, "success": True,
                                "probe_count": 1}

    monkeypatch.setattr(primary.requests, "post",
                        lambda url, json, timeout: Resp())

    budget = Budget(request_cap=1, rate=1000, timeout=100, now=lambda: 0.0)
    res = primary.run_argv("host", ["nmap", "-sV", "host"], budget=budget)
    assert res["ok"] is True
    assert budget.requests_made == 1          # baseline request WAS charged

    with pytest.raises(CapExceeded) as exc:
        primary.run_argv("host", ["nmap", "-sV", "host"], budget=budget)
    assert exc.value.reason == "budget_exhausted"


def test_run_argv_reconciles_extra_probes_above_baseline(monkeypatch):
    """When the engine reports probe_count > 1 (multi-probe tools), the
    post-run reconcile charges the DELTA above the baseline pre-charge, so
    the total charged equals probe_count, not probe_count + 1."""
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"stdout": "ok", "return_code": 0, "success": True,
                                "probe_count": 3}

    monkeypatch.setattr(primary.requests, "post",
                        lambda url, json, timeout: Resp())

    budget = Budget(request_cap=10, rate=1000, timeout=100, now=lambda: 0.0)
    primary.run_argv("host", ["nmap", "-sV", "host"], budget=budget)
    assert budget.requests_made == 3
