"""Health-aware halt: detect target degradation so an effect can't be misattributed."""
from __future__ import annotations

from collections.abc import Callable

LATENCY_FACTOR = 5.0
LATENCY_FLOOR_MS = 25.0


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
