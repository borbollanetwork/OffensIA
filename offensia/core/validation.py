"""Validation Engine (Control Plane).

First-class component whose job is to *challenge* findings, not confirm them
cheaply. A hypothesis survives only if deterministic checks reproduce it and
controls behave as an attacker theory predicts. The engine can disagree with the
primary testing logic.

A ``Check`` declares a command and an expectation:
  - expect="success": the check passes when the command reproduces the behavior.
  - expect="failure": the check passes when the command does NOT reproduce it
    (used for negative controls — the benign/control input must behave differently).

``runner(target, command) -> {"ok": bool, "raw": str, ...}`` is injected so the
engine is deterministic and unit-testable, and so it always flows through the
scope-guarded execution adapter in production.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Named checks the finding promotion policy understands.
KNOWN_CHECKS = {
    "reproduction", "negative_control", "control_request", "role_comparison",
    "ownership_comparison", "state_comparison", "timing_comparison",
    "semantic_validation", "impact_validation", "environmental_sanity",
}


@dataclass
class Check:
    name: str
    command: str
    expect: str = "success"  # "success" | "failure"


@dataclass
class ValidationReport:
    checks_passed: set = field(default_factory=set)
    checks_failed: set = field(default_factory=set)
    evidence: list = field(default_factory=list)  # per-check raw tails

    @property
    def verdict(self) -> str:
        if "reproduction" in self.checks_passed and "negative_control" in self.checks_passed:
            return "validated"
        if self.checks_failed and not self.checks_passed:
            return "false_positive"
        return "inconclusive"


def run_checks(target: str, checks: list[Check], runner) -> ValidationReport:
    report = ValidationReport()
    for chk in checks:
        if chk.name not in KNOWN_CHECKS:
            # Unknown checks never count toward promotion.
            report.checks_failed.add(chk.name)
            report.evidence.append({"check": chk.name, "error": "unknown check"})
            continue
        res = runner(target, chk.command)
        reproduced = bool(res.get("ok"))
        passed = reproduced if chk.expect == "success" else (not reproduced)
        (report.checks_passed if passed else report.checks_failed).add(chk.name)
        report.evidence.append({
            "check": chk.name, "expect": chk.expect, "reproduced": reproduced,
            "raw_tail": str(res.get("raw", ""))[-1000:],
        })
    return report
