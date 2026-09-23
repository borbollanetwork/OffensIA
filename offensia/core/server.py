"""OffensIA MCP server (Execution Plane gateway).

Every active tool call flows: scope check -> capability resolution -> adapter ->
bounded/normalized result -> evidence store -> hash-chained ledger. Network/tool
failures return structured errors and never crash the server. The model only sees
neutral offensia_* tools. Safety is enforced here in code, not by prompt.
"""
from __future__ import annotations

from typing import Any

from offensia.adapters.execution import primary as execp
from offensia.adapters.recon import primary as reconp
from offensia.core import coverage as cov
from offensia.core import evidence as ev_mod
from offensia.core import executor as _executor
from offensia.core import finding as fnd
from offensia.core import ledger as ledger_mod
from offensia.core import scope as scope_mod
from offensia.core import untrusted
from offensia.core import validation as val
from offensia.core.capability_registry import CapabilityRegistry
from offensia.core.config import get_paths
from offensia.core.jobs import ExecutionJob
from offensia.reporting import generator as report_gen

try:
    from mcp.server.fastmcp import FastMCP
    _HAVE_MCP = True
except Exception:  # noqa: BLE001 — safe degradation if mcp not installed
    _HAVE_MCP = False

    class FastMCP:  # type: ignore[no-redef]  # minimal stub if mcp not installed
        def __init__(self, name): self.name = name
        def tool(self):
            def deco(fn): return fn
            return deco
        def run(self):
            raise RuntimeError("the 'mcp' package is not installed; run: pip install mcp")


PATHS = get_paths()
mcp = FastMCP("offensia")

REGISTRY = CapabilityRegistry()
REGISTRY.bind("execution_primary", execp)
REGISTRY.bind("recon_primary", reconp)


def _adir(assessment_id: str):
    return PATHS.assessment_dir(assessment_id)


def _scope_error(target: str, assessment_id: str) -> dict:
    ledger_mod.append(_adir(assessment_id), {
        "kind": "scope_denied", "action": "deny", "target": target,
        "normalized_target": scope_mod.normalize(target).host,
        "summary": "out-of-scope attempt refused"})
    return {"ok": False, "target": target, "action": "scope", "error": "OUT_OF_SCOPE",
            "message": (f"'{scope_mod.normalize(target).host}' is not in scope. "
                        "Authorize it with offensia_scope_add only with written "
                        "authorization. Nothing was executed.")}


def _record(assessment_id: str, target: str, res: dict, kind: str) -> dict:
    """Store raw output as evidence and append a ledger event; attach references."""
    adir = _adir(assessment_id)
    ev_ref = None
    if res.get("raw"):
        ref = ev_mod.store(adir, res["raw"], kind=kind)
        ev_ref = ref.evidence_id
        res["evidence_id"] = ref.evidence_id
        res["evidence_sha256"] = ref.sha256
    event = ledger_mod.append(adir, {
        "kind": kind, "action": res.get("action", kind), "target": target,
        "normalized_target": scope_mod.normalize(target).host,
        "capability": kind, "ok": res.get("ok"), "summary": res.get("summary", ""),
        "evidence_id": ev_ref, "bounded": res.get("bounded", False),
        "error": res.get("error")})
    res["ledger_ref"] = event["event_id"]
    return res


# ------------------------------------------------------------------- scope tools
@mcp.tool()
def offensia_scope_list() -> dict:
    """List authorized scope entries."""
    return {"ok": True, "entries": scope_mod.load_scope(PATHS.scope_file)}


@mcp.tool()
def offensia_scope_add(target: str, authorization_ref: str, engagement: str = "") -> dict:
    """Authorize a target. authorization_ref (contract/ticket/bounty/LAB) required."""
    try:
        scope_mod.add_entry(target, authorization_ref, PATHS.scope_file, engagement)
    except ValueError as exc:
        return {"ok": False, "error": "NO_AUTHORIZATION", "message": str(exc)}
    return {"ok": True, "entries": scope_mod.load_scope(PATHS.scope_file)}


# -------------------------------------------------------------- recon/exec tools
@mcp.tool()
def offensia_recon_crawl(target: str, mode: str = "md", assessment: str = "default") -> dict:
    """Extract real web content for a target (capability: web.content_extract).
    Returns UNTRUSTED data fenced for the model; stores raw as evidence."""
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    res = reconp.fetch(target, mode)
    res = _record(assessment, target, res, "recon")
    if res.get("ok"):
        wrapped = untrusted.wrap(target, res.get("raw", ""))
        res["model_view"] = untrusted.render_for_model(wrapped)
        res["injection_suspected"] = wrapped.injection_suspected
    return res


@mcp.tool()
def offensia_port_scan(target: str, ports: str = "", assessment: str = "default") -> dict:
    """Port scan a target (capability: network.port_scan)."""
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    cmd = f"nmap -sV {('-p ' + ports) if ports else ''} {scope_mod.normalize(target).host}".strip()
    res = execp.run_command(target, cmd)
    return _record(assessment, target, res, "port_scan")


def _run_via_registry(job: ExecutionJob) -> dict:
    """Resolve the capability to an adapter and invoke it with the job's argv.
    Kept as a module function so tests can substitute it."""
    cap = REGISTRY.get(job.capability)          # raises KeyError if unknown
    adapter: Any = REGISTRY.resolve(job.capability)  # raises LookupError if unbound
    target = job.targets[0] if job.targets else ""
    command = " ".join([job.tool_id, *[str(a) for a in job.argv]])
    if cap.category == "recon":
        return adapter.fetch(target, "md")
    return adapter.run_command(target, command)


@mcp.tool()
def offensia_run_job(job: dict, assessment: str = "default") -> dict:
    """Run a validated, typed ExecutionJob (scope + availability + destruction guards
    enforced) serially through the executor. Replaces offensia_exec."""
    try:
        ej = ExecutionJob(**job)
    except TypeError as exc:
        return {"status": "refused", "reason": "BAD_JOB", "detail": str(exc)}
    return _executor.run_job(_adir(assessment), ej, scope_file=PATHS.scope_file,
                             runner=_run_via_registry,
                             health_probe=lambda t: True)


# ----------------------------------------------------------------- finding tools
@mcp.tool()
def offensia_finding_create(target: str, title: str, evidence_id: str,
                            status: str = "OBSERVATION", assessment: str = "default") -> dict:
    """Create a finding in a non-confirming state, anchored to real evidence.
    Confirmation happens only through offensia_validate_finding."""
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    adir = _adir(assessment)
    if not ev_mod.resolves(adir, _sha_for(adir, evidence_id)):
        return {"ok": False, "error": "EVIDENCE_NOT_FOUND",
                "message": "evidence_id does not resolve to a stored artifact"}
    try:
        f = fnd.new_finding(target, title, status=status, evidence_refs=[evidence_id])
    except fnd.PromotionError as exc:
        return {"ok": False, "error": "ILLEGAL_STATE", "message": str(exc)}
    fnd.upsert(adir, f)
    return {"ok": True, "finding_id": f.finding_id, "status": f.status}


@mcp.tool()
def offensia_validate_finding(target: str, finding_id: str, checks: list,
                              target_status: str = "VALIDATED",
                              assessment: str = "default") -> dict:
    """Run validation checks and promote a finding only if policy is satisfied.

    ``checks`` is a list of {name, command, expect} dicts. Promotion to VALIDATED/
    EXPLOITABLE/CONFIRMED_IMPACT is code-enforced from the checks that actually pass.
    """
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    adir = _adir(assessment)
    findings = {f.finding_id: f for f in fnd.load(adir)}
    if finding_id not in findings:
        return {"ok": False, "error": "NO_SUCH_FINDING"}
    check_objs = [val.Check(name=c.get("name", ""), command=c.get("command", ""),
                            expect=c.get("expect", "success")) for c in checks]
    report = val.run_checks(target, check_objs, runner=execp.run_command)
    ev = ledger_mod.append(adir, {"kind": "validation", "action": "validate",
                                  "target": target, "finding_id": finding_id,
                                  "summary": f"verdict={report.verdict}",
                                  "checks_passed": sorted(report.checks_passed)})
    try:
        f = fnd.promote(findings[finding_id], target_status,
                        report.checks_passed, validation_event_id=ev["event_id"])
    except fnd.PromotionError as exc:
        fnd.upsert(adir, findings[finding_id])
        return {"ok": False, "error": "NOT_PROMOTED", "verdict": report.verdict,
                "checks_passed": sorted(report.checks_passed), "message": str(exc)}
    fnd.upsert(adir, f)
    return {"ok": True, "finding_id": finding_id, "status": f.status,
            "verdict": report.verdict, "checks_passed": sorted(report.checks_passed)}


# --------------------------------------------------------- coverage/evidence/etc
@mcp.tool()
def offensia_coverage_status(assessment: str = "default") -> dict:
    """Coverage summary: tested / partial / not-tested / blocked / n-a / unknown."""
    return {"ok": True, "summary": cov.summary(_adir(assessment))}


@mcp.tool()
def offensia_coverage_set(item: str, state: str, note: str = "",
                          assessment: str = "default") -> dict:
    """Record a coverage state for an attack-surface item."""
    try:
        cov.set_state(_adir(assessment), item, state, note)
    except ValueError as exc:
        return {"ok": False, "error": "BAD_STATE", "message": str(exc)}
    return {"ok": True, "summary": cov.summary(_adir(assessment))}


@mcp.tool()
def offensia_evidence_get(evidence_id: str, assessment: str = "default") -> dict:
    """Resolve an evidence reference back to its stored artifact (bounded)."""
    adir = _adir(assessment)
    sha = _sha_for(adir, evidence_id)
    data = ev_mod.load(adir, sha) if sha else None
    if data is None:
        return {"ok": False, "error": "EVIDENCE_NOT_FOUND"}
    return {"ok": True, "evidence_id": evidence_id, "sha256": sha,
            "size": len(data), "raw": data[:65536].decode("utf-8", errors="replace")}


@mcp.tool()
def offensia_ledger_verify(assessment: str = "default") -> dict:
    """Verify the append-only ledger hash chain for an assessment."""
    return {"ok": True, "integrity": ledger_mod.verify(_adir(assessment))}


@mcp.tool()
def offensia_report_generate(kind: str = "technical", assessment: str = "default") -> dict:
    """Generate a report (executive|technical|evidence|coverage)."""
    adir = _adir(assessment)
    gen = {"executive": report_gen.executive, "technical": report_gen.technical,
           "evidence": report_gen.evidence_report, "coverage": report_gen.coverage_report}
    if kind not in gen:
        return {"ok": False, "error": "BAD_REPORT_KIND"}
    return {"ok": True, "kind": kind, "report": gen[kind](adir, assessment)}


def _sha_for(adir, evidence_id: str) -> str:
    """Map a short evidence_id to its full sha256 by scanning stored artifacts."""
    from pathlib import Path
    art = Path(adir) / "artifacts"
    if not art.exists():
        return ""
    for p in art.glob(f"{evidence_id}*.bin"):
        return p.stem
    return ""


def main():
    mcp.run()


if __name__ == "__main__":
    main()
