# OffensIA Doctrine — Internal Network & Active Directory

Applies to internal/assumed-breach engagements. Intelligence is in mapping trust
and identity relationships, not in running one more scanner. Everything active is
scope-guarded; internal ranges must be explicitly authorized (CIDR entries).

## What to look for
- **Discovery**: live hosts, services, OS/version, shares, default/weak creds,
  segmentation boundaries. Map, don't spray.
- **Identity (AD)**: users, groups, delegation (unconstrained/constrained/RBCD),
  Kerberos issues (AS-REP roasting, Kerberoasting), SMB signing, LDAP exposure,
  ADCS misconfigurations (vulnerable templates), GPO abuse, ACL paths to privileged
  principals.
- **Credential exposure**: files/shares with secrets, LSASS-adjacent risks,
  service-account passwords, cached creds.
- **Privilege boundaries**: local admin sprawl, trust between domains/forests,
  paths from a low-priv principal to Domain Admin / Enterprise Admin.
- **Lateral movement surface**: reachable admin interfaces, PSRemoting/WMI/SMB
  exposure between segments.

## When it applies / preconditions
- Active enumeration requires authorized internal scope (host/CIDR) and, for AD,
  at least one foothold identity. Privilege-escalation claims require the two
  identity contexts (before/after) to demonstrate the boundary crossing.

## Evidence required
- A relationship claim (e.g. "user A can reset user B's password"): the ACL/graph
  data plus a demonstrated or safely-validated effect, with a negative control
  showing a non-privileged principal cannot.
- Roasting: the requested ticket/hash artifact (handled per rules of engagement),
  not merely "the account is kerberoastable."

## Refuting false positives
A theoretical path in the graph is HYPOTHESIS until preconditions are shown to
hold. A weak-signing setting is HARDENING unless an actual relay/abuse is
demonstrated within scope. Never assert Domain Admin without the concrete access.

## Chaining
Model each step as an attack-graph edge (`can_assume`, `escalates_to`,
`authenticates_as`) with evidence and preconditions, then reason about the shortest
path to the objective — that path is the finding, not the isolated misconfig.
