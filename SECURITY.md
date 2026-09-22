# Security Policy

## Authorized use only

OffensIA is offensive-security tooling. Use it exclusively against systems you are
explicitly authorized to test (a written contract, a scoped bug-bounty program, or
your own lab). Scope is default-deny and enforced in code; do not attempt to bypass
it. The operator is responsible for holding the authorization referenced by each
scope entry.

## Reporting a vulnerability in OffensIA

Report suspected vulnerabilities in OffensIA itself privately to the maintainers.
Do not open a public issue for a security report. Include a description, affected
version/commit, and reproduction steps.

## Platform threat model

OffensIA processes untrusted, potentially hostile content (target pages, tool
output, source). See `docs/threat-model.md` for the threats considered (indirect
prompt injection, malicious tool output, command injection, SSRF against the host,
secret leakage, supply-chain drift) and the implemented mitigations and residual
risks.

## Secrets

Never commit API keys or credentials. Provider keys belong in `.env` (git-ignored)
or your shell environment. Local services bind to `127.0.0.1` by default.
