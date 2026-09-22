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
CAPABILITIES = ("network.port_scan", "web.http_probe", "generic.command")


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


def health() -> dict:
    s = settings()
    try:
        r = requests.get(f"{s['execution_url']}/health", timeout=5)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
