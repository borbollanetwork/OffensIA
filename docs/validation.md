# Validation

The Validation Engine challenges findings; it can disagree with the primary
testing logic. A `Check` declares a command and an expectation:

- `expect="success"` — passes when the command reproduces the behavior.
- `expect="failure"` — passes when a control/benign input does NOT reproduce it
  (negative control).

Promotion policy (code-enforced, in `offensia/core/finding.py`):

| Target state | Requires checks |
|---|---|
| VALIDATED | reproduction, negative_control |
| EXPLOITABLE | reproduction, negative_control |
| CONFIRMED_IMPACT | reproduction, negative_control, impact_validation |

A finding with no evidence, or missing a required check, cannot be promoted — the
model cannot override this by asserting a result.
