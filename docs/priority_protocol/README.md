# Priority-only Async Swap Python model

This model rebuilds the current Async Swap economic lifecycle inside the existing `uv4` checkout.
It is separate from the earlier `uv4.asyncswap` and oracle/surplus models. Source: the local contracts
workspace after the priority-fee-only audit changes, identified by [source_manifest.json](source_manifest.json).

## Run

From the uv4 repository:

```sh
uv sync --extra priority-model
uv run --extra priority-model pytest tests/priority_protocol -q
uv run --extra priority-model python -m uv4.priority_protocol.scenarios \
  --orders 20 --retries 100 --output docs/priority_protocol/coarse_prices.json
uv run --extra priority-model python examples/export_priority_vectors.py /path/to/contracts
uv run --extra priority-model python examples/check_priority_source.py /path/to/contracts
```

In the contracts repository:

```sh
forge test --match-contract 'CoarsePriceBlockingTest|PriorityPython.*Test' -vv
```

## Components and coverage

| Component | Modeled behavior |
| --- | --- |
| Router creation | Maker identity through the caller API, exact native payment, ERC-20 allowances, input and immediate bid escrow, matching only after payment, automatic LP attempt |
| PoolManager accounting | Unlock debts/credits, ERC-6909 claims, token backing, pool inventory, zero deltas at transaction end |
| Priority book | Price levels on v4 ticks (floor tick of the exact limit, ported bit for bit from `TickMath`), exact price first within each level, then fee/sequence for exact ties, eight-pair per-call cap |
| Matching | Resting-order pricing, integer rounding, both limit checks, proportional bid settlement, proportional remaining minimum, dust refunds, reprioritization |
| Direct fill | Live output price, maximum gross payment, minimum input window, clear-before-payout, protocol fee |
| Cancel/reprice | Owner/executor checks, complete input refund, non-refundable bid, minimum check, fresh sequence on reprice; a sell reprice that raises the minimum bid must already hold it |
| LP fill | Original input/minimum, temporary 3,000 fee and restoration, full-consumption requirement, rollback of failed self-call |
| FeeVault | Fee claims separate from maker escrow, current-owner collection |
| NativeClaims | Claim allowance, burn-before-transfer, rollback on rejected redemption |
| Admin | Two-step ownership, default/per-pool minimum, sweep of raw hook balances only |
| Signed actions | EIP-712 grant/reprice/cancel, one hook nonce store shared by grant/reprice/cancel (the Router burns cancel nonces through `useNonce`), deadlines, EOA recovery, Permit2 witness creation and nonce replay checks; ERC-1271 verifier interface |
| Order identity | Solidity ABI/Keccak pool IDs, salt derivation, collision walk, chain/pool/maker/direction/salt binding |

Every outer model call checks zero unlock deltas, nonnegative assets/claims/reserves, total token
conservation, PoolManager backing, and equality between the hook's claims and live order obligations.
Failures restore the complete world snapshot. A failed LP attempt restores only that nested call.

## Exact parts and boundaries

Order arithmetic uses integers with checked widths, 512-bit intermediate products, Solidity floor/ceil
rules, and the current price clamps. Sorting replaces the radix implementation: allocator/gas behavior
is not simulated. Identity hashing uses ABI encoding and Ethereum Keccak, not SHA3-256. Signature
recovery is real EOA recovery using `eth-keys`; the configurable addresses are simulation identities,
not deployed contracts. The `address()` helper derives fixture addresses from symbolic labels.

This is an executable protocol model, **not an EVM or a complete Uniswap v4 implementation**:

- `Uv4SingleRange` uses the local `uv4.swap.Swap` Decimal calculator. It rejects attempts to cross the
  configured liquidity interval. Its rounding is not claimed bit-identical to v4. Exact v4 tick
  crossing, LP position ownership, fee growth, and liquidity-position mint/burn are external boundaries.
  `configure_liquidity` is fixture setup with real backing in the model, not a position-manager port.
- A quote adapter can supply a different pool engine; the hook still checks input consumption,
  minimum output and atomic rollback. The coarse-price reproductions use **no LP liquidity**, so
  their results do not depend on approximate AMM quotes.
- Calls are Python methods, not ABI calldata dispatch or bytecode. Router userData mismatch guards
  are represented by a typed creation API rather than malformed ABI inputs. Raw callback caller
  checks and EVM transient storage are not separately emulated.
- ERC-1271 is an explicit verifier callback. ERC-20 transfer rejection and allowances are modeled;
  arbitrary token reentrancy, fee-on-transfer/rebasing behavior and gas are not. Native redemption
  is atomic, but arbitrary recipient execution and reentrancy are outside this model.
- The Python tests and differential vectors are evidence for covered behavior, not a proof of
  full equivalence or production readiness.

The existing local checkout includes an untracked `src/uv4/swap.py`, used by its existing package
exports and the optional LP adapter. This work preserves that file and the other existing changes;
it does not publish a new uv4 release or change repository remotes.

## Validation

- 48 focused model/tool tests pass, including deterministic lifecycle campaigns, randomized
  order pairs, claim-credit aggregation, self-credits, and receipt-comparison guards.
- 100 Python-generated arithmetic/matching vectors and signature hashes pass against Solidity and Huff.
- Eight shared stateful campaigns: 514 operations, 128 matches, 8,109 order-state checks, and
  8,109 wallet checks, plus escrow and settled-fee claims.
- The full local Solidity suite passes 867 tests, including the pinned Unichain fork tests.
  Current Huff tests pass separately; historical Huff storage-layout fixtures are excluded.
- Regenerated Lean models and focused refinements build. Shared-memory mutation in
  `ClaimTransfers.credit` remains opaque to FormalMind 0.1.1; batch-memory refinement is not proven.

Matching credits and priority fees use direct ERC-6909 claim transfers. A bounded match call
combines credits by recipient and currency and flushes them in first-credit order before returning.
The queue holds at most 33 distinct credits for eight matches. Self-credits transfer immediately;
redemption and underlying token payouts remain separate. The ledger models claim transfers without
changing unlock deltas. Hook matching/fee notices remain logical model events; exact PoolManager
receipt events are compared directly between the two contracts by the receipt tools.

See [coarse_prices.md](coarse_prices.md) and the machine-readable
[coarse_prices.json](coarse_prices.json).

## Signature references

Local `contracts/src/libraries/OrderSignatures.sol` defines the Async Swap types. Permit2 encoding
follows the upstream [PermitHash](https://github.com/Uniswap/permit2/blob/main/src/libraries/PermitHash.sol)
and [EIP712](https://github.com/Uniswap/permit2/blob/main/src/EIP712.sol) implementations.

## Exact eligibility repair

The default model now filters exact `Fraction` prices before applying priority rank. This is
intentionally independent of the Solidity augmented trie. The `scenarios` CLI still explicitly
selects the legacy policy to preserve the historical counterexamples in `coarse_prices.json`.

Regenerate and run the stateful differential campaign:

```sh
uv run --extra priority-model python examples/export_eligible_vectors.py /path/to/contracts
# From contracts:
forge test --match-contract 'EligiblePython[0-9]Test|EligiblePriceTest|CoarsePriceBlockingTest'
forge test --match-contract EligibleGasTest -vv > /tmp/eligible-gas.log
# From uv4 (paper path must contain figures/, sections/, evidence/):
uv run --with matplotlib python examples/report_eligible_gas.py /tmp/eligible-gas.log /path/to/whitepaper
```

[eligible_vectors.json](eligible_vectors.json) records the deterministic trace counts.
[eligible_gas.json](eligible_gas.json) records actual Solidity gas measurements and their boundaries.
The chosen pair policy selects the highest exact bid and lowest exact ask within the best
boundary bucket. No global volume optimum, individual-order starvation freedom, or numeric
worst-case gas guarantee is asserted. The paper gives the structural search bound and constrained
throughput objective. Eight remains the per-call cap; measurements up to 32 compose calls.

### Transaction gas and storage reuse

The optimized index stops ancestor repair when its summary is unchanged, retains unreachable
node/summary storage until reuse, and avoids a second buy-tree search when the head buy already
crosses the minimum ask. Recycled node records are fully overwritten. Summary refresh always
propagates beyond its first branch, preventing stale recycled bytes from hiding a changed subtree.
The independent Python selection/state model is unchanged; Solidity lifecycle traces test it
against the optimized implementation.

`matching_receipts.json` compares real Router transactions before and after optimization, including
intrinsic gas and applied refunds. The gross unlock data above is a different measurement.
Use an isolated local Anvil; the script resets it. From contracts, export the fixture:

```sh
EXPORT_GAS_FIXTURE=true FOUNDRY_OPTIMIZER_RUNS=43690 forge test --match-contract EligibleGasTest -vv > /tmp/gas-fixture.log
```

From this checkout, after starting `anvil --port 18547`:

```sh
python examples/measure_matching_receipts.py /path/to/contracts/deployments/eligible-gas-state.json /tmp/gas-fixture.log http://127.0.0.1:18547 /tmp/receipts.json
uv run --with matplotlib python examples/report_matching_receipts.py /tmp/before.json /tmp/receipts.json /path/to/whitepaper
```

Use the same compiler settings and fixture on both sides. The before/after report asserts that all
emitted events are identical. Measurements use 128 blockers, standard ERC20 fixtures, repeated
owners, and no LP positions; they are not gas bounds for arbitrary tokens or order distributions.

The current selection policy sorts exact rational prices before priority, including shared and
clamped levels. Signed repricing and cancellation bind the immutable creation sequence as well as the
shared nonce. Sell repricing that raises minimum output must satisfy the new bid floor, including
when both old and new floors hit the cap. Stateful vectors check rejected reprices and rollback.


Receipt measurements support both Solidity and native Huff projects. Exporters load the pool
configuration before dumping state, and the receipt tool verifies the imported pool FeeVault.
`examples/compare_matching_receipts.py SOLIDITY_JSON HUFF_BEFORE_JSON HUFF_AFTER_JSON OUTPUT_JSON`
checks every emitted event for equality and reports receipt gas savings for 1, 2, 4, and 8 matches.
Use the same dedicated local Anvil and compiler settings for all three reports.
