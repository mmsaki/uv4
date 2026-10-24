> Historical head-only matching results. The default model now uses exact eligibility.
> The scenarios CLI explicitly selects `legacy_matching=True` to reproduce this baseline.
> See [README.md](README.md#exact-eligibility-repair) for the repaired policy and differential tests.

# Coarse prices: small price gaps can cause indefinite stalls

The worst demonstrated consequence is a matching stall, not execution below a maker's limit.
Both matching loops stop after the first non-crossing pair. Inside one price key, bid priority can
put a worse exact price ahead of an executable order. Calling `matchBook` again selects the same
pair and makes no progress while that head remains unchanged.

## Ordinary-price reproduction

Assumptions: 18-decimal asset, 6-decimal USDC, pool spot price 1,000 USDC/asset, minimum order
1 USDC, no active LP liquidity. All bids and inputs are paid. The blocker is placed before the
honest sells and buys, so this state is reachable through normal Router creation.

| Order | Input | Minimum output | Priority bid |
| --- | --- | --- | --- |
| Blocker sell | 0.001999999999999999 asset, worth 1.999999999999999 USDC at spot | 2 USDC | 0.100001 USDC |
| Each honest sell (20 orders) | 1 asset | 1,000 USDC | 0.10 USDC |
| Each honest buy (20 orders) | 1,000 USDC | 1 asset | 0.10 USDC |

All orders have key `1000000000`. The blocker asks about
`1000.00000000000050000000000000025` USDC/asset, just above the buyers' limit. Its higher bid wins
its ask bucket. Each honest seller could match a buyer exactly, but neither loop scans past the blocker.

Results, reproduced in Python and in the real Solidity Router/Hook/PoolManager:

- **100 retries: zero trades; 20,000 USDC of executable quote-side backlog remains.**
- Cancelling the blocker returns its asset input and forfeits its **0.100001 USDC** bid.
- Three `matchBook(..., 8)` calls then execute **8 + 8 + 4** pairs and pay sellers 20,000 USDC.
- A newly submitted crossing sell with a larger bid can take the front of the bucket and trade.

The blocker commits roughly **2.100001 USDC of spot-valued input plus bid**, excluding gas.
Its input is returned on cancellation in this scenario; the bid is not. Its capital requirement
is not proportional to the blocked backlog. This is a constructed example, not a global minimum
attack cost: required bids, minimum order settings, prices, liquidity and competing orders matter.

There is no timeout or retry-based progress guarantee. Delay can persist indefinitely **if the
blocking head remains**, although cancellation, repricing, replacement with higher-priority orders,
an eligible individual filler, or a successful LP route can change the state. It is not permanent
loss of custody and it does not freeze every possible price level or entry point.

## Price width and token decimals

For an ordinary unclamped bucket, the human USDC-per-asset width is

```
Δ = 10^(assetDecimals - usdcDecimals - 18)
```

For an 18-decimal asset and 6-decimal USDC, Δ = **0.000001 USDC per asset**. Two exact prices within
an ordinary bucket differ by less than Δ. This says nothing about maximum delay or total backlog.
For a 24-decimal asset the width is 1 USDC; raw price keys are not decimal-normalized prices.

If a match actually executes, both exact limit inequalities still hold. Priority ordering may
select a less favorable executable price within a bucket; on ordinary buckets the unit-price
variation is less than Δ, and its total value scales with quantity. The demonstrated stall itself
executes no trade and creates no direct trading loss.

## Clamped buckets

| Bucket | Exact raw ratios mapped to it | Implication |
| --- | --- | --- |
| Key `1` | Positive ratios below `2 / 1e18` | The zero and one bins merge. Human prices span `(0, 2Δ)`, and relative differences can be enormous. |
| Key `uint128.max` | Ratios at least `uint128.max / 1e18`, subject to admission/overflow bounds | Saturation creates a broad upper bucket; the ordinary one-step bound does not apply. |

Python lower-clamp scenario: honest limits are **0.000000000001 USDC/asset**; the blocker asks
**0.0000019 USDC/asset**, a **1,900,000×** ratio. All have key `1`. Approximately 2 USDC of blocker
input plus a 0.100001 USDC bid stalls 20 million USDC of synthetic backlog through 100 retries.
This uses very large token quantities that still fit the input bound; it is a boundary scenario,
not a claim about liquidity or token supply in a deployed market.

The upper-clamp example uses astronomically high synthetic prices solely to exercise saturation.
It also stalls. Neither case bypasses the exact crossing test or proves infinite numeric ranges:
Solidity input/output widths, price-computation overflow, configured minima and available balances
still bound admissible orders.

## Fix directions

1. Order distinct limits by exact rational price, with bid/sequence priority only at an equal exact
   price. This addresses the cause but changes ordering semantics and implementation complexity.
2. Scan past non-crossing heads with a separate comparison budget and resumable progress. A fixed
   scan from the same head on every call can still be blocked by more bad heads than the budget.
3. More precision reduces ordinary collisions but does not eliminate them or solve clamping.

No matching-policy fix is applied by this simulation. The Solidity tests deliberately pass while
reproducing the unresolved behavior.
