# Threat Model — OffensIA itself

OffensIA processes untrusted, potentially hostile input and orchestrates powerful
tools. This documents the threats considered and the mitigations implemented, plus
residual risk.

| Threat | Mitigation | Residual risk |
|---|---|---|
| Indirect prompt injection (target pages, tool output) | Untrusted content is fenced (`offensia/core/untrusted.py`) and flagged when injection patterns appear; system prompts forbid obeying it | A novel phrasing may evade the pattern; content is still shown fenced, not executed |
| Malicious tool output | Bounded output; structured errors; never executed as instructions | Very large/binary output is truncated (bounded), possibly losing detail |
| Model bypassing safety by prompt | Scope, promotion, and ledger are enforced in code below the model | A bug in the enforcement code; covered by tests |
| Command injection via crafted args | Adapters send explicit commands; no `shell=True` in safety paths | The external engine's own command handling is out of OffensIA's control |
| SSRF against the OffensIA host | Local engines bind to 127.0.0.1 by default; scope limits targets | An engine misconfigured to 0.0.0.0 by the operator |
| Secret leakage | `.env` git-ignored; keys never committed; `.gitignore` covers `*.key`/`*.pem` | Operator committing secrets manually |
| Supply-chain / dependency drift | Pinned manifest (`deps/engines.yaml`); adapters isolate upstream APIs | Unpinned `commit` fields fall back to a branch (warned by installer) |
| Ledger tampering | Hash-chained events; `offensia ledger verify` | An attacker with write access could rewrite the whole chain consistently; store off-host for high assurance |
| Malformed agent config overwrite | Registration aborts on malformed existing config and preserves it | None known |

## Residual-risk summary
- The autonomous engagement engine is deferred; when added it must sit above these
  controls and bypass none of them.
- OffensIA enforces scope but cannot verify that the operator actually holds the
  authorization referenced by a scope entry.
