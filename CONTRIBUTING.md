# Contributing to OffensIA

## Ground rules
- Safety controls (scope, policy, evidence, validation, ledger) are enforced in
  code. Never move a safety decision into a prompt.
- Security-critical code is test-first. Add or update tests under `tests/` for any
  change to scope, ledger, findings, validation, adapters, or agent registration.
- Keep the core model-agnostic. Provider- and engine-specific details live in
  `offensia/providers/` and `offensia/adapters/` only.
- No vendoring of upstream engine source into this repository.

## Development
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

## Style
- Typed function signatures; small, focused modules with one responsibility.
- No `shell=True`, no unsafe deserialization, no silent exception swallowing in
  code paths that affect safety or evidence.
- Adapters must never let a network/tool failure raise into the MCP layer; return a
  structured error instead.

## Pull requests
Describe what changed and why, list the tests you added, and confirm the suite
passes. Changes touching safety controls get extra review.
