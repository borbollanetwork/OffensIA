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
    # No shell metacharacters are ever allowed through any pattern below.
    "generic_http": ToolSpec(
        "generic_http", "web.http_probe",
        (
            r"https?://[^\s;|&$`<>()\\]+",
            r"-X",
            r"GET|POST|PUT|HEAD|OPTIONS|DELETE|PATCH",
            r"-H",
            r"[A-Za-z0-9-]+: [A-Za-z0-9 _./:+=-]+",
            r"-d",
            r"[A-Za-z0-9 _./:+=&%-]+",
        ),
    ),
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


# generic_http's argv is validated positionally (flag -> its own value), not by
# free per-token matching. Free per-token matching lets an unrelated safe-looking
# token (e.g. a bare word, or "&&" hiding inside a permissive data charset) slip
# in anywhere in argv, regardless of context — which is exactly how the catch-all
# patterns this replaces reopened an injection path. Anchored, no metacharacters.
_HTTP_URL_RE = re.compile(r"^https?://[^\s;|&$`<>()\\]+$")
_HTTP_METHOD_RE = re.compile(r"^(?:GET|POST|PUT|HEAD|OPTIONS|DELETE|PATCH)$")
_HTTP_HEADER_RE = re.compile(r"^[A-Za-z0-9-]+: [A-Za-z0-9 _./:+=-]+$")
_HTTP_DATA_RE = re.compile(r"^[A-Za-z0-9 _./:+=&%-]+$")


def _generic_http_argv_allowed(argv: list) -> bool:
    i, n = 0, len(argv)
    while i < n:
        tok = str(argv[i])
        if _HTTP_URL_RE.match(tok):
            i += 1
            continue
        if tok == "-X":
            if i + 1 >= n or not _HTTP_METHOD_RE.match(str(argv[i + 1])):
                return False
            i += 2
            continue
        if tok == "-H":
            if i + 1 >= n or not _HTTP_HEADER_RE.match(str(argv[i + 1])):
                return False
            i += 2
            continue
        if tok == "-d":
            if i + 1 >= n or not _HTTP_DATA_RE.match(str(argv[i + 1])):
                return False
            i += 2
            continue
        # Any other bare token (including shell metacharacter sequences like
        # "&&", "|", "; rm -rf /", "$(whoami)") is refused outright.
        return False
    return True


def _argv_allowed(argv: list, spec: ToolSpec) -> bool:
    if spec.tool_id == "generic_http":
        return _generic_http_argv_allowed(argv)
    pats = [re.compile(f"^(?:{p})$") for p in spec.argv_allow]
    return all(any(p.match(str(a)) for p in pats) for a in argv)


def _has_disruptive_token(job: ExecutionJob) -> bool:
    hay = " ".join([job.tool_id, *[str(a) for a in job.argv]]).lower()
    return any(tok in hay for tok in DISRUPTIVE_DENYLIST)


def _validate_job_shape(job: ExecutionJob) -> None:
    """Reject malformed-but-constructable jobs before any field is iterated,
    so a bad type (e.g. argv=123, targets=123, cleanup_plan=[123]) raises a
    structured JobRejected instead of a raw TypeError/AttributeError."""
    if not isinstance(job.targets, list) or not all(isinstance(t, str) for t in job.targets):
        raise JobRejected("BAD_JOB", f"targets must be a list[str], got {job.targets!r}")
    if not isinstance(job.argv, list):
        raise JobRejected("BAD_JOB", f"argv must be a list, got {job.argv!r}")
    if not isinstance(job.cleanup_plan, list) or not all(
        isinstance(step, dict) for step in job.cleanup_plan
    ):
        raise JobRejected(
            "BAD_JOB", f"cleanup_plan must be a list[dict], got {job.cleanup_plan!r}"
        )


def validate_job(job: ExecutionJob, scope_file: Path) -> None:
    # 0. shape — reject malformed field types before iterating them
    _validate_job_shape(job)
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
