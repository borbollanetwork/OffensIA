"""Typed execution jobs and code-enforced pre-execution policy.

A job runs only if it passes scope, tool/argv allowlist, caps, the availability
guard (no DoS/crash/stress) and the destruction guard (no delete/overwrite of
pre-existing target-owned data). This replaces the generic-command path.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from offensia.core.scope import in_scope

DOS_RISK_CLASSES = {"dos", "availability_impact", "crash"}
# Tokens that indicate a disruptive/availability-affecting action, matched
# case-insensitively against each argv element and the tool id.
DISRUPTIVE_DENYLIST = (
    "flood", "stress", "dos", "slowloris", "hping3", "--flood", "-flood",
    "synflood", "udpflood", "loris", "killall", "shutdown", "reboot",
)


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    capability: str
    argv_allow: tuple  # regex patterns; each argv element must match one


# Static tool registry. Extend as adapters grow. argv_allow patterns are anchored.
TOOL_SPECS: dict[str, ToolSpec] = {
    "nmap": ToolSpec("nmap", "network.port_scan",
                     (r"-sV", r"-p", r"[0-9,\-]+", r"-Pn", r"-T[0-3]")),
    "httpx": ToolSpec("httpx", "web.http_probe", (r"-status-code", r"-title", r"-tech-detect")),
    # A constrained HTTP requester used by web oracles; URL + safe flags only.
    "generic_http": ToolSpec("generic_http", "web.http_probe",
                             (r"https?://[^\s]+", r"-X", r"GET|POST|PUT|HEAD|OPTIONS",
                              r"-H", r"[^\s].*", r"-d", r".*")),
}


class JobRejected(Exception):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass
class ExecutionJob:
    capability: str
    tool_id: str
    argv: list
    targets: list
    risk_class: str = "active"
    expected_oracle: str = "none"
    negative_control: dict | None = None
    request_cap: int = 100
    rate: int = 10
    timeout: int = 60
    cleanup_plan: list = field(default_factory=list)
    evidence_contract: list = field(default_factory=list)
    identity_context: dict = field(default_factory=dict)
    preconditions: list = field(default_factory=list)
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


def _argv_allowed(argv: list, spec: ToolSpec) -> bool:
    pats = [re.compile(f"^(?:{p})$") for p in spec.argv_allow]
    return all(any(p.match(str(a)) for p in pats) for a in argv)


def _has_disruptive_token(job: ExecutionJob) -> bool:
    hay = " ".join([job.tool_id, *[str(a) for a in job.argv]]).lower()
    return any(tok in hay for tok in DISRUPTIVE_DENYLIST)


def validate_job(job: ExecutionJob, scope_file: Path) -> None:
    # 1. scope — every target must be in scope (refuse whole job otherwise)
    for t in job.targets:
        if not in_scope(t, scope_file):
            raise JobRejected("OUT_OF_SCOPE", t)
    # 2. tool known
    spec = TOOL_SPECS.get(job.tool_id)
    if spec is None:
        raise JobRejected("UNKNOWN_TOOL", job.tool_id)
    # 3. availability guard (before argv detail so risk_class/denylist win clearly)
    if job.risk_class in DOS_RISK_CLASSES or _has_disruptive_token(job):
        raise JobRejected("AVAILABILITY_GUARD", job.risk_class)
    # 4. argv allowlist
    if not _argv_allowed(job.argv, spec):
        raise JobRejected("ARGV_NOT_ALLOWED", " ".join(map(str, job.argv)))
    # 5. destruction guard — cleanup may only remove self-created artifacts
    for step in job.cleanup_plan:
        if step.get("action") in ("delete", "overwrite", "truncate") \
                and step.get("origin") != "offensia":
            raise JobRejected("DESTRUCTION_GUARD", str(step.get("path")))
    # 6. caps present and sane
    if job.timeout <= 0 or job.request_cap <= 0 or job.rate <= 0:
        raise JobRejected("BAD_CAPS", f"timeout={job.timeout} cap={job.request_cap} rate={job.rate}")
