"""Health-aware halt: detect target degradation so an effect can't be misattributed."""
from __future__ import annotations

import re
import time
from collections.abc import Callable

LATENCY_FACTOR = 5.0
LATENCY_FLOOR_MS = 25.0


def probe_target(target: str, *, timeout: float = 3.0) -> dict:
    """Lightweight, low-noise liveness check of the in-scope TARGET (not the
    local execution engine). A HEAD request minimizes footprint on the target.

    Returns {"ok": bool, "status": int|None, "latency_ms": float|None}.
    On ANY failure (DNS, connection refused, timeout, ...) the target is
    UNMEASURABLE, not down — returns ok=True with no status/latency so a run
    is never halted on missing telemetry (defensive, non-halting default)."""
    from offensia.core import scope as scope_mod

    try:
        import requests

        raw = target.strip()
        has_scheme = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw))
        if has_scheme:
            start = time.monotonic()
            resp = requests.head(raw, timeout=timeout, allow_redirects=True)
        else:
            host = scope_mod.normalize(raw).host
            try:
                start = time.monotonic()
                resp = requests.head(f"https://{host}", timeout=timeout,
                                     allow_redirects=True)
            except Exception:
                start = time.monotonic()
                resp = requests.head(f"http://{host}", timeout=timeout,
                                     allow_redirects=True)
        latency_ms = (time.monotonic() - start) * 1000.0
        return {"ok": resp.status_code < 500, "status": resp.status_code,
                "latency_ms": latency_ms}
    except Exception:  # noqa: BLE001 — unmeasurable, never block a run on this
        return {"ok": True, "status": None, "latency_ms": None}


def degraded(baseline: dict, sample: dict) -> bool:
    if baseline.get("ok") and not sample.get("ok"):
        return True
    b, s = baseline.get("latency_ms"), sample.get("latency_ms")
    if b and s and not (b < LATENCY_FLOOR_MS and s < LATENCY_FLOOR_MS) and s > b * LATENCY_FACTOR:
        return True
    return False


def make_probe(check: Callable[[], dict], *, on_degrade: Callable[[dict, dict], None] | None = None):
    state: dict = {"baseline": None}

    def probe(target: str) -> bool:
        sample = check()
        if state["baseline"] is None:
            state["baseline"] = sample
            return bool(sample.get("ok", True))
        if degraded(state["baseline"], sample):
            if on_degrade:
                on_degrade(state["baseline"], sample)
            return False
        return True

    return probe
