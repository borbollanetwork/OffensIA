# OffensIA Doctrine — Web Attack Surface

Applies when the target exposes HTTP(S) applications. Map before testing; let
discovered technology activate deeper coverage (JWT, OAuth/OIDC, GraphQL,
WebSocket).

## What to look for (families)
Authentication, session management, access control and IDOR/BOLA, multi-tenant
isolation, business logic, injection classes, XSS, CSRF, SSRF, XXE, SSTI,
deserialization, file upload, path traversal, LFI/RFI, open redirect, CORS/CSP,
JWT, OAuth/OIDC/SAML, GraphQL, WebSocket, request smuggling/desync, host-header
attacks, prototype pollution, cache poisoning, cryptography and secrets,
information disclosure.

## Preconditions and evidence
- Access control / IDOR: requires at least two distinct authenticated contexts
  (roles or owners). Evidence = the two requests and their differing responses,
  plus a negative control proving the boundary normally holds.
- Injection: evidence = the payload, the differential response, and a negative
  control with a benign input.
- SSRF: evidence = an out-of-band or reflected indication that the server made the
  request; correlate into the attack graph toward internal resources.

## Refuting false positives
A scanner alert is at most SUSPECTED. Promote only after reproduction plus a
negative control that behaves differently. If controls do not separate, mark
INCONCLUSIVE — never CONFIRMED.
