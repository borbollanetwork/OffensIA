"""Assessment state (Control Plane) — resumable.

The authoritative state never depends on one LLM context window. An assessment can
be created, listed, shown, and resumed with its scope, discoveries, coverage,
findings, hypotheses, and pending work restored from disk.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from offensia.core.config import get_paths


def _state_file(assessment_dir: Path) -> Path:
    Path(assessment_dir).mkdir(parents=True, exist_ok=True)
    return Path(assessment_dir) / "state.json"


def _default_state(assessment_id: str, engagement: str = "") -> dict:
    return {
        "assessment_id": assessment_id,
        "engagement": engagement,
        "created": datetime.now(UTC).isoformat(),
        "discoveries": {"technologies": [], "hosts": []},
        "hypotheses": [],
        "pending_tests": [],
        "pending_validation": [],
    }


def create(assessment_id: str, engagement: str = "", base: str | None = None) -> dict:
    paths = get_paths(base)
    adir = paths.assessment_dir(assessment_id)
    data = _default_state(assessment_id, engagement)
    _state_file(adir).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    return data


def load(assessment_id: str, base: str | None = None) -> dict | None:
    paths = get_paths(base)
    path = _state_file(paths.assessment_dir(assessment_id))
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    # Tolerate a state.json missing assessment keys (e.g. clobbered by a legacy
    # executor checkpoint, or otherwise partial): merge onto the default template
    # without overwriting any real values already present.
    merged = _default_state(assessment_id)
    merged.update(loaded)
    return merged


def save(assessment_id: str, data: dict, base: str | None = None) -> None:
    paths = get_paths(base)
    _state_file(paths.assessment_dir(assessment_id)).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_assessments(base: str | None = None) -> list[str]:
    paths = get_paths(base)
    if not paths.engagements_dir.exists():
        return []
    return sorted(p.name for p in paths.engagements_dir.iterdir()
                  if (p / "state.json").exists() or (p / "executor-checkpoint.json").exists())
