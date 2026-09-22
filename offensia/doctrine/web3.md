# OffensIA Doctrine — Web3 / Smart Contracts

Applies to smart contracts, on-chain protocols, and the off-chain infrastructure
(RPC, indexers, bridges, front-ends) around them. On authorized engagements prefer
a fork/testnet: value moves are irreversible, so never test economic exploits
against mainnet funds. Reading source (usually available) plus local simulation is
the core loop; see `code-review.md`.

## What to look for
- **Access control**: missing/incorrect `onlyOwner`/role checks, unprotected
  initializers, ownership-transfer flaws, privileged upgrade paths.
- **Arithmetic & accounting**: rounding/precision loss, fee-on-transfer and rebasing
  mismatches, share/price inflation, unchecked math in older compilers.
- **Reentrancy**: single-function, cross-function, and read-only reentrancy; state
  updated after external calls (violates checks-effects-interactions).
- **Oracle/price manipulation**: spot-price reliance, flash-loan-assisted skew,
  manipulable TWAP windows.
- **Upgradeability & proxies**: storage-collision, uninitialized implementation,
  `delegatecall` to attacker-influenced code, selector clashes.
- **Bridges & cross-chain**: message verification, replay across chains, signer/quorum
  assumptions.
- **MEV / ordering**: front-running, sandwiching, and unfair ordering where it maps to
  a security or fairness invariant.
- **Off-chain**: RPC exposure, key management, signature replay, front-end/wallet
  interaction (bridge into `web.md`).

## When it applies / preconditions
- A confirmed economic exploit requires a reproduction on a fork/testnet with a
  before/after state (attacker balance/authorization changes) and a negative control
  (a well-behaved actor cannot). Reading the contract yields HYPOTHESIS only.

## Evidence required
- The exploit transaction/script, the state diff it produces, the invariant it
  violates, and the negative control — captured from the fork/testnet run.

## Refuting false positives
A pattern that "looks reentrant" guarded by a mutex/nonReentrant or CEI ordering is
FALSE_POSITIVE. A privileged function is OBSERVATION until an unauthorized principal
is shown to call it. Never present a theoretical drain as a demonstrated one.

## Chaining
Oracle skew → undercollateralized borrow → protocol insolvency; or upgrade flaw →
implementation swap → fund control. Model each hop as an attack-graph edge with the
on-fork evidence and preconditions.
