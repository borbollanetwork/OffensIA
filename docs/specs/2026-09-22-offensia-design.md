# OffensIA — Design Specification

**Date:** 2026-09-22
**Status:** Approved (design phase)
**Repository:** private
**Consumption model:** MCP client + presets (Kimi K3, GLM)

---

## 1. Purpose and scope

OffensIA is a **private orchestration layer** for authorized offensive security
work (penetration testing, red team engagements, bug bounty, security research)
driven by an LLM operator — primarily Kimi (K2/K3) and GLM.

It does not reimplement scanners or exploit engines. It sits above existing
security engines and gives the LLM a single, governed interface with three
guarantees:

1. **Scope is law.** No target is acted on unless it is explicitly authorized in
   `scope.allow`. This is the primary safety control and is enforced in code, not
   prompt.
2. **Evidence over assertion (anti-hallucination).** A vulnerability only exists
   once it carries raw evidence and, ideally, a deterministic command that
   reproduces it. Claims without artifacts are rejected.
3. **Auditability.** Every tool call and finding is written to an append-only
   ledger per engagement. The operator cites the ledger, never memory.

### Success criteria

- An LLM client (Kimi or GLM) connects via MCP and can run a complete engagement
  loop: recon → hypothesis → deterministic proof → recorded finding → report.
- Any target outside `scope.allow` is refused automatically, with nothing executed.
- No finding enters the ledger without raw evidence.
- Adding, updating, or swapping an underlying engine does not change the
  `offensia_*` tool interface the model sees.

### Non-goals

- Not a hosted service; runs locally / in the operator's own environment.
- Not a replacement for written authorization from the target owner. OffensIA
  enforces scope; it does not grant permission.
- No built-in autonomous agent loop of its own in v1 — autonomy is delegated to a
  backend engine behind a single tool.

---

## 2. Architecture

Thin orchestration. OffensIA wraps external engines through **adapters** and
exposes a neutral, branded tool namespace (`offensia_*`) so the operator model
sees one consistent interface. External engines are consumed as **dependencies**
(git submodule / pip / Docker) under `deps/`; their source is **not** copied into
the OffensIA source tree, and their own `LICENSE`/`NOTICE` files remain intact in
their dependency directories.

```
/OffensIA/
├── core/                # offensia-core MCP server (governance)
│   ├── server.py        # scope, evidence gate, ledger, engagement lifecycle
│   ├── adapters/
│   │   ├── recon.py     # recon / content ingestion engine adapter
│   │   ├── exec.py      # deterministic tooling engine adapter
│   │   └── autonomous.py# sandboxed autonomous engagement adapter
│   ├── ledger.py        # append-only JSONL ledger
│   ├── scope.py         # scope.allow loader + matcher
│   └── doctrine_loader.py
├── doctrine/            # own methodology + skills (operator's content)
│   ├── INDEX.md
│   ├── TECHNIQUES.md
│   └── skills/
├── presets/
│   ├── kimi/            # kimi-mcp.json + env + system prompt
│   └── glm/             # glm-mcp.json + env + system prompt
├── deps/                # external engines (submodule/installer) — not in source
├── engagements/
│   └── <target>/        # ledger.jsonl, findings/, evidence/, report.md
├── scope.allow
├── offensia             # thin CLI (up / scope / engage / report)
├── install.sh
├── tests/
└── README.md            # OffensIA's own documentation
```

### Component responsibilities

- **core/server.py** — the only MCP surface the model talks to. Registers the
  `offensia_*` tools. Model-agnostic. Enforces scope + evidence + ledger on every
  call that touches a target.
- **core/adapters/** — one module per capability class. Each adapter translates a
  neutral OffensIA request into calls to a specific backend engine and normalizes
  the response into a single OffensIA result schema. Isolating the backend here is
  what lets engines be swapped/updated without changing the model-facing interface.
- **core/scope.py** — loads `scope.allow`, normalizes a target to a bare host, and
  matches against exact hosts and `*.domain` globs. Default deny.
- **core/ledger.py** — append-only writer/reader for
  `engagements/<target>/ledger.jsonl`.
- **doctrine/** — the operator's own methodology and on-demand skills, routed by
  `INDEX.md` / `TECHNIQUES.md`. Derived and rewritten as original content; no
  third-party skill files are packaged.
- **presets/** — per-model MCP configuration and tuned system prompts. The core is
  model-agnostic; anything model-specific lives here.

---

## 3. MCP tool interface (`offensia_*`)

All tools that name a target are scope-guarded and ledger-logged.

| Tool | Purpose |
|------|---------|
| `offensia_scope_list()` | List authorized targets. |
| `offensia_scope_add(target, authorization_ref)` | Add a target. Refused without an `authorization_ref` (contract id, ticket, bounty program handle, or `LAB`). |
| `offensia_recon(target, mode)` | Recon / real-content ingestion (page content, DOM, screenshots, service discovery). Produces raw fact into the ledger. |
| `offensia_exec(target, command)` | Run one deterministic security tool command. Scope-guarded, logged. |
| `offensia_finding(target, title, severity, raw_evidence, verify_command)` | Register a finding. Rejected without `raw_evidence`; marked `confirmed` only if `verify_command` reproduces the result, else `unconfirmed`. |
| `offensia_engage(target, instruction, scan_mode, max_budget, max_turns)` | Launch a sandboxed autonomous engagement with hard cost/turn ceilings. |
| `offensia_engage_status(target, run_id)` | Poll an autonomous run. |
| `offensia_ledger(target, n)` | Read the last n ledger records. |

### Result schema (normalized)

Every adapter returns:

```json
{
  "ok": true,
  "target": "<host>",
  "action": "recon|exec|engage|finding",
  "raw": "<verbatim engine output>",
  "summary": "<short normalized summary>",
  "ledger_ref": "<line id>"
}
```

`raw` is always preserved so downstream reasoning stands on verbatim output.

---

## 4. Data flow

```
LLM operator (Kimi / GLM via MCP)
   │
   ├─ offensia_scope_add(target, authorization_ref)   → scope.allow
   ├─ offensia_recon(target)   → recon adapter   → raw fact → ledger
   ├─ (form hypothesis from raw fact)
   ├─ offensia_exec(target, cmd) → exec adapter  → proof   → ledger
   ├─ offensia_finding(target, …, raw_evidence, verify_command)
   │        → evidence gate → deterministic re-check → ledger (confirmed/unconfirmed)
   ├─ offensia_engage(target, …) → autonomous adapter (sandbox, budget-capped)
   └─ offensia_ledger(target) → cite records for the report
```

Anti-hallucination discipline (enforced, not advisory):

1. Recon first; raw fact into the ledger before any claim.
2. Every vulnerability hypothesis is proven with a deterministic tool.
3. A finding exists only through `offensia_finding` with `raw_evidence`.
4. Out-of-scope target = automatic refusal.

---

## 5. Provider presets (Kimi + GLM)

- **presets/kimi/** — `kimi-mcp.json` in Kimi CLI format (`mcpServers` key,
  launched via `kimi --mcp-config-file`), plus env (`OFFENSIA_LLM`, provider key)
  and a system prompt tuned to Kimi.
- **presets/glm/** — `glm-mcp.json` in the GLM client's MCP config format (to be
  confirmed against the current GLM client before implementation), plus env and a
  GLM-tuned system prompt.

Both presets point at the same model-agnostic OffensIA core. Only configuration
and prompt wording differ per model.

---

## 6. Dependencies and installation

`install.sh` provisions the backend engines into `deps/` (git submodule or
pip/Docker) and verifies health. Because engines are referenced rather than
copied, upstream updates are pulled without touching OffensIA source, and each
engine's own license notices remain in place inside its dependency directory.

Backend capability classes required:

- **recon/ingestion** — an LLM-friendly crawler with an MCP interface.
- **deterministic tooling** — a security-tool server exposing common tools over an
  API/MCP interface.
- **autonomous engagement** — a sandboxed (Docker) autonomous pentest agent with
  budget/turn controls and its own MCP-client capability.

Adapters target these capability classes, so a specific engine can be replaced as
long as the class is satisfied.

---

## 7. Safety and authorization model

- `scope.allow` ships **empty**. Nothing runs until a target is added with an
  `authorization_ref`.
- Scope matching is default-deny, enforced in `core/scope.py` on every
  target-bearing call.
- Autonomous engagements always run in a Docker sandbox with hard `max_budget` and
  `max_turns` ceilings.
- OffensIA enforces scope; it does not constitute authorization. Written
  authorization from the target owner remains the operator's responsibility and is
  referenced via `authorization_ref`.
- If the repository is ever made public or the engine source is ever vendored into
  the tree, third-party MIT/Apache-2.0 notices become mandatory and must be added
  at that point.

---

## 8. Testing strategy

- **Unit** — scope matcher (exact + glob + default deny), evidence gate (reject
  without evidence; confirmed only on reproduction), ledger append/read, adapter
  normalization against mocked engines.
- **Refusal test** — out-of-scope target returns refusal and executes nothing.
- **Smoke** — `offensia up` boots the stack and passes a self-test;
  `offensia_recon` against a local lab target returns raw content and a ledger line.
- **Preset test** — Kimi and GLM MCP configs are valid and load.

---

## 9. Open items to confirm before/at implementation

- Exact GLM client MCP config format and the exact model ids for Kimi K3 and the
  target GLM model.
- Which provisioning method for `deps/` (git submodule vs installer script) fits
  the operator's workflow best.
- Whether v1 ships the autonomous engagement tool or defers it to v2 (core loop of
  recon → exec → finding → report is the minimum viable engagement).
