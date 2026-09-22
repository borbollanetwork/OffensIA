<p align="center">
  <img src="assets/banner.png" alt="OffensIA" width="100%">
</p>

# OffensIA

[![CI](https://github.com/borbollanetwork/OffensIA/actions/workflows/ci.yml/badge.svg)](https://github.com/borbollanetwork/OffensIA/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Evidence-driven, model-agnostic offensive-security orchestration platform for
authorized pentests. Scope-is-law (default-deny), evidence-gated findings with a
validation state machine, and a hash-chained audit ledger — safety enforced in
code, not prompts. MCP-native for Kimi & GLM. Created by Renato Borbolla.**

OffensIA turns a disciplined offensive-security methodology into a governed,
model-agnostic platform an LLM operator (Kimi / GLM) drives through a single MCP
interface. It is built around three guarantees enforced in code, not by prompt:

1. **Scope is law** — default-deny; nothing runs against a target that is not
   explicitly authorized.
2. **Evidence over assertion** — a finding is confirmed only through a validation
   lifecycle backed by real artifacts; the model can never self-declare impact.
3. **Auditability** — an append-only, hash-chained ledger records every action; the
   operator cites references, never model memory.

OffensIA is not a "scanner + LLM summary." The intelligence lives in planning,
adaptive testing, coverage control, evidence correlation, validation, and
false-positive elimination. Tools are sensors and actuators.

> **Authorized use only.** OffensIA enforces scope; it does not grant permission.
> Use it only against systems you are authorized to test.

## Architecture

Three planes, deliberately decoupled:

- **Control plane** — scope, policy, assessment state, coverage, capability
  registry, providers, knowledge retrieval (`offensia/core`, `offensia/providers`,
  `offensia/knowledge`).
- **Execution plane** — the MCP gateway and adapters that reach external tool
  engines behind a neutral capability interface (`offensia/core/server.py`,
  `offensia/adapters`).
- **Evidence plane** — hash-chained ledger, content-addressed evidence store,
  finding state machine, attack graph, reporting (`offensia/core/ledger.py`,
  `evidence.py`, `finding.py`, `attack_graph.py`, `offensia/reporting`).

External engines are consumed as **dependencies** declared in `deps/engines.yaml`
and reached only through adapters — never vendored into this repository.

## Install (one command)

```bash
git clone <your-private-repo> OffensIA
cd OffensIA
./install.sh kimi          # or: ./install.sh glm
```

The installer runs preflight → creates a venv → installs the package → provisions
the engines from the pinned manifest → registers the OffensIA MCP server into your
agent config (with backup, atomic write, and abort-on-malformed) → runs health and
self-test. Then start your agent — the `offensia_*` tools are available.

## Configure

- **Kimi / GLM:** presets live in `offensia/presets/kimi/` and `offensia/presets/glm/`
  (MCP config + hardened system prompt). Model identifiers are configurable via
  `OFFENSIA_MODEL_ID` / `KIMI_MODEL_ID` / `GLM_MODEL_ID` — OffensIA never invents an
  identifier. See `.env.example`.
- **Register MCP manually:** `offensia agent register --agent-config <path>`
  (undo with `offensia agent unregister --agent-config <path>`).

## Use

```bash
offensia scope add app.authorized.example --auth CONTRACT-2026-001  # authorize first
offensia assessment create eng-42
# ...drive the engagement from your LLM agent via offensia_* tools...
offensia coverage show eng-42
offensia ledger verify eng-42
offensia report technical eng-42
offensia resume eng-42            # resumable state
offensia knowledge index ./doctrine
offensia doctor                   # actionable diagnostics
```

### How evidence validation works
A finding starts in a non-confirming state anchored to a stored `evidence_id`.
`offensia_validate_finding` runs reproduction and negative-control checks through
the scope-guarded execution adapter. Promotion to `VALIDATED` / `EXPLOITABLE` /
`CONFIRMED_IMPACT` is code-enforced from the checks that actually pass — the model
cannot promote a finding by asserting it.

## Extending

- **Add an adapter:** implement a module under `offensia/adapters/<class>/` exposing
  the capability functions, then bind its `PROVIDER_KEY` in the capability registry.
- **Add a provider:** subclass `BaseModelProvider` in `offensia/providers/` with its
  `ProviderMetadata`; keep offensive methodology out of provider code.

## Documentation

See `docs/` — architecture, installation, configuration, providers, MCP, scope,
evidence, validation, coverage, knowledge, threat model, development.

## Status

First production-oriented build. The autonomous engagement engine is deferred to a
later milestone; its interface exists via the capability registry. See
`docs/LIMITATIONS.md` for what is fully implemented versus interface-only.

## Author & Credits

Created by **Renato Borbolla** — https://renatoborbolla.com

If you improve, clone, or fork this project, please give due credit to the author
(Renato Borbolla), keeping this attribution and a link to https://renatoborbolla.com
in your copy or derivative work.
