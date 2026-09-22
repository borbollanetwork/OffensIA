# OffensIA Doctrine — Evidence Ladder & Validation Flow

Always separate the **validation state** of a finding (how well it is proven) from
its **contextual severity** (how much it matters — see `severity.md`). This card
maps evidence quality to the finding state machine (`offensia/core/finding.py`).

## Golden rule
A scanner alert, an accepted payload, an error, a crash, or the absence of an alert
is not, by itself, proof. Promotion is driven by evidence, reproducibility,
exploitability, context, and confirmed impact — never by tool output alone.

## The ladder (validation state)

| State | Meaning | Minimum to reach it |
|---|---|---|
| INFORMATIONAL | useful fact, no security flaw shown | an observation |
| HARDENING | defensive improvement, no exploitability shown | a config/observation |
| OBSERVATION / HYPOTHESIS | a surface fact / a testable theory | recorded, with preconditions |
| SUSPECTED | plausible signal, not yet validated | at least one evidence artifact |
| VALIDATED | insecure behavior reproduced & demonstrated | reproduction + negative control |
| EXPLOITABLE | usable primitive with confirmed technical effect | reproduction + negative control |
| CONFIRMED_IMPACT | serious impact, realistic preconditions, real reach | reproduction + negative control + impact validation |
| FALSE_POSITIVE / INCONCLUSIVE | refuted / evidence ambiguous | control separates, or does not |

`SUSPECTED` is not `VALIDATED`; `VALIDATED` is not automatically `CONFIRMED_IMPACT`.
The code enforces these gates — a model cannot skip them by asserting a result.

## Validation flow (apply per test class, any domain)
```
surface -> baseline & negative control -> hypothesis ->
lowest-noise controlled test -> confirm the technical effect ->
false-positive control -> reproducible evidence ->
exploitability & impact assessment -> root cause -> retest bypass classes
```

## Evidence record (per item)
Target · hypothesis · expected vs observed · oracle · negative control ·
reproducible evidence (request/response, logs, hashes, timestamps, sanitized) ·
next step. Each artifact proves one specific claim and is traceable to its test and
its ledger event.

## Chaining (only confirmed findings)
Model each validated finding with `requires` (preconditions) and `grants`
(capability obtained). Create an attack-graph edge only when a prior finding's
`grant` satisfies the next finding's `require` — shared theme, same-host CVEs, or
same-scanner output are NOT a chain. Validate reachability, identity, privilege,
and a negative control at every hop; evidence for one step never proves the next.
Execute only the minimal link that demonstrates the transition, and stop when
impact is safely proven, the next link leaves scope, or evidence does not support
the transition.
