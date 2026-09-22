# Changelog

All notable changes to OffensIA are documented here. Format loosely follows
Keep a Changelog; this project uses semantic-ish versioning while pre-1.0.

## [0.1.0] — 2026-09-22

First production-oriented build.

### Added
- Three-plane architecture (control / execution / evidence).
- Default-deny scope engine with target normalization, domain globs, CIDRs,
  exclusions, and authorization metadata.
- Append-only, hash-chained evidence ledger with integrity verification.
- Content-addressed evidence store; findings reference evidence, not model memory.
- Finding lifecycle state machine with code-enforced, validation-gated promotion.
- Validation engine (reproduction, negative controls) that can refute findings.
- Coverage engine with adaptive activation by discovered technology.
- Attack graph (SQLite) with evidence-bearing edges and path enumeration.
- Capability registry decoupling the planner from upstream engine APIs.
- Execution and recon adapters with bounded, normalized output and no crash-through.
- MCP server exposing neutral `offensia_*` tools through the full safety pipeline.
- Provider abstraction (Kimi, GLM) with configurable, never-invented model ids.
- Knowledge engine (discover/classify/index/selective-retrieve) with KNOWLEDGE_GAP.
- Reporting (executive/technical/evidence/coverage) with honest completeness language.
- One-command installer; non-destructive, abort-on-malformed agent registration.
- CLI: init, doctor, status, scope, assessment, resume, coverage, ledger verify,
  finding, report, agent register/unregister, engines status, knowledge index.
- Original OffensIA doctrine; hardened Kimi/GLM system prompts.
- Pinned engine dependency manifest.
- Test suite for safety-critical components.

### Deferred
- Autonomous engagement engine (interface present via capability registry).
