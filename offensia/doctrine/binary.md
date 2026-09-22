# OffensIA Doctrine — Binary & Exploit Development

Applies to native binaries, services, and their memory-safety behavior. Work in an
authorized, isolated environment (lab/sandbox); crashes and exploit attempts run
against the engagement's own instances, never shared production. Static review plus
controlled dynamic analysis is the loop — a crash is a starting point, not a finding.

## What to look for
- **Memory safety**: buffer/stack/heap overflows, use-after-free, double-free,
  type confusion, off-by-one, integer overflow feeding allocation/length.
- **Input handling / parsers**: length/bounds checks, format strings, unsafe copies,
  deserialization of native structures.
- **Mitigations present**: ASLR, DEP/NX, stack canaries, RELRO, CFI/CET — assess what
  actually applies to the target and how it constrains exploitability.
- **Primitives**: from a crash, what does the bug give — controlled read, controlled
  write, control-flow hijack — and how reliable is it.
- **Attack surface**: which inputs reach the vulnerable code (reachability from an
  entry point matters, like `code-review.md`).

## When it applies / preconditions
- Requires an authorized binary/service and an isolated environment. A confirmed
  finding requires a reproducible crash tied to a specific input, with triage
  identifying the bug class; an EXPLOITABLE claim requires a demonstrated primitive
  (e.g. controlled PC / arbitrary write) — not "it crashed."

## Evidence required
- The crashing input, the reproduction steps, the triage (fault type, faulting
  instruction, controllability), and — for EXPLOITABLE — a proof-of-concept
  demonstrating the primitive, with the mitigations that were in effect noted.

## Refuting false positives
A crash under a debugger is OBSERVATION until triaged; many crashes are non-security
(null deref without controllability). A memory bug behind a mitigation that fully
neutralizes it may be HARDENING, not EXPLOITABLE. State the exploitability honestly,
including uncertainty.

## Novel research & chaining
Follow `research.md`: reproducible anomaly → security-relevant behavior → validated
vulnerability → known-vuln correlation → potential novel finding, with explicit
uncertainty. Chain only demonstrated primitives (e.g. info-leak defeating ASLR →
write primitive → control flow), each hop evidenced in the attack graph.
