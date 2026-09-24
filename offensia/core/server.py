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
from offensia.core import digest as digest_mod
from offensia.core import evidence as ev_mod
from offensia.core import executor as _executor
from offensia.core import finding as fnd
from offensia.core import ledger as ledger_mod
from offensia.core import scope as scope_mod
from offensia.core import state as state_mod
from offensia.core import untrusted
from offensia.core.capability_registry import CapabilityRegistry
from offensia.core.config import get_paths
from offensia.core.jobs import TOOL_SPECS, ExecutionJob
from offensia.core.oracles import authorization, file_read, http_differential, oast  # noqa: F401
from offensia.core.oracles import base as oracles
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


def _ensure_state(assessment: str) -> None:
    """Bootstrap assessment state on first tool use, so an MCP-only engagement
    is listed and resumable. Never raises — bookkeeping must not block a tool."""
    adir = _adir(assessment)
    if not (adir / "state.json").exists():
        try:
            state_mod.create(assessment, base=str(PATHS.base))
        except Exception:  # noqa: BLE001 — never block a tool on bookkeeping
            pass


def _attach_digest(adir, res: dict, kind: str) -> dict:
    ev_id = res.get("evidence_id")
    if ev_id:
        raw = ev_mod.load(adir, _sha_for(adir, ev_id)) or b""
        res["digest"] = digest_mod.summarize(kind, raw)
    return res


def _scope_error(target: str, assessment_id: str) -> dict:
    ledger_mod.append(_adir(assessment_id), {
        "kind": "scope_denied", "action": "deny", "target": target,
        "normalized_target": scope_mod.normalize(target).host,
        "summary": "out-of-scope attempt refused"})
    return {"ok": False, "target": target, "action": "scope", "error": "OUT_OF_SCOPE",
            "message": (f"'{scope_mod.normalize(target).host}' is not in scope. "
                        "Authorize it with offensia_scope_add only with written "
                        "authorization. Nothing was executed.")}


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
    _ensure_state(assessment)
    job = ExecutionJob(capability="web.content_extract", tool_id="crawl4ai_ref",
                       argv=[], targets=[target], expected_oracle="none")
    res = _executor.run_job(_adir(assessment), job, scope_file=PATHS.scope_file,
                            runner=_run_via_registry, health_probe=lambda t: True)
    res["ok"] = res.get("status") == "completed"
    adir = _adir(assessment)
    ev_id = res.get("evidence_id")
    if ev_id:
        raw = ev_mod.load(adir, _sha_for(adir, ev_id)) or b""
        text = raw.decode("utf-8", errors="replace")
        max_preview = 4096
        # Fence overhead (source line + END marker) plus a fixed margin for the
        # optional "[INJECTION-SUSPECTED]" flag, so the rendered preview is
        # guaranteed to fit max_preview regardless of the flag being present.
        overhead = len(untrusted.render_for_model(untrusted.wrap(target, ""))) \
            + len(" [INJECTION-SUSPECTED]")
        body_budget = max(0, max_preview - overhead)
        wrapped = untrusted.wrap(target, text[:body_budget])
        res["preview"] = untrusted.render_for_model(wrapped)   # bounded, still fenced
        res["injection_suspected"] = untrusted.wrap(target, text).injection_suspected
        res["digest"] = digest_mod.summarize("recon", raw)
        res.pop("model_view", None)                            # do not dump full body
    return res


@mcp.tool()
def offensia_port_scan(target: str, ports: str = "", assessment: str = "default") -> dict:
    """Port scan a target (capability: network.port_scan)."""
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    _ensure_state(assessment)
    argv = ["-sV", "-Pn"] + (["-p", ports] if ports else [])
    job = ExecutionJob(capability="network.port_scan", tool_id="nmap",
                       argv=argv, targets=[target], expected_oracle="none")
    adir = _adir(assessment)
    res = _executor.run_job(adir, job, scope_file=PATHS.scope_file,
                            runner=_run_via_registry, health_probe=lambda t: True)
    return _attach_digest(adir, res, "port_scan")


def _run_via_registry(job: ExecutionJob, budget: Any = None) -> dict:
    """Resolve the capability to an adapter and invoke it with the job's argv (list
    form; no shell string is ever built). Kept as a module function so tests can
    substitute it."""
    cap = REGISTRY.get(job.capability)          # raises KeyError if unknown
    adapter: Any = REGISTRY.resolve(job.capability)  # raises LookupError if unbound
    target = job.targets[0] if job.targets else ""
    if cap.category == "recon":
        if budget is not None:
            budget.charge(target)
        return adapter.fetch(target, "md")
    spec = TOOL_SPECS.get(job.tool_id)
    argv = [job.tool_id, *[str(a) for a in job.argv]]
    if spec is not None and spec.target_position == "append":
        argv.append(scope_mod.normalize(target).host)
    return adapter.run_argv(target, argv, budget=budget)


@mcp.tool()
def offensia_run_job(job: dict, assessment: str = "default") -> dict:
    """Run a validated, typed ExecutionJob (scope + availability + destruction guards
    enforced) serially through the executor. Replaces offensia_exec."""
    try:
        ej = ExecutionJob(**job)
    except TypeError as exc:
        return {"status": "refused", "reason": "BAD_JOB", "detail": str(exc)}
    _ensure_state(assessment)
    adir = _adir(assessment)
    res = _executor.run_job(adir, ej, scope_file=PATHS.scope_file,
                            runner=_run_via_registry,
                            health_probe=lambda t: True)
    return _attach_digest(adir, res, "http")


def _exp_job(exp: dict, argv: list, identity: dict | None) -> ExecutionJob:
    return ExecutionJob(
        capability=exp["capability"], tool_id=exp["tool_id"],
        argv=list(argv), targets=[exp["target"]],
        expected_oracle=exp.get("expected_oracle", "none"),
        request_cap=exp.get("request_cap", 20), rate=exp.get("rate", 5),
        timeout=exp.get("timeout", 30), identity_context=identity or {})


def _run_leg(adir, exp: dict, argv: list, identity: dict | None, *,
             lock=None) -> tuple[dict, dict]:
    job = _exp_job(exp, argv, identity)
    res = _executor.run_job(adir, job, scope_file=PATHS.scope_file,
                            runner=_run_via_registry, health_probe=lambda t: True,
                            lock=lock)
    raw = b""
    if res.get("evidence_id"):
        raw = ev_mod.load(adir, _sha_for(adir, res["evidence_id"])) or b""
    norm = {"ok": res.get("status") == "completed",
            "raw": raw.decode("utf-8", errors="replace"),
            "evidence_id": res.get("evidence_id")}
    # Only forward oast_events when the leg's raw result actually carries them —
    # an unconditional [] default would shadow OASTOracle's collector fallback.
    if "oast_events" in res:
        norm["oast_events"] = res["oast_events"]
    return res, norm


@mcp.tool()
def offensia_run_experiment(experiment: dict, assessment: str = "default") -> dict:
    """Run a typed experiment (baseline/candidate/negative-control) serially and
    evaluate it with the named semantic oracle. Returns a structured verdict —
    the model never sets the verdict itself."""
    target = experiment.get("target", "")
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    _ensure_state(assessment)
    for required in ("capability", "tool_id", "target", "candidate_argv"):
        if not experiment.get(required):
            return {"ok": False, "error": "BAD_EXPERIMENT", "detail": required}
    oracle_name = experiment.get("expected_oracle", "")
    if oracle_name not in oracles.available():
        return {"ok": False, "error": "UNKNOWN_ORACLE", "message": oracle_name}
    adir = _adir(assessment)
    job_results: dict = {}
    refs: list = []
    legs = [("candidate", experiment["candidate_argv"], experiment.get("candidate_identity")
             or experiment.get("identity"))]
    if experiment.get("baseline_argv"):
        legs.insert(0, ("baseline", experiment["baseline_argv"], experiment.get("identity")))
    if experiment.get("negative_argv"):
        legs.append(("negative_control", experiment["negative_argv"],
                     experiment.get("negative_identity") or experiment.get("identity")))
    normalized: dict = {}
    try:
        lock = _executor.acquire_lock(adir)
    except _executor.LockHeld:
        return {"ok": False, "error": "BUSY"}
    try:
        for name, argv, ident in legs:
            raw_res, norm = _run_leg(adir, experiment, argv, ident, lock=lock)
            job_results[name] = raw_res
            normalized[name] = norm
            if norm.get("evidence_id"):
                refs.append(norm["evidence_id"])
    finally:
        lock.release()
    identity = dict(experiment.get("identity", {}))
    correlation_id = experiment.get("correlation_id", "")
    if oracle_name == "oast":
        collector = oast.OASTCollector(adir)
        correlation_id = correlation_id or collector.token()
        identity["_collector"] = collector
    ctx = oracles.OracleContext(
        target=target, baseline=normalized.get("baseline"),
        candidate=normalized.get("candidate"),
        negative_control=normalized.get("negative_control"),
        identity=identity, canary=experiment.get("canary", ""),
        correlation_id=correlation_id, evidence_refs=refs)
    verdict = oracles.get(oracle_name).evaluate(ctx)
    ctx_ref = ev_mod.store(adir, str({"oracle": oracle_name, "verdict": verdict.verdict,
                                      "rationale": verdict.rationale}), kind="experiment")
    event = ledger_mod.append(adir, {"kind": "experiment", "action": "run_experiment",
                                     "target": target, "oracle": oracle_name,
                                     "verdict": verdict.verdict,
                                     "evidence_id": ctx_ref.evidence_id})
    return {"ok": True, "experiment_id": event["event_id"],
            "status": "completed", "oracle_verdict": verdict.verdict,
            "confidence": verdict.confidence, "reproduced": verdict.reproduced,
            "rationale": verdict.rationale,
            "negative_control_used": verdict.negative_control_used,
            "correlation_id": correlation_id,
            "evidence_refs": refs + [ctx_ref.evidence_id],
            "digest": {name: digest_mod.summarize("http", norm.get("raw", ""))
                      for name, norm in normalized.items()},
            "job_results": {k: v.get("status") for k, v in job_results.items()}}


# ----------------------------------------------------------------- finding tools
@mcp.tool()
def offensia_finding_create(target: str, title: str, evidence_id: str,
                            status: str = "OBSERVATION", assessment: str = "default") -> dict:
    """Create a finding in a non-confirming state, anchored to real evidence.
    Confirmation happens only through offensia_validate_finding."""
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    _ensure_state(assessment)
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
def offensia_validate_finding(target: str, finding_id: str, assessment: str = "default",
                              experiment: dict | None = None,
                              target_status: str = "VALIDATED") -> dict:
    """Promote a finding only via an oracle-driven ``experiment`` run.

    ``experiment`` (same shape as ``offensia_run_experiment`` expects) is run
    and the resulting oracle verdict — never a model-set verdict — drives
    promotion via ``finding.promote_from_verdict``. This is the only
    promotion path; there is no command-string/checks fallback.
    """
    if not scope_mod.in_scope(target, PATHS.scope_file):
        return _scope_error(target, assessment)
    adir = _adir(assessment)
    findings = {f.finding_id: f for f in fnd.load(adir)}
    if finding_id not in findings:
        return {"ok": False, "error": "NO_SUCH_FINDING"}
    if experiment is None:
        return {"ok": False, "error": "EXPERIMENT_REQUIRED",
                "message": "validation requires a typed experiment + oracle"}
    exp = dict(experiment)
    exp.setdefault("target", target)
    exp_res = offensia_run_experiment(exp, assessment=assessment)
    if not exp_res.get("ok"):
        return exp_res
    v = oracles.OracleVerdict(
        reproduced=exp_res["reproduced"], verdict=exp_res["oracle_verdict"],
        confidence=exp_res["confidence"], rationale=exp_res["rationale"],
        negative_control_used=exp_res["negative_control_used"],
        evidence_refs=exp_res["evidence_refs"])
    try:
        f = fnd.promote_from_verdict(findings[finding_id], target_status,
                                     exp["expected_oracle"], v,
                                     validation_event_id=exp_res["experiment_id"])
    except fnd.PromotionError as exc:
        fnd.upsert(adir, findings[finding_id])
        return {"ok": False, "error": "NOT_PROMOTED", "verdict": v.verdict,
                "confidence": v.confidence, "message": str(exc)}
    fnd.upsert(adir, f)
    return {"ok": True, "finding_id": finding_id, "status": f.status,
            "verdict": v.verdict, "experiment_id": exp_res["experiment_id"]}


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
