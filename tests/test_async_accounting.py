import pytest

from uv4.async_accounting import (
    assert_invariants,
    cancel_order,
    fee_amount_from_input,
    open_order,
    partial_fill,
)


ONE = 10**18
FEE_PPM = 12_000  # 1.2%


def test_fee_amount_rounds_up():
    assert fee_amount_from_input(0, FEE_PPM) == 0
    assert fee_amount_from_input(1, FEE_PPM) == 1
    assert fee_amount_from_input(ONE, FEE_PPM) == 12_000_000_000_000_000


def test_open_order_isolates_fee_from_fillable_input():
    state = open_order(amount_in=ONE, amount_out=1_976 * ONE, fee_ppm=FEE_PPM)

    assert state.gross_input == ONE
    assert state.fee_amount == 12_000_000_000_000_000
    assert state.net_input == 988_000_000_000_000_000
    assert state.remaining_input == state.net_input
    assert state.accrued_fee == state.fee_amount
    assert_invariants(state)


def test_partial_fill_pays_from_net_input_only():
    state = open_order(amount_in=ONE, amount_out=1_976 * ONE, fee_ppm=FEE_PPM)

    input_share, new_state = partial_fill(state, 988 * ONE)

    assert input_share == state.net_input // 2
    assert new_state.remaining_input == state.net_input - input_share
    assert new_state.accrued_fee == state.fee_amount
    assert (
        new_state.accrued_fee + new_state.remaining_input + new_state.filled_input
        == state.gross_input
    )
    assert_invariants(new_state)


def test_two_partial_fills_converge_and_keep_fee_isolated():
    state = open_order(amount_in=ONE, amount_out=1_976 * ONE, fee_ppm=FEE_PPM)

    share1, state = partial_fill(state, 988 * ONE)
    share2, state = partial_fill(state, 988 * ONE)

    assert state.remaining_output == 0
    assert state.remaining_input == 0
    assert share1 + share2 == 988_000_000_000_000_000
    assert state.accrued_fee == 12_000_000_000_000_000
    assert_invariants(state)


def test_cancel_returns_only_remaining_net_input_and_keeps_fee():
    state = open_order(amount_in=ONE, amount_out=1_976 * ONE, fee_ppm=FEE_PPM)
    _, state = partial_fill(state, 988 * ONE)

    refund, protocol_fee = cancel_order(state)

    assert refund == state.remaining_input
    assert protocol_fee == state.accrued_fee
    assert refund + state.filled_input + protocol_fee == state.gross_input


def test_partial_fill_rejects_invalid_amounts():
    state = open_order(amount_in=ONE, amount_out=1_000, fee_ppm=FEE_PPM)

    with pytest.raises(ValueError, match="fill_output must be positive"):
        partial_fill(state, 0)

    with pytest.raises(ValueError, match="fill_output exceeds remaining_output"):
        partial_fill(state, 1_001)


def test_open_order_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="amount_in must be positive"):
        open_order(0, 1, FEE_PPM)

    with pytest.raises(ValueError, match="amount_out must be non-negative"):
        open_order(ONE, -1, FEE_PPM)

    with pytest.raises(ValueError, match="fee consumes all input"):
        open_order(1, 1, 999_999)


def test_invariants_hold_across_multiple_partial_fills():
    state = open_order(amount_in=5 * ONE, amount_out=10_000 * ONE, fee_ppm=FEE_PPM)

    for fill in [2_500 * ONE, 3_000 * ONE, 2_000 * ONE, 2_500 * ONE]:
        _, state = partial_fill(state, fill)
        assert_invariants(state)

    assert state.remaining_output == 0
    assert state.remaining_input == 0
    assert state.accrued_fee == fee_amount_from_input(5 * ONE, FEE_PPM)
