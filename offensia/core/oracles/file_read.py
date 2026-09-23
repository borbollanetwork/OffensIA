"""File-read oracle: canary-file read proves traversal/inclusion, before any real path."""
from __future__ import annotations

from offensia.core.oracles import base


class FileReadOracle(base.Oracle):
    name = "file_read"
    requires_negative_control = True

    def evaluate(self, ctx: base.OracleContext) -> base.OracleVerdict:
        if not ctx.canary:
            return base.inconclusive("no canary marker configured")
        if ctx.negative_control is None:
            return base.inconclusive("negative control required")
        if base.is_error(ctx.candidate):
            return base.inconclusive("candidate errored or block page — not a signal")
        got = ctx.canary in base.resp_body(ctx.candidate)
        if not got:
            return base.disproven("canary not present in candidate response")
        if ctx.canary in base.resp_body(ctx.negative_control):
            return base.inconclusive("canary also present in control — not discriminating")
        return base.confirmed("canary content retrieved via the tested vector", "high",
                              nc_used=True,
                              evidence_refs=ctx.evidence_refs)


base.register(FileReadOracle())
