"""Append-only, hash-chained evidence ledger (Evidence Plane).

Each event stores ``previous_event_hash`` and its own ``event_hash`` computed over
the canonical event body. Tampering with any historical record breaks the chain,
which ``verify`` detects. JSONL storage per assessment.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

GENESIS = "0" * 64


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(previous_hash: str, body: dict) -> str:
    payload = previous_hash + _canonical(body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ledger_file(assessment_dir: Path) -> Path:
    Path(assessment_dir).mkdir(parents=True, exist_ok=True)
    return Path(assessment_dir) / "ledger.jsonl"


def _last_hash(path: Path) -> str:
    if not path.exists():
        return GENESIS
    last = GENESIS
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = json.loads(line).get("event_hash", last)
    return last


def append(assessment_dir: Path, record: dict) -> dict:
    """Append an event. Returns the stored event (with ids and hashes)."""
    path = _ledger_file(assessment_dir)
    previous = _last_hash(path)
    body = {
        "event_id": uuid.uuid4().hex,
        "timestamp": datetime.now(UTC).isoformat(),
        "previous_event_hash": previous,
        **record,
    }
    body["event_hash"] = _hash(previous, body)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(_canonical(body) + "\n")
    return body


def read_all(assessment_dir: Path) -> list[dict]:
    path = _ledger_file(assessment_dir)
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def tail(assessment_dir: Path, n: int = 40) -> list[dict]:
    return read_all(assessment_dir)[-n:]


def verify(assessment_dir: Path) -> dict:
    """Recompute the chain. Returns {ok, count, broken_at}."""
    events = read_all(assessment_dir)
    previous = GENESIS
    for idx, ev in enumerate(events):
        stored = ev.get("event_hash")
        body = {k: v for k, v in ev.items() if k != "event_hash"}
        if ev.get("previous_event_hash") != previous:
            return {"ok": False, "count": len(events), "broken_at": idx,
                    "reason": "previous_event_hash mismatch"}
        if _hash(previous, body) != stored:
            return {"ok": False, "count": len(events), "broken_at": idx,
                    "reason": "event_hash mismatch"}
        previous = stored
    return {"ok": True, "count": len(events), "broken_at": None}
