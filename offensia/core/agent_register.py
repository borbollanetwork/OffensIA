"""Agent/MCP registration — non-destructive, atomic, abort-on-malformed.

Merge flow (spec section 26/28):
  read -> parse -> validate -> backup -> build candidate -> validate candidate ->
  atomic replace -> verify.

If the EXISTING config is malformed JSON, the modification is ABORTED and the
original preserved — OffensIA never guesses or repairs a third-party config.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path


class RegistrationAbort(Exception):
    pass


def build_server_entry(base: Path, python: str) -> dict:
    return {
        "command": python,
        "args": ["-m", "offensia.core.server"],
        "env": {"OFFENSIA_BASE": str(Path(base).resolve())},
    }


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".offensia-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def merge_config(config_path: Path, server_entry: dict, name: str = "offensia") -> dict:
    """Register OffensIA into an agent MCP config. Returns {ok, backup, aborted, reason}."""
    config_path = Path(config_path)
    backup = None
    data: dict = {"mcpServers": {}}

    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegistrationAbort(
                f"existing config at {config_path} is malformed JSON ({exc}); "
                "aborting to preserve it. Fix or move it, then retry."
            ) from exc
        if not isinstance(existing, dict):
            raise RegistrationAbort(
                f"existing config at {config_path} is not a JSON object; aborting."
            )
        backup = config_path.with_suffix(config_path.suffix + f".bak.{_timestamp()}")
        shutil.copy2(config_path, backup)
        data = existing

    data.setdefault("mcpServers", {})
    if not isinstance(data["mcpServers"], dict):
        raise RegistrationAbort("existing 'mcpServers' is not an object; aborting.")
    data["mcpServers"][name] = server_entry

    candidate = json.dumps(data, indent=2, ensure_ascii=False)
    json.loads(candidate)  # validate candidate before writing
    _atomic_write(config_path, candidate)

    verify = json.loads(config_path.read_text(encoding="utf-8"))
    ok = name in verify.get("mcpServers", {})
    return {"ok": ok, "backup": str(backup) if backup else None, "aborted": False,
            "reason": "" if ok else "post-write verification failed"}


def restore_backup(config_path: Path) -> bool:
    config_path = Path(config_path)
    backups = sorted(glob.glob(str(config_path) + ".bak.*"))
    if not backups:
        return False
    shutil.copy2(backups[-1], config_path)
    return True
