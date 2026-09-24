"""Serial executor primitives: exclusive lock, append-only action log, and
deterministic resume. One active job per assessment; every lifecycle transition is
recorded so an interrupted run never looks completed.
"""
from __future__ import annotations

import json
import json as _json
import os
import os as _os
import tempfile as _tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from offensia.core import evidence as _evidence
from offensia.core import ledger as _ledger
from offensia.core.budget import Budget, CapExceeded
from offensia.core.jobs import JobRejected, validate_job

CAP_STATES = {"timeout", "budget_exhausted", "rate_limited"}
TERMINAL = {"completed", "failed", "interrupted", "refused"} | CAP_STATES


class LockHeld(Exception):
    pass


class Lock:
    def __init__(self, path: Path):
        self.path = path

    def release(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def acquire_lock(adir: Path) -> Lock:
    Path(adir).mkdir(parents=True, exist_ok=True)
    lock_path = Path(adir) / ".lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        # Stale lock detection: if the recorded pid is dead, take it over.
        try:
            pid = int(lock_path.read_text().strip() or "0")
        except (ValueError, OSError):
            pid = 0
        if pid and _pid_alive(pid):
            raise LockHeld(str(lock_path)) from exc
        lock_path.unlink(missing_ok=True)
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as fh:
        fh.write(str(os.getpid()))
    return Lock(lock_path)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _actions_file(adir: Path) -> Path:
    Path(adir).mkdir(parents=True, exist_ok=True)
    return Path(adir) / "actions.jsonl"


def read_actions(adir: Path) -> list[dict]:
    p = _actions_file(adir)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def next_seq(adir: Path) -> int:
    acts = read_actions(adir)
    return (acts[-1]["seq"] + 1) if acts else 1


def record_action(adir: Path, seq: int, phase: str, data: dict) -> dict:
    rec = {"seq": seq, "phase": phase,
           "ts": datetime.now(UTC).isoformat(), **data}
    with _actions_file(adir).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def resume(adir: Path) -> list[dict]:
    """Reclassify any job that reached 'running'/'intent' but no terminal phase as
    'interrupted', and record that transition. Returns the interrupted actions."""
    acts = read_actions(adir)
    seen_terminal: set[str] = {a["job_id"] for a in acts if a["phase"] in TERMINAL}
    started = {a["job_id"] for a in acts if a["phase"] in ("intent", "running")}
    interrupted = []
    for job_id in started - seen_terminal:
        rec = record_action(adir, next_seq(adir), "interrupted", {"job_id": job_id})
        interrupted.append(rec)
    return interrupted


def _atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _tempfile.mkstemp(dir=str(path.parent), prefix=".ckpt-", suffix=".tmp")
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(_json.dumps(obj, ensure_ascii=False, indent=2))
            fh.flush(); _os.fsync(fh.fileno())
        _os.replace(tmp, path)
    finally:
        if _os.path.exists(tmp):
            _os.remove(tmp)


def _checkpoint(adir: Path, job, status: str, terminal_seq: int, evidence_id: str | None,
                 budget_consumed: dict | None = None) -> None:
    _atomic_write_json(Path(adir) / "executor-checkpoint.json", {
        "last_job_id": job.job_id, "last_action_seq": terminal_seq, "last_status": status,
        "last_evidence_id": evidence_id, "budget_consumed": budget_consumed})


def run_job(adir, job, *, scope_file, runner, health_probe=None,
            now=time.monotonic, lock=None) -> dict:
    adir = Path(adir)
    owns_lock = lock is None
    if owns_lock:
        try:
            lock = acquire_lock(adir)
        except LockHeld:
            return {"status": "refused", "action_seq": None, "reason": "BUSY",
                    "evidence_id": None, "ledger_ref": None}
    try:
        seq = next_seq(adir)
        # validate first; a rejected job is recorded 'refused' and nothing runs
        try:
            validate_job(job, scope_file)
        except JobRejected as exc:
            term = record_action(adir, seq, "refused", {"job_id": job.job_id, "reason": exc.reason})
            _checkpoint(adir, job, "refused", term["seq"], None, None)
            return {"status": "refused", "action_seq": seq, "reason": exc.reason,
                    "evidence_id": None, "ledger_ref": None}
        record_action(adir, seq, "intent", {"job_id": job.job_id, "tool_id": job.tool_id,
                                            "targets": job.targets})
        # health-aware halt: do not hammer an unavailable target
        if health_probe is not None and not all(health_probe(t) for t in job.targets):
            term = record_action(adir, next_seq(adir), "interrupted",
                          {"job_id": job.job_id, "reason": "target_unavailable"})
            _checkpoint(adir, job, "interrupted", term["seq"], None, None)
            return {"status": "interrupted", "action_seq": seq, "reason": "target_unavailable",
                    "evidence_id": None, "ledger_ref": None}
        record_action(adir, next_seq(adir), "running", {"job_id": job.job_id})
        budget = Budget(request_cap=job.request_cap, rate=job.rate,
                        timeout=job.timeout, now=now)
        try:
            result = runner(job, budget)
        except CapExceeded as exc:
            term = record_action(adir, next_seq(adir), exc.reason, {"job_id": job.job_id})
            _checkpoint(adir, job, exc.reason, term["seq"], None, budget.snapshot())
            return {"status": exc.reason, "action_seq": seq, "reason": exc.reason,
                    "evidence_id": None, "ledger_ref": None}
        except Exception as exc:  # noqa: BLE001 — runner failure is a job failure, not a crash
            term = record_action(adir, next_seq(adir), "failed", {"job_id": job.job_id, "error": str(exc)})
            _checkpoint(adir, job, "failed", term["seq"], None, budget.snapshot())
            return {"status": "failed", "action_seq": seq, "error": str(exc),
                    "evidence_id": None, "ledger_ref": None}
        ev = _evidence.store(adir, result.get("raw", ""), kind=job.capability)
        event = _ledger.append(adir, {"kind": "job", "action": "run_job", "job_id": job.job_id,
                                      "tool_id": job.tool_id, "ok": result.get("ok"),
                                      "evidence_id": ev.evidence_id})
        status = "completed" if result.get("ok") else "failed"
        term = record_action(adir, next_seq(adir), status, {"job_id": job.job_id,
                                                     "evidence_id": ev.evidence_id})
        _checkpoint(adir, job, status, term["seq"], ev.evidence_id, budget.snapshot())
        return {"status": status, "action_seq": seq, "evidence_id": ev.evidence_id,
                "ledger_ref": event["event_id"]}
    finally:
        if owns_lock:
            lock.release()
