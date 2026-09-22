"""Reporting (Evidence Plane).

Builds report families from authoritative state (findings, coverage, ledger,
attack graph). Uses honest completeness language: never "no vulnerabilities" —
only "no vulnerability identified within executed coverage" — and always shows
untested/blocked/unknown areas.
"""
from __future__ import annotations

from pathlib import Path

from offensia.core import coverage as cov
from offensia.core import finding as fnd
from offensia.core import ledger as led

CONFIRMING = {fnd.VALIDATED, fnd.EXPLOITABLE, fnd.CONFIRMED_IMPACT}


def _bucket(findings: list[fnd.Finding]) -> dict[str, list[fnd.Finding]]:
    b: dict[str, list[fnd.Finding]] = {
        "validated": [], "suspected": [], "inconclusive": [], "false_positive": [],
        "blocked": [], "informational": []}
    for f in findings:
        if f.status in CONFIRMING:
            b["validated"].append(f)
        elif f.status == fnd.SUSPECTED:
            b["suspected"].append(f)
        elif f.status == fnd.INCONCLUSIVE:
            b["inconclusive"].append(f)
        elif f.status == fnd.FALSE_POSITIVE:
            b["false_positive"].append(f)
        elif f.status == fnd.BLOCKED:
            b["blocked"].append(f)
        else:
            b["informational"].append(f)
    return b


def executive(assessment_dir: Path, assessment_id: str) -> str:
    findings = fnd.load(assessment_dir)
    b = _bucket(findings)
    cs = cov.summary(assessment_dir)
    lines = [f"# OffensIA Executive Report — {assessment_id}", "",
             f"- Confirmed findings: {len(b['validated'])}",
             f"- Suspected: {len(b['suspected'])} | Inconclusive: {len(b['inconclusive'])}",
             f"- False positives: {len(b['false_positive'])} | Blocked: {len(b['blocked'])}",
             ""]
    if not b["validated"]:
        lines.append("No vulnerability was identified within the executed test coverage. "
                     "This is not a claim that the target is free of vulnerabilities.")
    lines += ["", "## Coverage", f"Items tracked: {cs['total']}", ""]
    for state, n in cs["counts"].items():
        lines.append(f"- {state}: {n}")
    return "\n".join(lines) + "\n"


def technical(assessment_dir: Path, assessment_id: str) -> str:
    findings = fnd.load(assessment_dir)
    b = _bucket(findings)
    lines = [f"# OffensIA Technical Report — {assessment_id}", ""]
    for section, items in b.items():
        lines.append(f"## {section.replace('_', ' ').title()} ({len(items)})")
        for f in items:
            lines.append(f"### [{f.status}] {f.severity} — {f.title}")
            lines.append(f"- target: {f.target}")
            lines.append(f"- confidence: {f.confidence} | CWE: {f.cwe or 'n/a'}")
            lines.append(f"- evidence refs: {', '.join(f.evidence_refs) or 'none'}")
            lines.append(f"- validation checks passed: {', '.join(f.checks_passed) or 'none'}")
            lines.append("")
    return "\n".join(lines) + "\n"


def evidence_report(assessment_dir: Path, assessment_id: str) -> str:
    chain = led.verify(assessment_dir)
    events = led.read_all(assessment_dir)
    lines = [f"# OffensIA Evidence Report — {assessment_id}", "",
             f"Ledger integrity: {'VERIFIED' if chain['ok'] else 'BROKEN at ' + str(chain['broken_at'])}",
             f"Total events: {chain['count']}", "", "## Event trail"]
    for e in events:
        lines.append(f"- {e.get('timestamp')} [{e.get('kind','?')}] "
                     f"{e.get('action','')} :: {e.get('summary','')} "
                     f"(event {e.get('event_id','')[:8]})")
    return "\n".join(lines) + "\n"


def coverage_report(assessment_dir: Path, assessment_id: str) -> str:
    cs = cov.summary(assessment_dir)
    data = cov.load(assessment_dir)
    lines = [f"# OffensIA Coverage Report — {assessment_id}", "",
             f"Activated methodologies: {', '.join(cs['activated']) or 'none'}", "",
             "## Items"]
    for item, v in data["items"].items():
        lines.append(f"- {item}: {v['state']} {('— ' + v['note']) if v.get('note') else ''}")
    lines += ["", "## Untested / blocked (shown as clearly as tested)"]
    for item, v in data["items"].items():
        if v["state"] in (cov.NOT_TESTED, cov.BLOCKED, cov.UNKNOWN):
            lines.append(f"- {item}: {v['state']}")
    return "\n".join(lines) + "\n"
