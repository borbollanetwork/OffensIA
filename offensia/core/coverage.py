"""Coverage Engine (Control Plane).

Tracks what has and has not been tested per attack-surface item, and adapts the
plan when technologies are discovered. The final report must show untested areas
as clearly as tested ones — so coverage is persisted state, not a checklist.
"""
from __future__ import annotations

import json
from pathlib import Path

TESTED = "TESTED"
PARTIALLY_TESTED = "PARTIALLY_TESTED"
NOT_TESTED = "NOT_TESTED"
BLOCKED = "BLOCKED"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"

COVERAGE_STATES = {TESTED, PARTIALLY_TESTED, NOT_TESTED, BLOCKED, NOT_APPLICABLE, UNKNOWN}

# Technology -> methodology families to activate when discovered (adaptive coverage).
TECH_ACTIVATION = {
    "graphql": ["web.graphql"],
    "oauth": ["web.oauth_oidc"],
    "oidc": ["web.oauth_oidc"],
    "kubernetes": ["cloud.kubernetes"],
    "websocket": ["web.websocket"],
    "jwt": ["web.jwt"],
    "saml": ["web.saml"],
    "grpc": ["api.grpc"],
}


def _file(assessment_dir: Path) -> Path:
    Path(assessment_dir).mkdir(parents=True, exist_ok=True)
    return Path(assessment_dir) / "coverage.json"


def load(assessment_dir: Path) -> dict:
    path = _file(assessment_dir)
    if not path.exists():
        return {"items": {}, "activated": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save(assessment_dir: Path, data: dict) -> None:
    _file(assessment_dir).write_text(json.dumps(data, indent=2, ensure_ascii=False),
                                     encoding="utf-8")


def set_state(assessment_dir: Path, item: str, state: str, note: str = "") -> dict:
    if state not in COVERAGE_STATES:
        raise ValueError(f"unknown coverage state {state!r}")
    data = load(assessment_dir)
    data["items"][item] = {"state": state, "note": note}
    save(assessment_dir, data)
    return data


def activate_for_tech(assessment_dir: Path, technology: str) -> list[str]:
    """Return and record the methodology families activated by a discovery."""
    families = TECH_ACTIVATION.get(technology.lower().strip(), [])
    data = load(assessment_dir)
    for fam in families:
        if fam not in data["activated"]:
            data["activated"].append(fam)
        data["items"].setdefault(fam, {"state": NOT_TESTED, "note": f"activated by {technology}"})
    save(assessment_dir, data)
    return families


def summary(assessment_dir: Path) -> dict:
    data = load(assessment_dir)
    counts = {s: 0 for s in COVERAGE_STATES}
    for v in data["items"].values():
        counts[v.get("state", UNKNOWN)] = counts.get(v.get("state", UNKNOWN), 0) + 1
    return {"counts": counts, "activated": data["activated"], "total": len(data["items"])}
