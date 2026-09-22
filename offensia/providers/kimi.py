"""Kimi / K3-compatible provider. Model id is configurable (OFFENSIA_MODEL_ID or
KIMI_MODEL_ID); no identifier is invented."""
from __future__ import annotations

import os

from offensia.providers.base import BaseModelProvider, ProviderMetadata


class KimiProvider(BaseModelProvider):
    metadata = ProviderMetadata(
        key="kimi",
        display_name="Kimi (K3-compatible)",
        auth_env="MOONSHOT_API_KEY",
        default_base_url="https://api.moonshot.ai/v1",
        supports_mcp=True,
        model_env="KIMI_MODEL_ID",
    )

    def __init__(self, model_id: str | None = None, base_url: str | None = None):
        model_id = model_id or os.environ.get("OFFENSIA_MODEL_ID") or os.environ.get("KIMI_MODEL_ID", "")
        super().__init__(model_id=model_id, base_url=base_url)
