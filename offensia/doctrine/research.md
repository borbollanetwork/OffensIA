# OffensIA Doctrine — Novel Vulnerability Research

Novelty is a strong claim. Do not call an anomaly a zero-day because a CVE lookup
did not immediately match it.

## Lifecycle
```
ANOMALY -> REPRODUCIBLE_ANOMALY -> SECURITY_RELEVANT_BEHAVIOR ->
VULNERABILITY_CANDIDATE -> VALIDATED_VULNERABILITY ->
KNOWN-VULNERABILITY CORRELATION -> POTENTIAL_NOVEL_VULNERABILITY
```

The objective is to detect **"this behavior violates the expected security
invariant"** before asking **"which known vulnerability is this?"**

## Authorized methods
Differential analysis, state-machine analysis, authorization differential testing,
parser differential testing, boundary analysis, input mutation, protocol edge-case
testing, race-condition investigation, invariant-violation checks, source-assisted
review, fuzzing where explicitly authorized, crash triage, behavior comparison,
semantic error-state analysis.

## Discipline
- Every step produces evidence in the ledger; the anomaly must reproduce.
- Correlate against known vulnerabilities before claiming novelty.
- A potential novel finding is always reported with explicit uncertainty and the
  exact invariant it violates.
