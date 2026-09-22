"""Normalized result schema shared by every adapter and MCP tool.

Network failures and tool crashes are captured here as structured errors — they
never propagate as exceptions into the MCP server.
"""
from __future__ import annotations


def result(ok: bool, target: str, action: str, raw: str = "", summary: str = "",
           ledger_ref: str | None = None, error: str | None = None,
           bounded: bool = False) -> dict:
    return {
        "ok": ok, "target": target, "action": action, "raw": raw,
        "summary": summary, "ledger_ref": ledger_ref, "error": error,
        "bounded": bounded,
    }


def bound_output(text: str, max_bytes: int) -> tuple[str, bool]:
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return text, False
    return data[:max_bytes].decode("utf-8", errors="replace"), True
