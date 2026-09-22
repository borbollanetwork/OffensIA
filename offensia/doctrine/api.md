# OffensIA Doctrine — API Attack Surface

Applies to REST, GraphQL, gRPC, SOAP, WebSocket, and custom APIs.

## What to look for
BOLA, BFLA, object-property authorization, mass assignment, authentication and
authorization, JWT/OAuth, rate limiting, business logic, excessive data exposure,
schema abuse, shadow and deprecated APIs, multi-tenancy, webhooks, race conditions,
state transitions.

## Method
Build an authorization matrix where possible:

```
role x endpoint x method x object x ownership x state
```

For each cell, the hypothesis is "context A can perform an action only context B
should." Evidence requires the A request, the B baseline, and a negative control
showing the boundary normally holds.

## GraphQL / gRPC
When GraphQL is discovered, activate schema introspection review, query-depth and
batching abuse, and field-level authorization. For gRPC, review reflection
exposure and method-level authorization. Evidence is always the concrete
request/response pair stored in the evidence plane.
