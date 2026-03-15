# AsyncSwap State Machine

This document captures the core state transitions and invariants for AsyncSwap V1 in a protocol-neutral form.

## State Variables

- `original_input`
- `original_output`
- `remaining_input`
- `remaining_output`
- `filler_payout_total`
- `protocol_fee_total`
- `protocol_surplus_total`
- `refunded_input_total`
- `delivered_output_total`
- `cancelled_output_total`
- `user_rebate_total`
- `user_rebate_returned`
- `deadline`
- `current_time`
- `cancelled`

## Transitions

### Open Order

Initialize:

- `remaining_input = original_input - initial_protocol_fee` (upfront mode)
- `remaining_input = original_input` (on-fill mode)
- `remaining_output = original_output`
- `deadline` must be `0` (no expiry) or strictly in the future

### Fill

Each fill supplies:

- `output_amount`
- `gross_input_slice`
- `filler_payout`
- `protocol_fee`
- `protocol_surplus`
- `user_rebate`

Preconditions:

- order is not cancelled
- order is not expired (`deadline == 0` or `current_time <= deadline`)
- `output_amount >= ceil(remaining_output / 2)` (minimum fill threshold)
- `output_amount <= remaining_output`

Constraint:

`gross_input_slice = filler_payout + protocol_fee + protocol_surplus + user_rebate`

The charged amount removed from `remaining_input` is:

`charged_input = filler_payout + protocol_fee + protocol_surplus`

On partial fill:

- the user rebate stays recoverable inside `remaining_input`

On full fill:

- the user rebate is returned directly to the user (`user_rebate_returned += user_rebate`)
- this prevents value from being stranded in a completed order

### Cancel

Preconditions:

- before expiry: only the swapper can cancel
- after expiry: anyone can cancel (keeper)

Effects:

`refund = remaining_input`

Then:

- `remaining_input = 0`
- `remaining_output = 0`
- `cancelled_output_total += remaining_output`
- `refunded_input_total += refund`
- `cancelled = true`

Funds always go to the swapper, regardless of who cancels.

## Invariants

### Value conservation

`original_input = remaining_input + refunded_input_total + filler_payout_total + protocol_fee_total + protocol_surplus_total`

### Output conservation

`original_output = remaining_output + delivered_output_total + cancelled_output_total`

### User protection

`user_rebate_total <= remaining_input + refunded_input_total + user_rebate_returned`

The user's share of captured surplus must remain recoverable either:

- in the live order's `remaining_input`, or
- in refunded input after cancellation, or
- already returned directly on full fill.

### Monotonicity

Every valid fill must strictly decrease:

- `remaining_output`
- `remaining_input` by the charged amount

No fill may create value or overdraw balances.

### Expiry safety

- before expiry: only swapper can cancel
- after expiry: anyone can cancel, but funds still go to swapper
- expired orders cannot be filled

### Minimum fill threshold

Each fill must cover at least 50% of `remaining_output`, ensuring convergence in O(log n) fills.
