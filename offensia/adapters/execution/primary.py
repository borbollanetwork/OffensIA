"""Execution adapter (Execution Plane).

Satisfies active capabilities (port scan, HTTP probe, generic command) by talking
to a local deterministic tool-execution engine over HTTP. Output is bounded and
normalized. The concrete engine is declared in deps/engines.yaml and reached only
through this adapter, so upstream naming never leaks upward.
"""
from __future__ import annotations

import requests

from offensia.core.config import settings
from offensia.adapters.base import result, bound_output

PROVIDER_KEY = "execution_primary"
CAPABILITIES = ("network.port_scan", "web.http_probe", "generic.command")


def run_command(target: str, command: str, use_cache: bool = True) -> dict:
    s = settings()
    try:
        resp = requests.post(
            f"{s['execution_url']}/api/command",
            json={"command": command, "use_cache": use_cache},
            timeout=s["http_timeout"],
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — must not crash the MCP layer
        return result(False, target, "exec", error=f"{type(exc).__name__}: {exc}")
    raw, bounded = bound_output(str(data.get("stdout", "")), s["http_max_bytes"])
    return result(True, target, "exec", raw=raw, bounded=bounded,
                  summary=f"rc={data.get('return_code')} success={data.get('success')}")


def health() -> dict:
    s = settings()
    try:
        r = requests.get(f"{s['execution_url']}/health", timeout=5)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
