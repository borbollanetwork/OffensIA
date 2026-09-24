"""HTTP differential oracle: baseline vs candidate vs negative control."""
from __future__ import annotations

import re

from offensia.core.oracles import base

_DYNAMIC = [
    # keyword (csrf/nonce/_token/xsrf) followed — possibly via an attribute
    # indirection like `name=csrf value=TOKEN` — by its token value.
    re.compile(
        r"(?i)(?:csrf[_-]?token|csrf|nonce|_token|xsrf)"
        r"(?:[^A-Za-z0-9]|value)*[A-Za-z0-9._\-]+"
    ),
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:?\d{2})?"),
    re.compile(r"\b[A-Fa-f0-9]{16,}\b"),
]


def _norm(body: str) -> str:
    out = body
    for pat in _DYNAMIC:
        out = pat.sub("<DYN>", out)
    return re.sub(r"\s+", " ", out).strip()


class HTTPDifferentialOracle(base.Oracle):
    name = "http_differential"
    requires_negative_control = True

    def evaluate(self, ctx: base.OracleContext) -> base.OracleVerdict:
        if ctx.negative_control is None:
            return base.inconclusive("negative control required")
        if base.is_error(ctx.candidate):
            return base.inconclusive("candidate errored or block page — not a signal")
        b = _norm(base.resp_body(ctx.baseline))
        c = _norm(base.resp_body(ctx.candidate))
        n = _norm(base.resp_body(ctx.negative_control))
        differs = c != b
        control_holds = n == b
        if not differs:
            return base.disproven("candidate identical to baseline")
        if not control_holds:
            return base.inconclusive("negative control also diverged — boundary not shown")
        extra_ok = all(_norm(base.resp_body(a)) != b and not base.is_error(a) for a in ctx.attempts)
        confidence = "high" if (ctx.attempts and extra_ok) else "medium"
        if ctx.attempts and not extra_ok:
            return base.inconclusive("difference not reproducible across attempts")
        return base.confirmed("candidate diverges from baseline; control holds",
                              confidence, nc_used=True, evidence_refs=ctx.evidence_refs)


base.register(HTTPDifferentialOracle())
