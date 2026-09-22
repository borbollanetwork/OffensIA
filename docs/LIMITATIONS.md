# Limitations — what is implemented vs. interface-only

This first build is honest about its edges. Nothing below is claimed as working
that is not.

## Fully implemented and tested
- Default-deny scope engine (normalization, glob, CIDR, exclusions, metadata).
- Append-only hash-chained ledger + integrity verification.
- Content-addressed evidence store.
- Finding state machine with code-enforced, validation-gated promotion.
- Validation engine (reproduction + negative control) with injectable runner.
- Coverage engine with adaptive activation.
- Attack graph (SQLite) with path enumeration.
- Capability registry.
- Execution and recon adapters (bounded, normalized, no crash-through) — tested
  against mocked engines.
- MCP server pipeline (scope → capability → adapter → evidence → ledger).
- Provider abstraction (Kimi, GLM) with configurable model ids.
- Knowledge engine (index + selective retrieve + KNOWLEDGE_GAP).
- Reporting (executive/technical/evidence/coverage).
- One-command installer; non-destructive, abort-on-malformed agent registration.
- CLI surface.

## Interface present, depends on runtime provisioning
- **Execution / recon engines**: OffensIA talks to them over HTTP. They are
  provisioned from `deps/engines.yaml` at install time; until they are running,
  `offensia_exec` / `offensia_recon_crawl` return structured "engine unavailable"
  errors (by design). The adapter contracts are covered by tests using mocks.
- **Engine command semantics**: `offensia_port_scan` composes an `nmap`-style
  command for the execution engine. Confirm the exact command surface your
  provisioned engine expects.

## Deferred (interface via capability registry, no adapter bound)
- **Autonomous engagement engine.** `future` in `deps/engines.yaml`. When added it
  must sit above scope/policy/evidence/validation/ledger and bypass none of them.

## Environment notes for this build
- `gh` was not available in the build environment, so the private GitHub repository
  was prepared locally and not pushed. Exact push commands are in the delivery
  notes / README history.
- Dependency `commit` fields ship empty (branch fallback). Pin them for reproducible
  production installs.
