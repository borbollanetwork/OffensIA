"""HTTP differential oracle: baseline vs candidate vs negative control."""
from __future__ import annotations

from offensia.core.oracles import base


class HTTPDifferentialOracle(base.Oracle):
    name = "http_differential"
    requires_negative_control = True

    def evaluate(self, ctx: base.OracleContext) -> base.OracleVerdict:
        if ctx.negative_control is None:
            return base.inconclusive("negative control required")
        if base.is_error(ctx.candidate):
            return base.inconclusive("candidate errored or block page — not a signal")
        b = base.resp_body(ctx.baseline)
        c = base.resp_body(ctx.candidate)
        n = base.resp_body(ctx.negative_control)
        differs = c != b
        control_holds = n == b
        if not differs:
            return base.disproven("candidate identical to baseline")
        if not control_holds:
            return base.inconclusive("negative control also diverged — boundary not shown")
        extra_ok = all(base.resp_body(a) != b and not base.is_error(a) for a in ctx.attempts)
        confidence = "high" if (ctx.attempts and extra_ok) else "medium"
        if ctx.attempts and not extra_ok:
            return base.inconclusive("difference not reproducible across attempts")
        return base.confirmed("candidate diverges from baseline; control holds",
                              confidence, nc_used=True, evidence_refs=ctx.evidence_refs)


base.register(HTTPDifferentialOracle())
