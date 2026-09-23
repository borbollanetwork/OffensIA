"""Serial executor primitives: exclusive lock, append-only action log, and
deterministic resume. One active job per assessment; every lifecycle transition is
recorded so an interrupted run never looks completed.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

TERMINAL = {"completed", "failed", "interrupted", "refused"}


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
    except (ProcessLookupError, PermissionError):
        return pid == os.getpid()  # PermissionError means it exists
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
