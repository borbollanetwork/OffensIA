# Changelog

All notable changes to OffensIA are documented here. Format loosely follows
Keep a Changelog.

## [1.1.0] — 2026-09-22

### Added
- CI (GitHub Actions): ruff + mypy + bandit + pytest on Python 3.11/3.12/3.13.
- Lint/type/security tooling configured in pyproject; pinned engine commits in
  deps/engines.yaml with pinned-checkout in the installer.
- Doctrine cards for core and extended domains: web, api, mobile, internal/AD,
  cloud, containers/Kubernetes, code review, web3, iot, wireless, binary, research.
- Distilled cross-cutting doctrine: evidence ladder (validation states + chaining)
  and a contextual severity model beyond CVSS.
- Hardened Kimi/GLM operator system prompts (evidence-first, chaining discipline,
  high-risk safety gates, coverage honesty).
- Knowledge engine indexes title + bounded body tokens for accurate selective
  retrieval; reference engine for dependency-free end-to-end self-test.

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
