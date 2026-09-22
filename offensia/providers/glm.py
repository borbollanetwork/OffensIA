"""GLM-compatible provider. Model id is configurable (OFFENSIA_MODEL_ID or
GLM_MODEL_ID); no identifier is invented."""
from __future__ import annotations

import os

from offensia.providers.base import BaseModelProvider, ProviderMetadata


class GLMProvider(BaseModelProvider):
    metadata = ProviderMetadata(
        key="glm",
        display_name="GLM-compatible",
        auth_env="ZHIPU_API_KEY",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        supports_mcp=True,
        model_env="GLM_MODEL_ID",
    )

    def __init__(self, model_id: str | None = None, base_url: str | None = None):
        model_id = model_id or os.environ.get("OFFENSIA_MODEL_ID") or os.environ.get("GLM_MODEL_ID", "")
        super().__init__(model_id=model_id, base_url=base_url)


def get_provider(key: str):
    from offensia.providers.kimi import KimiProvider
    key = (key or "").lower()
    if key == "kimi":
        return KimiProvider()
    if key == "glm":
        return GLMProvider()
    raise KeyError(f"unknown provider {key!r}")
