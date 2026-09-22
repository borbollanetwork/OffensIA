# OffensIA Doctrine — Source-Assisted Review

Applies when source code is authorized and available. Source turns black-box
guessing into targeted, evidence-backed testing: find the sink, trace the source,
then prove it at runtime. Code reading alone yields HYPOTHESIS, never a confirmed
finding — dynamic validation still applies.

## What to look for (source → sink)
- **Injection sinks**: raw SQL/command/template/deserialization calls fed by
  request data; trace taint from input to sink through the call graph.
- **AuthZ gaps**: endpoints/handlers missing an authorization check that peers
  have; object access without an ownership/tenant check (BOLA/IDOR in code).
- **Secrets & config**: hardcoded credentials, keys, tokens; insecure defaults;
  debug/back-door flags.
- **Crypto**: weak algorithms, static IVs/keys, homemade crypto, missing signature
  verification.
- **Trust boundaries**: where untrusted input crosses into a privileged operation;
  SSRF-prone outbound calls; unsafe file paths (traversal/upload).
- **Dependencies**: known-vulnerable or EOL libraries actually reachable from an
  entry point (reachability matters, not just presence).

## When it applies / preconditions
- Requires authorized access to the source. A confirmed finding requires linking
  the code path to a runtime demonstration against an in-scope deployment; if no
  runtime is reachable, cap the state at SUSPECTED and say so.

## Evidence required
- The exact file:line of the source and the sink, the taint path between them, and
  a runtime reproduction (request/response) against an authorized target — plus a
  negative control.
- Dependency finding: proof the vulnerable code path is reachable, not just the
  version string.

## Refuting false positives
A dangerous-looking sink guarded by an upstream sanitizer/validator is
FALSE_POSITIVE. A vulnerable dependency that is never reached is INFORMATIONAL.
"The code looks wrong" without a reachable, demonstrated effect is HYPOTHESIS.

## Chaining
Source review is a force multiplier: use it to generate precise hypotheses for the
other domains (web/api/cloud), then validate them there and record the evidence.
