# AsyncSwap State Machine Spec v1 (USD-Value Fairness)

This document is intended to be readable by someone who has not followed the prior design discussion. It should explain:

- what AsyncSwap is trying to guarantee
- what state the protocol must track
- what actions can happen
- what must always remain true
- what the protocol assumes about the world around it

If the short summary is enough, read the **Summary** section. If you need the full model, continue through the detailed sections below.

## Terminology

- **order**: a user instruction to exchange one asset for another under protocol rules
- **swapper**: the user who opens the order and escrows input
- **filler**: the counterparty / solver who delivers output and earns input claims
- **keeper**: a third party allowed to clean up expired orders
- **input**: the asset the user escrows
- **output**: the asset the user expects to receive from a filler
- **fee**: protocol revenue taken according to the configured fee policy
- **surplus**: excess value extracted from a bad quote relative to a trusted fair-value reference
- **user rebate**: the part of captured surplus reserved for the user rather than the filler or treasury
- **common numeraire**: the shared value unit used to compare assets, currently intended to be USD-like
- **oracle**: an external trusted value source used to estimate fair value
- **governance**: the token-voting and timelock system that controls protocol policy

## Summary

### Principle

**AsyncSwap V1 exists to ensure users do not silently lose value on bad quotes. When trusted value references are available, the protocol can refund users, internalize MEV, and route excess value according to explicit policy.**

### State

- store token amounts as primary state
- derive common-value / USD accounting from those amounts
- track per-order state, global protocol state, oracle state, reward state, and governance state

The key simplification is that the protocol stores **amounts**, while value fairness is computed as a **derived interpretation** of those amounts using trusted references.

### Actions

- split the system into two layers:
  - core protocol actions
  - governance actions
- core actions cover open, fill, batch fill, cancel, fee claim, and surplus claim
- governance actions cover policy updates, rewards, proposals, voting, queueing, and execution

This two-layer split matters because it separates:

- the economic mechanics of the protocol itself
- the political control plane that is allowed to tune protocol policy

### Invariants

- input conservation
- value conservation
- output conservation
- non-negativity
- no double claim
- user rebate recoverability
- filler payout boundedness
- user loss boundedness
- protocol capture boundedness
- expiry safety
- pause safety
- governance legitimacy
- governance execution safety

### Oracle

- oracle trust is an external assumption, not a protocol invariant
- what we verify is the protocol’s behavior given oracle inputs
- if oracle data is missing or stale, behavior must still be deterministic

The v1 direction assumes that fair execution is judged in a common value unit when trusted references exist, but the protocol should remain live even when oracle data is unavailable.

### Governance

- governance is part of the protocol model, not an afterthought
- token voting, proposals, timelock queueing, and execution all belong in scope
- governance controls policy, but protocol invariants still constrain what those policy changes can do

In other words: governance is powerful, but not unconstrained. The formal model exists partly to define those constraints.

### Current Direction

- this is a V1 spec
- fairness is evaluated in a common value unit
- governance-controlled policy is live at execution time
- the protocol should remain simple in implementation even if the model is richer in analysis

This document is a plain-English formalization target for AsyncSwap v1. It is intentionally written before any TLA+ syntax so the protocol model can be reviewed and corrected first.

The goal is to define:

- the protocol state
- the allowed actions
- the safety invariants that must always hold
- the liveness assumptions we rely on
- the policy questions that still need explicit decisions

This spec reflects the intended v1 design direction:

- asynchronous escrowed orders
- partial fills
- fee modes (`upfront` and `on-fill` / refund toggle)
- expiry and keeper cancellation
- token/USD oracle-based surplus capture
- governance-controlled policy parameters

The central principle of v1 is:

> users should not silently lose value because of bad quotes; any excess value transfer should be measurable in a common numeraire and routed by explicit protocol policy.

---

## 1. Core Model

AsyncSwap is an async intent protocol.

A user opens an order by escrowing input. Fillers later deliver output and receive a claim on the escrowed input. If the order is never fully filled, the remaining input can be cancelled back to the user (or cleaned up by a keeper after expiry).

The protocol may also:

- charge protocol fees
- measure value in a common USD-like numeraire
- capture surplus / MEV from bad user quotes in value terms
- route captured value between user, filler, and treasury according to governance policy

This means AsyncSwap is not only a settlement mechanism. It is also a policy engine for deciding how value should move when quotes are materially unfair.

### v1 Fairness Rule

For any fill where trusted token/USD prices are available, the protocol should be able to answer:

- how much value the user gave up
- how much value the user received
- whether the quoted execution transferred excess value away from the user
- how that excess value is split between user, filler, and treasury

This fairness rule is the defining economic property of the v1 design.

---

## 2. State Variables

### 2.1 Per-order state

For each order `o`:

- `originalInput[o]`
- `originalOutput[o]`
- `remainingInput[o]`
- `remainingOutput[o]`
- `filledInput[o]`
- `deliveredOutput[o]`
- `feeRemaining[o]`
- `feeAccrued[o]` (optional accounting view; may also be derivable)
- `surplusAccrued[o]` (optional accounting view; may also be derivable)
- `userRebateAccrued[o]`
- `deadline[o]`
- `cancelled[o]`

These variables are the primary state needed to model what the user put in, what has already been executed, and what can still happen to the order.

### 2.2 Per-order value state

For each order `o`, the protocol should be able to reason about value in a common numeraire (e.g. USD x 1e18):

- `originalInputValue[o]`
- `deliveredOutputValue[o]`
- `remainingInputValue[o]`
- `remainingOutputValue[o]`
- `protocolFeeValue[o]`
- `protocolSurplusValue[o]`
- `fillerValue[o]`
- `userRebateValue[o]`

These are derived-value quantities rather than required onchain storage. They exist so the formal model can talk about fairness and loss in a way users actually understand.

### 2.3 Global protocol state

- `paused`
- `minimumFee`
- `poolFee[poolId]`
- `feeRefundToggle`
- `treasury`
- `accruedFees[currency]`
- `accruedSurplus[currency]`

These variables represent protocol-wide policy and accounting rather than any single order.

### 2.4 Oracle state

Per token:

- `oracleAdapter[token]`
- `oracleMaxAge[token]`

Or equivalently via an adapter layer that can price tokens in a common unit.

Per pool policy:

- `oracleMaxDeviationBps[poolId]`
- `userSurplusBps[poolId]`
- `fillerSurplusBps[poolId]`
- `protocolSurplusBps[poolId]`

The preferred direction is now a **USD-normalized fair-value model**:

- each token has a USD (or USD-like) reference price
- the protocol compares the value of what the user gives vs what the user receives
- surplus capture is defined in common-value terms, not pair-relative quote terms

This is the core architectural choice that makes v1 different from a purely pair-relative pricing system.

### 2.5 Reward state

Per address:

- `hasSwapReward[address]`
- `hasFillerReward[address]`
- `hasKeeperReward[address]`

### 2.6 Governance state

For the governance token and proposal system:

- `tokenBalance[address]`
- `delegatedVotes[address]`
- `minter`
- `maxSupply`

For proposal lifecycle:

- `proposalId`
- `proposalTargets`
- `proposalCalldata`
- `proposalState` (`Pending`, `Active`, `Succeeded`, `Queued`, `Executed`, `Canceled`)
- `proposalSnapshotBlock`
- `proposalDeadlineBlock`
- `timelockDelay`
- `queuedExecutionTime`

This state determines how governance decisions become valid state transitions on the core protocol.

Without modeling this layer, the protocol model would be incomplete because governance is explicitly allowed to tune policy.

---

## 3. Actions

The action model is intentionally split into two layers:

- **Layer 1: core protocol actions** — escrow, fill, batch fill, cancel, fee/surplus claims
- **Layer 2: governance actions** — token voting, proposal lifecycle, timelock execution, and policy updates

This separation allows economic correctness and governance control to be reasoned about independently before they are composed.

The goal is to make it clear which actions move value and which actions only change policy.

### 3.1 `OpenOrder`

Inputs:

- user
- direction
- amountIn
- target quote (tick / price)
- minAmountOut
- optional deadline

Effects:

- escrows input
- computes quoted output
- initializes or accumulates order state
- may charge fee immediately (upfront mode)
- may mint a one-time swapper reward

### 3.2 `FillOrder`

Inputs:

- filler
- order
- fillOutputAmount

Effects:

- checks remaining balances
- checks minimum fill threshold
- checks expiry
- computes proportional input share
- computes fee effects (depending on fee mode)
- computes input/output value in common USD terms
- optionally computes oracle surplus capture in value terms
- delivers output to swapper
- transfers input claim to filler
- may mint a one-time filler reward

This is the most economically important transition in the system.

### 3.3 `BatchFill`

Inputs:

- filler
- arrays of orders / directions / fill amounts

Effects:

- equivalent to multiple `FillOrder` operations in one transaction
- must preserve economic consistency with sequential execution

### 3.4 `CancelByUser`

Inputs:

- swapper
- order

Effects:

- returns remaining input to the swapper
- clears remaining order state
- unfilled fees may or may not be forgiven depending on fee mode policy

### 3.5 `CancelByKeeper`

Inputs:

- keeper
- expired order

Effects:

- only allowed after expiry
- returns remaining input to the swapper
- may mint a one-time keeper reward
- does not redirect user funds to the keeper

### 3.6 `ClaimFees`

Inputs:

- treasury / caller
- currency

Effects:

- treasury receives accrued protocol fees
- accrued fee balance decreases accordingly

### 3.7 `ClaimSurplus`

Inputs:

- treasury / caller
- currency

Effects:

- treasury receives accrued protocol surplus
- accrued surplus balance decreases accordingly

### 3.8 Governance actions

- `SetPoolFee`
- `SetFeeRefundToggle`
- `SetOracleConfig`
- `SetTreasury`
- `Pause`
- `Unpause`
- ownership transfer actions

These must not corrupt any live order accounting.

### 3.9 Governance token actions

- `MintRewardToken`
- `DelegateVotes`
- `TransferToken`
- `SetMinter`

These actions affect governance power distribution and who can create or execute future proposals.

### 3.10 Proposal lifecycle actions

- `CreateProposal`
- `CastVote`
- `QueueProposal`
- `ExecuteProposal`
- `CancelProposal`

These actions must preserve governance legitimacy and timelock ordering.

---

## 4. Safety Invariants

The v1 spec keeps the following 13 invariants as the baseline set.

These invariants are the core claims the protocol should be able to defend under all valid executions.

### 4.1 Input conservation

For each order:

`originalInput = remainingInput + refundedInput + fillerPayout + protocolFee + protocolSurplus`

No input value may be created or destroyed.

### 4.2 Value conservation

For each order, measured in the common numeraire:

`originalInputValue = remainingInputValue + refundedInputValue + fillerValue + protocolFeeValue + protocolSurplusValue`

This is the primary fairness invariant for the future design.

### 4.3 Output conservation

For each order:

`originalOutput = remainingOutput + deliveredOutput + cancelledOutput`

### 4.4 Non-negativity

For every reachable state:

- `remainingInput >= 0`
- `remainingOutput >= 0`
- `accruedFees >= 0`
- `accruedSurplus >= 0`

### 4.5 No double claim

A filler may never receive more total input claim than the order made available for all fills.

### 4.6 User rebate recoverability

If oracle surplus capture gives a share to the user, that value must remain recoverable:

- either in `remainingInput`
- or already returned in a refund

### 4.7 Filler payout boundedness

A filler should never receive more value than:

- fair-value claim
- plus the configured filler surplus share

### 4.8 User loss boundedness

User loss must be explicitly measurable in common-value terms.

If the protocol chooses to allow bad quotes to execute, then any excess loss beyond fair value must be routed according to policy, not leaked implicitly.

### 4.9 Protocol capture boundedness

Protocol fees and protocol surplus must remain distinct accounting buckets.

Protocol surplus may only come from configured surplus capture logic, not from arbitrary principal.

### 4.10 Expiry safety

Before expiry:

- only the swapper may cancel

After expiry:

- anyone may cancel
- funds still go back to the swapper

### 4.11 Pause safety

When paused:

- no new swaps
- no fills
- cancellations remain available

### 4.12 Governance non-corruption

Governance changes must not silently violate the active policy in force at execution time.

In v1, the intended model is that fairness is evaluated using the **current** oracle and governance policy at the time of fill. This means governance may change surplus split and oracle parameters over time, but execution must still satisfy the active fairness rule and conservation invariants.

### 4.13 Batch equivalence

For a set of fills executed in one batch, the final economic state should be consistent with valid sequential execution of the same fills.

This does not require byte-for-byte equality if rounding differs slightly, but must preserve conservation and bounded payout properties.

### 4.14 Numeraire consistency

If token/USD oracle prices are available for both sides of a trade, then:

- input value and output value must be comparable in the same unit
- fairness checks must be based on those common-value measurements
- the protocol must not rely on pool-local price alone when a stronger common-value reference exists

### 4.15 Reward uniqueness

Each address may receive at most one reward per configured role:

- one swapper reward
- one filler reward
- one keeper reward

No combination of fills, cancels, or expiries should allow the same role reward to be minted twice.

### 4.16 Governance legitimacy

Any governance-controlled state transition must only be reachable if:

- enough voting power existed at the proposal snapshot
- the proposal passed according to the configured counting rules
- the timelock delay elapsed before execution

### 4.17 Governance execution safety

Governance proposals must only change the intended policy/config values.

They must not:

- silently bypass ownership checks
- skip timelock delay
- mutate unrelated order state
- cause value conservation invariants to fail

### Baseline invariant list

1. Input conservation
2. Value conservation
3. Output conservation
4. Non-negativity
5. No double claim
6. User rebate recoverability
7. Filler payout boundedness
8. User loss boundedness
9. Protocol capture boundedness
10. Expiry safety
11. Pause safety
12. Governance legitimacy
13. Governance execution safety

---

## 5. Oracle Assumptions

Oracle trustworthiness is treated as an external assumption, not a protocol invariant.

The model assumes:

- configured oracle values are meaningful in the intended common numeraire
- oracle timestamps are meaningful and monotonically interpretable
- a configured oracle is not maliciously returning adversarial values outside the scope of the trust model

The protocol must still guarantee correct behavior *given* oracle inputs, including:

- deterministic handling of missing oracle data
- deterministic handling of stale oracle data
- consistent use of the currently active governance-configured oracle policy
- no mixing of incompatible numeraires when computing value fairness

This section exists so the reader can clearly separate:

- what the protocol proves
- what the protocol must trust

---

## 6. Liveness Assumptions

These are not guaranteed by the contract alone, but assumed about the environment:

- if a valid filler exists, an order may eventually fill
- if an order expires, a keeper may eventually cancel it
- governance proposals that pass can eventually execute after the timelock

These assumptions are not guarantees of the contract, but they are important to make the system economically meaningful.

---

## 7. Oracle Policy Assumptions

Current preferred policy direction:

- do **not** revert fills on bad quotes
- instead, measure surplus relative to trusted token/USD fair values
- route that surplus between user / filler / protocol according to governance config
- if oracle data is missing or stale, skip capture rather than blocking execution

This makes user protection explicit while preserving execution liveness.

This section is about intended policy, not hardcoded implementation detail.

---

## 8. Open Questions

These are the design choices that are still intentionally unresolved.

1. Should unfilled fee in on-fill mode always be fully forgiven on cancel? (Current intent: yes.)
2. How strict should batch equivalence be under rounding?
3. When only one side of a pair has a USD oracle, what fallback policy should apply?
4. Should the protocol support multiple value numeraires beyond USD / USD-like pricing?
5. Should governance changes to surplus split be rate-limited or timelock-only for already-open order systems?

---

## 9. Next Formalization Step

Translate this document into a small executable transition system with:

- state tuple
- next-state actions
- invariants checked after each transition

Only once the plain-English model is stable should it be translated into a TLA+ spec.

That is why this document aims to be complete and reviewable in natural language first.
