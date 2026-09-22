"""Finding lifecycle — a real, code-enforced state machine.

The LLM may propose observations and hypotheses; it may NOT arbitrarily declare a
finding VALIDATED, EXPLOITABLE, or CONFIRMED_IMPACT. Promotion to those states is
policy-driven and requires specific validation evidence (see ``PROMOTION_REQUIRES``
and ``core.validation``).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Lifecycle states (spec section 5)
INFORMATIONAL = "INFORMATIONAL"
HARDENING = "HARDENING"
OBSERVATION = "OBSERVATION"
HYPOTHESIS = "HYPOTHESIS"
SUSPECTED = "SUSPECTED"
VALIDATED = "VALIDATED"
EXPLOITABLE = "EXPLOITABLE"
CONFIRMED_IMPACT = "CONFIRMED_IMPACT"
FALSE_POSITIVE = "FALSE_POSITIVE"
INCONCLUSIVE = "INCONCLUSIVE"
BLOCKED = "BLOCKED"
NOT_TESTED = "NOT_TESTED"

STATES = {
    INFORMATIONAL, HARDENING, OBSERVATION, HYPOTHESIS, SUSPECTED, VALIDATED,
    EXPLOITABLE, CONFIRMED_IMPACT, FALSE_POSITIVE, INCONCLUSIVE, BLOCKED, NOT_TESTED,
}

# States the model/orchestrator may set directly (low-commitment, non-confirming).
MODEL_SETTABLE = {
    INFORMATIONAL, HARDENING, OBSERVATION, HYPOTHESIS, SUSPECTED, NOT_TESTED, BLOCKED,
}

# States reachable only through the validation pipeline (code-enforced).
VALIDATION_GATED = {VALIDATED, EXPLOITABLE, CONFIRMED_IMPACT}

# Which validation checks must have passed to enter each gated state.
PROMOTION_REQUIRES = {
    VALIDATED: {"reproduction", "negative_control"},
    EXPLOITABLE: {"reproduction", "negative_control"},
    CONFIRMED_IMPACT: {"reproduction", "negative_control", "impact_validation"},
}


class PromotionError(Exception):
    pass


@dataclass
class Finding:
    finding_id: str
    target: str
    title: str
    status: str
    severity: str = "unknown"
    confidence: str = "low"
    cwe: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    validation_events: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    notes: str = ""


def new_finding(target: str, title: str, status: str = OBSERVATION,
                evidence_refs: list[str] | None = None) -> Finding:
    if status not in MODEL_SETTABLE:
        raise PromotionError(
            f"a finding cannot be created directly in state {status!r}; "
            "gated states are reached only through validation"
        )
    return Finding(
        finding_id=uuid.uuid4().hex[:12], target=target, title=title,
        status=status, evidence_refs=list(evidence_refs or []),
    )


def promote(finding: Finding, target_status: str, checks_passed: set[str],
            validation_event_id: str = "") -> Finding:
    """Attempt to promote a finding. Enforces evidence/validation requirements.

    ``checks_passed`` is the set of validation checks the Validation Engine has
    actually confirmed for this finding. Raises PromotionError if requirements are
    not met.
    """
    if target_status not in STATES:
        raise PromotionError(f"unknown state {target_status!r}")
    if target_status in VALIDATION_GATED:
        required = PROMOTION_REQUIRES[target_status]
        missing = required - set(checks_passed)
        if missing:
            raise PromotionError(
                f"cannot promote to {target_status}: missing validation {sorted(missing)}"
            )
        if not finding.evidence_refs:
            raise PromotionError("cannot promote a finding with no evidence references")
    finding.status = target_status
    finding.checks_passed = sorted(set(finding.checks_passed) | set(checks_passed))
    if validation_event_id:
        finding.validation_events.append(validation_event_id)
    return finding


# ------------------------------------------------------------------ persistence
def _store_file(assessment_dir: Path) -> Path:
    Path(assessment_dir).mkdir(parents=True, exist_ok=True)
    return Path(assessment_dir) / "findings.json"


def save(assessment_dir: Path, findings: list[Finding]) -> None:
    _store_file(assessment_dir).write_text(
        json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load(assessment_dir: Path) -> list[Finding]:
    path = _store_file(assessment_dir)
    if not path.exists():
        return []
    return [Finding(**d) for d in json.loads(path.read_text(encoding="utf-8"))]


def upsert(assessment_dir: Path, finding: Finding) -> None:
    items = load(assessment_dir)
    items = [f for f in items if f.finding_id != finding.finding_id]
    items.append(finding)
    save(assessment_dir, items)
