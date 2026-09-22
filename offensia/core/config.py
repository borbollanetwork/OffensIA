"""Filesystem paths and runtime settings for OffensIA.

No engine-specific product names leak above the adapter layer. This module only
holds locations and neutral configuration values, all overridable via env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE = os.environ.get(
    "OFFENSIA_BASE", str(Path(__file__).resolve().parents[2])
)


@dataclass(frozen=True)
class Paths:
    base: Path
    scope_file: Path
    engagements_dir: Path
    deps_dir: Path
    presets_dir: Path
    engines_manifest: Path

    def assessment_dir(self, assessment_id: str) -> Path:
        d = self.engagements_dir / _safe(assessment_id)
        d.mkdir(parents=True, exist_ok=True)
        return d


def _safe(name: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "default"


def get_paths(base: str | None = None) -> Paths:
    root = Path(base or DEFAULT_BASE).resolve()
    return Paths(
        base=root,
        scope_file=root / "scope.allow",
        engagements_dir=root / "engagements",
        deps_dir=root / "deps",
        presets_dir=root / "offensia" / "presets",
        engines_manifest=root / "deps" / "engines.yaml",
    )


def settings() -> dict:
    """Runtime settings. Local-bind defaults; model ids are configurable, never
    invented."""
    return {
        "execution_url": os.environ.get("OFFENSIA_EXECUTION_URL", "http://127.0.0.1:8888"),
        "recon_url": os.environ.get("OFFENSIA_RECON_URL", "http://127.0.0.1:11235"),
        "http_timeout": int(os.environ.get("OFFENSIA_HTTP_TIMEOUT", "300")),
        "http_max_bytes": int(os.environ.get("OFFENSIA_HTTP_MAX_BYTES", str(512 * 1024))),
        "provider": os.environ.get("OFFENSIA_PROVIDER", "kimi"),
        "model_id": os.environ.get("OFFENSIA_MODEL_ID", ""),
    }
