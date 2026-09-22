"""Scope engine — default-deny. The primary safety control.

Lives below the LLM orchestration layer so a model cannot bypass it by prompting.
Supports exact hosts, domain/subdomain globs, IPs, CIDRs, and exclusions, and
normalizes every target before comparison. Denied attempts are recorded by the
caller (server) into the ledger.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class NormalizedTarget:
    raw: str
    host: str
    port: int | None
    ip: ipaddress._BaseAddress | None


def normalize(target: str) -> NormalizedTarget:
    """Reduce any target form to a comparable host (+ optional port).

    Handles scheme, credentials, path, query, and uppercase. Bracketed IPv6 with
    port is supported (e.g. ``[2001:db8::1]:443``).
    """
    raw = target.strip()
    t = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", raw)
    t = t.split("/")[0].split("?")[0]
    t = t.split("@")[-1]
    port: int | None = None
    if t.startswith("["):  # bracketed IPv6, optional :port
        host = t[1 : t.index("]")]
        rest = t[t.index("]") + 1 :]
        if rest.startswith(":") and rest[1:].isdigit():
            port = int(rest[1:])
    elif t.count(":") == 1 and t.rsplit(":", 1)[1].isdigit():
        host, p = t.rsplit(":", 1)
        port = int(p)
    else:
        host = t
    host = host.lower().strip().rstrip(".")
    ip: ipaddress._BaseAddress | None = None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    return NormalizedTarget(raw=raw, host=host, port=port, ip=ip)


@dataclass
class ScopeRule:
    pattern: str
    exclude: bool = False
    meta: dict = field(default_factory=dict)


def _parse_line(line: str) -> ScopeRule | None:
    body, _, comment = line.partition("#")
    body = body.strip()
    if not body:
        return None
    meta: dict = {}
    for tok in comment.strip().split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            meta[k] = v
    exclude = body.startswith("!")
    pattern = body[1:].strip() if exclude else body
    return ScopeRule(pattern=pattern.lower(), exclude=exclude, meta=meta)


def load_rules(scope_file: Path) -> list[ScopeRule]:
    p = Path(scope_file)
    if not p.exists():
        return []
    rules = []
    for line in p.read_text(encoding="utf-8").splitlines():
        r = _parse_line(line)
        if r:
            rules.append(r)
    return rules


def load_scope(scope_file: Path) -> list[str]:
    """Convenience: the allow patterns (non-exclusions)."""
    return [r.pattern for r in load_rules(scope_file) if not r.exclude]


def _matches(nt: NormalizedTarget, pattern: str) -> bool:
    # CIDR
    if "/" in pattern:
        try:
            net = ipaddress.ip_network(pattern, strict=False)
            return nt.ip is not None and nt.ip in net
        except ValueError:
            return False
    # subdomain glob
    if pattern.startswith("*."):
        base = pattern[2:]
        return nt.host == base or nt.host.endswith("." + base)
    # exact host or ip
    return nt.host == pattern


def in_scope(target: str, scope_file: Path) -> bool:
    nt = normalize(target)
    if not nt.host:
        return False
    rules = load_rules(scope_file)
    if any(r.exclude and _matches(nt, r.pattern) for r in rules):
        return False
    return any((not r.exclude) and _matches(nt, r.pattern) for r in rules)


def add_entry(target: str, authorization_ref: str, scope_file: Path,
              engagement: str = "") -> None:
    if not authorization_ref or not authorization_ref.strip():
        raise ValueError("authorization_ref is required to add a scope entry")
    Path(scope_file).parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    entry = target.strip().lower()
    meta = f"auth={authorization_ref.strip()} added={stamp}"
    if engagement:
        meta += f" engagement={engagement.strip()}"
    with Path(scope_file).open("a", encoding="utf-8") as fh:
        fh.write(f"{entry}  # {meta}\n")


def remove_entry(target: str, scope_file: Path) -> bool:
    p = Path(scope_file)
    if not p.exists():
        return False
    entry = target.strip().lower()
    kept, removed = [], False
    for line in p.read_text(encoding="utf-8").splitlines():
        r = _parse_line(line)
        if r and not r.exclude and r.pattern == entry:
            removed = True
            continue
        kept.append(line)
    p.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed
