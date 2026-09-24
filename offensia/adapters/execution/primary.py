"""Execution adapter (Execution Plane).

Satisfies active capabilities (port scan, HTTP probe, generic command) by talking
to a local deterministic tool-execution engine over HTTP. Output is bounded and
normalized. The concrete engine is declared in deps/engines.yaml and reached only
through this adapter, so upstream naming never leaks upward.
"""
from __future__ import annotations

import requests

from offensia.adapters.base import bound_output, result
from offensia.core.config import settings

PROVIDER_KEY = "execution_primary"
CAPABILITIES = ("network.port_scan", "web.http_probe")


def run_command(target: str, command: str, use_cache: bool = True) -> dict:
    s = settings()
    try:
        resp = requests.post(  # nosec B113 — timeout is set dynamically below
            f"{s['execution_url']}/api/command",
            json={"command": command, "use_cache": use_cache},
            timeout=s["http_timeout"],
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — must not crash the MCP layer
        return result(False, target, "exec", error=f"{type(exc).__name__}: {exc}")
    raw, bounded = bound_output(str(data.get("stdout", "")), s["http_max_bytes"])
    # ok reflects COMMAND success (return_code 0 / engine success), not HTTP
    # transport — the validation engine keys reproduction on this signal.
    succeeded = bool(data.get("success")) and int(data.get("return_code", 0) or 0) == 0
    return result(succeeded, target, "exec", raw=raw, bounded=bounded,
                  summary=f"rc={data.get('return_code')} success={data.get('success')}")


def run_argv(target: str, argv: list, budget=None, timeout: float | None = None) -> dict:
    """Run a tool by argv list — no shell string is ever built. The engine execs
    the list with shell=False. `budget.charge(target)` is applied first when given."""
    s = settings()
    if budget is not None:
        from offensia.core.budget import CapExceeded
        try:
            budget.charge(target)
        except CapExceeded as exc:
            raise exc
    try:
        resp = requests.post(  # nosec B113 — timeout set below
            f"{s['execution_url']}/api/command",
            json={"argv": [str(a) for a in argv], "use_cache": False},
            timeout=timeout or s["http_timeout"],
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — must not crash the MCP layer
        return result(False, target, "exec", error=f"{type(exc).__name__}: {exc}")
    raw, bounded = bound_output(str(data.get("stdout", "")), s["http_max_bytes"])
    succeeded = bool(data.get("success")) and int(data.get("return_code", 0) or 0) == 0
    res = result(succeeded, target, "exec", raw=raw, bounded=bounded,
                 summary=f"rc={data.get('return_code')} success={data.get('success')}")
    if budget is not None:
        pc = int(data.get("probe_count", 1) or 1)
        if pc > 1:
            from offensia.core.budget import CapExceeded
            try:
                budget.charge(target, cost=pc - 1)
            except CapExceeded as exc:
                raise exc
    return res


def health() -> dict:
    s = settings()
    try:
        r = requests.get(f"{s['execution_url']}/health", timeout=5)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
