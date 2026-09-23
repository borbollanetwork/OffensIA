"""Capability Registry (Control/Execution boundary).

The planner requests *capabilities* ("web.content_extract"), never engine product
names. Adapters declare which capabilities they satisfy; the registry resolves a
capability to a provider adapter. This keeps upstream engines swappable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    id: str
    category: str          # discovery | recon | validation | exploitation | ...
    risk: str              # passive | active
    scope_required: bool
    provider: str          # logical provider key (e.g. execution_primary)
    outputs: tuple = ()
    requirements: dict = field(default_factory=dict)


# Built-in capability catalog (extend as adapters grow).
CATALOG: dict[str, Capability] = {
    "network.port_scan": Capability(
        "network.port_scan", "discovery", "active", True, "execution_primary",
        outputs=("stdout", "normalized_ports"), requirements={"network": True}),
    "web.content_extract": Capability(
        "web.content_extract", "recon", "passive", True, "recon_primary",
        outputs=("html", "markdown", "screenshot")),
    "web.http_probe": Capability(
        "web.http_probe", "discovery", "active", True, "execution_primary",
        outputs=("stdout",), requirements={"network": True}),
}


class CapabilityRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, object] = {}

    def bind(self, provider_key: str, adapter: object) -> None:
        self._providers[provider_key] = adapter

    def get(self, capability_id: str) -> Capability:
        if capability_id not in CATALOG:
            raise KeyError(f"unknown capability {capability_id!r}")
        return CATALOG[capability_id]

    def resolve(self, capability_id: str) -> object:
        cap = self.get(capability_id)
        adapter = self._providers.get(cap.provider)
        if adapter is None:
            raise LookupError(f"no adapter bound for provider {cap.provider!r}")
        return adapter

    def list_capabilities(self) -> list[str]:
        return sorted(CATALOG)
