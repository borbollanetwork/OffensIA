"""Knowledge taxonomy schema."""
from __future__ import annotations

from dataclasses import dataclass, field

TAXONOMY_DIMENSIONS = (
    "domain", "platform", "technology", "technique", "attack_surface",
    "vulnerability_class", "preconditions", "validation_method", "framework",
    "tool_capability",
)


@dataclass
class KnowledgeDoc:
    doc_id: str
    path: str
    title: str
    kind: str
    tags: list[str] = field(default_factory=list)
    domain: str = ""
