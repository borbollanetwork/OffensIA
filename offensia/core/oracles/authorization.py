"""Authorization oracle: BOLA/BFLA/IDOR via cross-identity access + boundary control."""
from __future__ import annotations

from offensia.core.oracles import base


def _granted(result, marker) -> bool:
    if base.is_error(result):
        return False
    status = base.resp_status(result)
    if status is not None and status >= 400:
        return False
    return marker in base.resp_body(result)


class AuthorizationOracle(base.Oracle):
    name = "authorization"
    requires_negative_control = True

    def evaluate(self, ctx: base.OracleContext) -> base.OracleVerdict:
        marker = str(ctx.identity.get("marker", ""))
        if not marker:
            return base.inconclusive("no identity marker to discriminate")
        if ctx.negative_control is None:
            return base.inconclusive("negative control required")
        cand = _granted(ctx.candidate, marker)
        ctrl = _granted(ctx.negative_control, marker)
        if cand and not ctrl:
            return base.confirmed("attacker identity obtained the protected object; "
                                  "boundary holds under control", "high",
                                  nc_used=True, evidence_refs=ctx.evidence_refs)
        if cand and ctrl:
            return base.inconclusive("control also granted — boundary not demonstrated")
        return base.disproven("attacker identity did not obtain the protected object")


base.register(AuthorizationOracle())
