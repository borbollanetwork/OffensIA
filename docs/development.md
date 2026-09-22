# Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

- Security-critical code is test-first (`tests/`).
- Core stays model-agnostic; engine/provider specifics live in adapters/providers.
- Adapters must return structured errors, never raise into the MCP layer.
- No vendoring of upstream engine source.

See CONTRIBUTING.md for the full workflow.
