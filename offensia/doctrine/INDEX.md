# OffensIA Doctrine — Index

Original OffensIA methodology. Loaded selectively by the Knowledge Engine — never
injected wholesale into model context. Each card explains what to look for, when a
test applies, which preconditions matter, what evidence is required, and how a
false positive is refuted.

- `lifecycle.md` — the OffensIA assessment lifecycle and invariants (read first)
- `web.md` — web application attack surface
- `api.md` — API attack surface (REST/GraphQL/gRPC)
- `mobile.md` — Android/iOS clients and their backends
- `internal.md` — internal network and Active Directory
- `cloud.md` — AWS / Azure / GCP identity and exposure
- `containers.md` — containers and Kubernetes (activated on discovery)
- `code-review.md` — source-assisted review feeding the other domains
- `research.md` — novel-vulnerability research discipline

Every card shares the same shape: what to look for, when it applies and its
preconditions, the evidence required to confirm, how a false positive is refuted,
and how findings chain in the attack graph. Cards are guidance for generating and
proving hypotheses — a finding is still confirmed only through the evidence-backed
validation lifecycle.

Cross-cutting invariants live in `lifecycle.md` and always win over any card.
