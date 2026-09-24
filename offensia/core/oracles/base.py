"""Oracle framework base.

An oracle turns baseline / candidate / negative-control results into a verdict.
It never confirms on a bare signal (200, exit 0, timeout, reflection, block page);
confirmation needs a real semantic difference plus a negative control that shows
the boundary normally holds. Oracles are pure functions over OracleContext, so
they are deterministic and unit-testable with fabricated results.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_BLOCK_MARKERS = re.compile(
    r"(access denied|request blocked|blocked by|forbidden|waf|"
    r"captcha|are you a robot|rate limit|too many requests)",
    re.IGNORECASE,
)


@dataclass
class OracleContext:
    target: str
    baseline: dict | None = None
    candidate: dict | None = None
    negative_control: dict | None = None
    identity: dict = field(default_factory=dict)
    canary: str = ""
    correlation_id: str = ""
    attempts: list = field(default_factory=list)      # extra candidate results
    evidence_refs: list = field(default_factory=list)
    oast_window_closed: bool = False


@dataclass
class OracleVerdict:
    reproduced: bool
    verdict: str                    # "confirmed" | "disproven" | "inconclusive"
    confidence: str                 # "low" | "medium" | "high"
    rationale: str
    negative_control_used: bool = False
    evidence_refs: list = field(default_factory=list)


def confirmed(rationale, confidence="medium", nc_used=False, evidence_refs=None):
    return OracleVerdict(True, "confirmed", confidence, rationale, nc_used,
                         list(evidence_refs or []))


def disproven(rationale, evidence_refs=None):
    return OracleVerdict(False, "disproven", "low", rationale, False,
                         list(evidence_refs or []))


def inconclusive(rationale, evidence_refs=None):
    return OracleVerdict(False, "inconclusive", "low", rationale, False,
                         list(evidence_refs or []))


class Oracle:
    name: str = ""
    requires_negative_control: bool = True

    def evaluate(self, ctx: OracleContext) -> OracleVerdict:
        raise NotImplementedError


REGISTRY: dict[str, Oracle] = {}


def register(oracle: Oracle) -> Oracle:
    REGISTRY[oracle.name] = oracle
    return oracle


def get(name: str) -> Oracle:
    return REGISTRY[name]


def available() -> list[str]:
    return sorted(REGISTRY)


# -------- result accessors (tolerant of the adapter result shape) -----------
def resp_body(result: dict | None) -> str:
    if not result:
        return ""
    return str(result.get("raw", "") or "")


def resp_status(result: dict | None) -> int | None:
    if not result:
        return None
    m = re.search(r"HTTP/\d(?:\.\d)?\s+(\d{3})", resp_body(result))
    if m:
        return int(m.group(1))
    st = result.get("status")
    return int(st) if isinstance(st, int) else None


def looks_like_block_page(body: str) -> bool:
    return bool(_BLOCK_MARKERS.search(body or ""))


def is_error(result: dict | None) -> bool:
    if not result:
        return True
    if result.get("ok") is False or result.get("error"):
        return True
    return looks_like_block_page(resp_body(result))
