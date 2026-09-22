"""Provider abstraction. Offensive methodology stays OUT of provider code.

Providers only describe how to talk to a model vendor (endpoint, auth env var,
tool/MCP compatibility, model id). Model identifiers are configurable and never
invented; if unknown, they are surfaced as required configuration.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderMetadata:
    key: str
    display_name: str
    auth_env: str
    default_base_url: str
    supports_mcp: bool
    model_env: str


class BaseModelProvider:
    metadata: ProviderMetadata

    def __init__(self, model_id: str | None = None, base_url: str | None = None):
        import os

        self.model_id = model_id or os.environ.get(self.metadata.model_env, "")
        self.base_url = base_url or os.environ.get(
            f"{self.metadata.key.upper()}_BASE_URL", self.metadata.default_base_url)

    def requires(self) -> list[str]:
        """Return the configuration keys still missing for this provider to run."""
        import os

        missing = []
        if not self.model_id:
            missing.append(self.metadata.model_env)
        if not os.environ.get(self.metadata.auth_env):
            missing.append(self.metadata.auth_env)
        return missing

    def describe(self) -> dict:
        return {
            "key": self.metadata.key,
            "display_name": self.metadata.display_name,
            "model_id": self.model_id or f"(unset — configure via {self.metadata.model_env})",
            "base_url": self.base_url,
            "supports_mcp": self.metadata.supports_mcp,
            "missing_config": self.requires(),
        }
