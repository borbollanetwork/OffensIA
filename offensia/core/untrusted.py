"""Untrusted-content handling (defense against indirect prompt injection).

All target-derived content (web pages, tool stdout, source, docs, crawler output)
is UNTRUSTED DATA. It must never be interpreted as instructions to the model or
the execution layer. This module wraps such content with explicit framing and
neutralizes the most common injection triggers before it is shown to a model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns commonly used to hijack an agent via page/tool content.
_INJECTION_HINTS = re.compile(
    r"(ignore (all |the )?(previous|prior|above) instructions"
    r"|disregard (all|previous)"
    r"|you are now"
    r"|system prompt"
    r"|<\s*/?\s*system\s*>)",
    re.IGNORECASE,
)


@dataclass
class UntrustedContent:
    source: str
    body: str
    injection_suspected: bool


def wrap(source: str, body: str, max_bytes: int = 512 * 1024) -> UntrustedContent:
    truncated = body[:max_bytes]
    return UntrustedContent(
        source=source,
        body=truncated,
        injection_suspected=bool(_INJECTION_HINTS.search(truncated)),
    )


def render_for_model(content: UntrustedContent) -> str:
    """Return content clearly fenced as DATA, never CONTROL. The model prompt tells
    the model that everything inside is untrusted target data."""
    flag = " [INJECTION-SUSPECTED]" if content.injection_suspected else ""
    return (
        f"<<<OFFENSIA_UNTRUSTED_DATA source={content.source}{flag}>>>\n"
        f"{content.body}\n"
        f"<<<END_OFFENSIA_UNTRUSTED_DATA>>>"
    )
