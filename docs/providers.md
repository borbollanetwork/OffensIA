# Providers

OffensIA is model-agnostic. A provider only describes how to talk to a vendor;
offensive methodology never lives in provider code.

- `offensia/providers/base.py` — `BaseModelProvider`, `ProviderMetadata`.
- `offensia/providers/kimi.py` — Kimi / K3-compatible.
- `offensia/providers/glm.py` — GLM-compatible + `get_provider(key)`.

Model identifiers are configurable and never invented. If a model id or API key is
missing, `provider.describe()["missing_config"]` lists exactly what to set;
`offensia doctor` surfaces it too.

## Add a provider
Subclass `BaseModelProvider`, set `metadata` (key, auth env, base url, model env,
MCP support), and register it in `get_provider`.
