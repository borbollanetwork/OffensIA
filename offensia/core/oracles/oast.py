"""OAST oracle + a file-based collector for out-of-band callbacks.

Each experiment mints a unique correlation id; a callback confirms only when its
id matches. A callback with no correlation never confirms a finding.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from offensia.core.oracles import base


class OASTCollector:
    def __init__(self, adir):
        self.path = Path(adir) / "oast.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def token(self) -> str:
        return uuid.uuid4().hex[:16]

    def record(self, correlation_id: str, meta: dict) -> None:
        rec = {"correlation_id": correlation_id,
               "ts": datetime.now(UTC).isoformat(), **meta}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def events(self, correlation_id: str) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("correlation_id") == correlation_id:
                out.append(rec)
        return out


class OASTOracle(base.Oracle):
    name = "oast"
    requires_negative_control = False

    def evaluate(self, ctx: base.OracleContext) -> base.OracleVerdict:
        if not ctx.correlation_id:
            return base.inconclusive("no correlation id minted for this experiment")
        events = []
        if ctx.candidate and isinstance(ctx.candidate.get("oast_events"), list):
            events = [e for e in ctx.candidate["oast_events"]
                      if e.get("correlation_id") == ctx.correlation_id]
        else:
            collector = ctx.identity.get("_collector")
            if collector is not None:
                events = collector.events(ctx.correlation_id)
        if events:
            return base.confirmed(f"{len(events)} correlated out-of-band callback(s)",
                                  "high", nc_used=False, evidence_refs=ctx.evidence_refs)
        if not ctx.oast_window_closed:
            return base.inconclusive("no callback yet; polling window still open")
        return base.disproven("no correlated out-of-band callback within the window")


base.register(OASTOracle())
