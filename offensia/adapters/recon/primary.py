"""Recon adapter (Execution Plane).

Satisfies web.content_extract by talking to a local LLM-friendly crawling engine
over HTTP, returning real page content (markdown/html). Content is returned as
UNTRUSTED data for the caller to fence before showing a model.
"""
from __future__ import annotations

import requests

from offensia.adapters.base import bound_output, result
from offensia.core.config import settings

PROVIDER_KEY = "recon_primary"
CAPABILITIES = ("web.content_extract",)


def fetch(target: str, mode: str = "md") -> dict:
    s = settings()
    try:
        resp = requests.post(  # nosec B113 — timeout is set dynamically below
            f"{s['recon_url']}/{mode}",
            json={"url": target},
            timeout=s["http_timeout"],
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return result(False, target, "recon", error=f"{type(exc).__name__}: {exc}")
    body = data.get("markdown") or data.get("html") or str(data)
    raw, bounded = bound_output(str(body), s["http_max_bytes"])
    return result(True, target, "recon", raw=raw, bounded=bounded, summary=f"recon:{mode}")


def health() -> dict:
    s = settings()
    try:
        r = requests.get(f"{s['recon_url']}/health", timeout=5)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
