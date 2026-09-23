"""Deterministic, LLM-free digest of raw tool output.

The model reads this compact structured summary instead of raw dumps; the raw
artifact stays in the evidence store and is fetched on demand. Pure functions,
bounded output, never raise on adversarial input.
"""
from __future__ import annotations

import re

_STATUS = re.compile(r"HTTP/\d(?:\.\d)?\s+(\d{3})")
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_PARAM = re.compile(r"[?&]([A-Za-z0-9_.\-]{1,40})=")
_LINK = re.compile(r"<a\s[^>]*href=", re.IGNORECASE)
_FORM = re.compile(r"<form\b", re.IGNORECASE)
_PORT = re.compile(r"^\s*(\d{1,5}/(?:tcp|udp))\s+open\s+(\S+)?\s*(.*)$", re.MULTILINE)
_TECH_HEADERS = re.compile(r"(?im)^(?:Server|X-Powered-By|X-AspNet-Version|Via):\s*(.+)$")
_TECH_MARKERS = (
    ("WordPress", r"wp-content|wp-includes"), ("Django", r"csrfmiddlewaretoken"),
    ("Laravel", r"laravel_session|XSRF-TOKEN"), ("Express", r"(?i)x-powered-by:\s*express"),
    ("React", r"__REACT_DEVTOOLS|data-reactroot"),
)
_ANOMALY = (
    ("SQL_error", r"SQL syntax|SQLSTATE|ORA-\d{5}|psql:|mysql_fetch"),
    ("stack_trace", r"Traceback \(most recent call last\)|at [\w.$]+\([\w.]+:\d+\)"),
    ("server_error", r"HTTP/\d(?:\.\d)?\s+5\d{2}"),
    ("debug_leak", r"(?i)DEBUG\s*=\s*True|X-Debug|Whoops!"),
)
_CAP_STR = 200


def _u(seq, n):
    out, seen = [], set()
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        out.append(x[:_CAP_STR] if isinstance(x, str) else x)
        if len(out) >= n:
            break
    return out


def summarize(kind: str, raw, *, max_items: int = 20) -> dict:
    if isinstance(raw, bytes):
        n = len(raw)
        text = raw.decode("utf-8", errors="replace")
    else:
        text = raw or ""
        n = len(text.encode("utf-8", errors="replace"))
    out: dict = {"kind": kind, "bytes": n}
    if not text:
        return out
    codes = sorted({int(m) for m in _STATUS.findall(text)})
    if codes:
        out["status_codes"] = codes[:max_items]
    titles = _u((t.strip() for t in _TITLE.findall(text) if t.strip()), max_items)
    if titles:
        out["titles"] = titles
    tech = list(_TECH_HEADERS.findall(text))
    tech += [name for name, pat in _TECH_MARKERS if re.search(pat, text)]
    tech = _u((t.strip() for t in tech if t.strip()), max_items)
    if tech:
        out["tech"] = sorted(tech)
    params = _u(sorted(set(_PARAM.findall(text))), max_items)
    if params:
        out["params"] = params
    ports = []
    for portproto, svc, extra in _PORT.findall(text):
        label = f"{portproto} {svc or ''} {extra or ''}".strip()
        ports.append(label[:_CAP_STR])
    ports = _u(ports, max_items)
    if ports:
        out["ports"] = ports
    links = len(_LINK.findall(text))
    if links:
        out["links"] = links
    forms = len(_FORM.findall(text))
    if forms:
        out["forms"] = forms
    anomalies = [name for name, pat in _ANOMALY if re.search(pat, text)]
    if anomalies:
        out["anomalies"] = anomalies
    return out
