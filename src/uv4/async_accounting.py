from dataclasses import dataclass


MAX_FEE = 1_000_000  # fee in ppm, same convention as Uniswap V4


@dataclass(frozen=True)
class AsyncOrderAccounting:
    gross_input: int
    fee_amount: int
    net_input: int
    total_output: int
    remaining_input: int
    remaining_output: int
    accrued_fee: int
    filled_input: int
    delivered_output: int


def fee_amount_from_input(amount_in: int, fee_ppm: int) -> int:
    """Compute protocol fee rounded up, matching Solidity mulDivRoundingUp."""
    if amount_in < 0:
        raise ValueError("amount_in must be non-negative")
    if not 0 <= fee_ppm < MAX_FEE:
        raise ValueError(f"fee_ppm must be in [0, {MAX_FEE})")
    if amount_in == 0 or fee_ppm == 0:
        return 0
    return (amount_in * fee_ppm + MAX_FEE - 1) // MAX_FEE


def open_order(amount_in: int, amount_out: int, fee_ppm: int) -> AsyncOrderAccounting:
    """Open an async order.

    gross_input: what the user deposits
    fee_amount: protocol fee taken from gross input
    net_input: filler-claimable portion after fee
    total_output: user output target actually owed by fillers
    """
    if amount_in <= 0:
        raise ValueError("amount_in must be positive")
    if amount_out < 0:
        raise ValueError("amount_out must be non-negative")

    fee_amount = fee_amount_from_input(amount_in, fee_ppm)
    if fee_amount >= amount_in:
        raise ValueError("fee consumes all input")

    net_input = amount_in - fee_amount
    return AsyncOrderAccounting(
        gross_input=amount_in,
        fee_amount=fee_amount,
        net_input=net_input,
        total_output=amount_out,
        remaining_input=net_input,
        remaining_output=amount_out,
        accrued_fee=fee_amount,
        filled_input=0,
        delivered_output=0,
    )


def partial_fill(
    state: AsyncOrderAccounting, fill_output: int
) -> tuple[int, AsyncOrderAccounting]:
    """Apply a partial fill and return (input_share_to_filler, new_state).

    The filler earns a proportional share of the remaining net input:
        floor(fill_output * remaining_input / remaining_output)
    """
    if fill_output <= 0:
        raise ValueError("fill_output must be positive")
    if state.remaining_output == 0:
        raise ValueError("order already fully filled")
    if fill_output > state.remaining_output:
        raise ValueError("fill_output exceeds remaining_output")

    input_share = (fill_output * state.remaining_input) // state.remaining_output

    new_state = AsyncOrderAccounting(
        gross_input=state.gross_input,
        fee_amount=state.fee_amount,
        net_input=state.net_input,
        total_output=state.total_output,
        remaining_input=state.remaining_input - input_share,
        remaining_output=state.remaining_output - fill_output,
        accrued_fee=state.accrued_fee,
        filled_input=state.filled_input + input_share,
        delivered_output=state.delivered_output + fill_output,
    )
    return input_share, new_state


def cancel_order(state: AsyncOrderAccounting) -> tuple[int, int]:
    """Cancel an order and return (refund_to_user, protocol_fee_kept)."""
    return state.remaining_input, state.accrued_fee


def assert_invariants(state: AsyncOrderAccounting) -> None:
    """Check accounting identities for testing/model validation."""
    assert state.gross_input == state.net_input + state.accrued_fee
    assert state.net_input == state.remaining_input + state.filled_input
    assert state.total_output == state.remaining_output + state.delivered_output
    assert state.remaining_input >= 0
    assert state.remaining_output >= 0
    assert state.accrued_fee == state.fee_amount
