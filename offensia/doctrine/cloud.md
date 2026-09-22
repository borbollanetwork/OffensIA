# OffensIA Doctrine — Cloud (AWS / Azure / GCP)

Applies to cloud accounts, subscriptions, and projects. Cloud security is mostly an
identity-and-trust problem: who can assume what, and what that reaches. Enumeration
and any state change must be authorized in scope; prefer read-only enumeration and
explicitly flag any mutating action.

## What to look for
- **IAM**: over-permissive roles/policies, wildcard actions, privilege-escalation
  primitives (pass-role, policy-version, create-access-key on others), unused but
  dangerous permissions.
- **Trust relationships**: cross-account role assumption, external principals,
  federation/OIDC trust (e.g. CI providers assuming roles), confused-deputy setups.
- **Exposure**: public storage buckets/blobs, snapshots, databases, management
  interfaces; overly open network rules/security groups.
- **Secrets**: keys in metadata, user-data, environment, functions, or repos.
- **Metadata service**: SSRF reaching IMDS → temporary credentials (correlate with
  `web.md` SSRF findings).
- **Kubernetes** (see `containers.md`), serverless functions, and CI/CD identity.
- **Logging/detection context**: whether the action would be observed (informational
  for the defender-facing report).

## When it applies / preconditions
- Enumeration requires authorized credentials/role and the account in scope. A
  privilege-escalation claim requires demonstrating (or safely validating) the
  escalation with a before/after identity, not just a permission listing.

## Evidence required
- IAM esc: the policy/permission data PLUS the performed or dry-run-validated
  escalation, with a negative control (a principal without the permission cannot).
- Public exposure: the unauthenticated request and its successful response, scoped
  to authorized resources.

## Refuting false positives
A broad policy is OBSERVATION until an escalation or reachable impact is shown.
"Bucket looks public" is SUSPECTED until an unauthenticated read/list actually
succeeds. Provider-side compensating controls can make a scary-looking permission a
FALSE_POSITIVE.

## Chaining
SSRF → IMDS → temporary credentials → assumed role → reachable data/other account.
Each hop is an attack-graph edge with evidence; the chain is the finding.
