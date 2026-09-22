# OffensIA Doctrine — Severity Model

Severity is **contextual risk**, calibrated independently from the validation state
(see `evidence-ladder.md`). A finding's severity never comes from a vulnerability
name or a CVSS number alone, and a scanner's label is never the severity.

## Calibrate on these factors
- **Exploitability** — how reliably the primitive works in practice.
- **Preconditions** — how realistic the required state/identity/position is.
- **Required privileges** — unauthenticated vs low-priv vs already-admin.
- **Attack complexity** — steps, timing, and reliability needed.
- **Exposure** — external internet-facing vs internal vs local only.
- **Blast radius** — how much (and whose) data/systems are reachable.
- **Data sensitivity** — what is exposed if the impact lands.
- **Tenant boundaries** — cross-tenant / cross-account effects raise severity.
- **Chaining** — does it enable or extend an attack path (see below)?
- **Persistence** — can the attacker keep access?
- **Existing controls** — segmentation, MFA, WAF/EDR, allow-lists that reduce it.
- **Detectability** — whether the action is observed (informational for defenders).

## CVSS
Use CVSS as one input and a communication aid, not the verdict. Report it where
appropriate, but the OffensIA severity is the contextual judgment above.

## Interaction with the ladder
- Severity is assessed only for findings at `VALIDATED` or above; below that, a
  finding carries a hypothesis-level risk note, not a final severity.
- Raising severity via a chain is allowed only when the chain **demonstrably**
  changes exploitability, blast radius, or business impact. Do not sum CVSS across
  links, and do not inflate risk with speculative links.

## Completeness language
Never state "no vulnerabilities" or "all found." Report severity within the
executed coverage, and always surface untested / blocked / unknown areas alongside
confirmed risk (see `coverage.md`).
