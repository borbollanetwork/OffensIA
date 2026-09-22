# Architecture

OffensIA is organized as three decoupled planes.

## Control plane
- `offensia/core/config.py` — paths and settings (env-overridable).
- `offensia/core/scope.py` — default-deny scope, normalization, glob/CIDR/exclusions.
- `offensia/core/state.py` — resumable assessment state.
- `offensia/core/coverage.py` — coverage tracking + adaptive activation.
- `offensia/core/capability_registry.py` — capability → provider resolution.
- `offensia/providers/` — model provider abstraction (Kimi, GLM).
- `offensia/knowledge/` — selective knowledge retrieval.

## Execution plane
- `offensia/core/server.py` — MCP gateway; every active tool passes
  scope → capability → adapter → bounded/normalized result → evidence → ledger.
- `offensia/adapters/execution/` — deterministic tool execution.
- `offensia/adapters/recon/` — web content ingestion.
- `offensia/core/untrusted.py` — untrusted-content fencing.

## Evidence plane
- `offensia/core/ledger.py` — append-only, hash-chained events.
- `offensia/core/evidence.py` — content-addressed artifact store.
- `offensia/core/finding.py` — finding state machine + promotion policy.
- `offensia/core/attack_graph.py` — SQLite attack graph.
- `offensia/reporting/generator.py` — report families.

## Key rule
Safety is enforced in code below the model. A model driving OffensIA cannot bypass
scope, fabricate a confirmed finding, or rewrite the ledger by prompting.
