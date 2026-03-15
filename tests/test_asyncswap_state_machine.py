import pytest

from uv4.asyncswap_state_machine import AsyncSwapStateMachine


ONE = 10**18


def test_upfront_mode_half_fill_then_cancel_conserves_value():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=988_000_000_000_000_000,
        initial_protocol_fee=12_000_000_000_000_000,
    )

    machine.fill(
        output_amount=494_000_000_000_000_000,
        gross_input_slice=494_000_000_000_000_000,
        filler_payout=494_000_000_000_000_000,
    )
    refund = machine.cancel()

    assert refund == 494_000_000_000_000_000
    machine.assert_state()


def test_on_fill_mode_half_fill_then_cancel_conserves_value():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=988_000_000_000_000_000,
    )

    machine.fill(
        output_amount=494_000_000_000_000_000,
        gross_input_slice=500_000_000_000_000_000,
        filler_payout=494_000_000_000_000_000,
        protocol_fee=6_000_000_000_000_000,
    )
    refund = machine.cancel()

    assert refund == 500_000_000_000_000_000
    machine.assert_state()


def test_surplus_full_fill_returns_user_rebate_immediately():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=100_000_000,
    )

    machine.fill(
        output_amount=100_000_000,
        gross_input_slice=ONE,
        filler_payout=931_818_181_818_181_817,
        protocol_surplus=22_727_272_727_272_728,
        user_rebate=45_454_545_454_545_455,
    )

    assert machine.remaining_output == 0
    # Rebate returned immediately
    assert machine.user_rebate_returned == 45_454_545_454_545_455
    machine.assert_state()


def test_surplus_partial_fill_returns_user_rebate_immediately():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=200_000_000,
    )

    machine.fill(
        output_amount=100_000_000,
        gross_input_slice=500_000_000_000_000_000,
        filler_payout=465_909_090_909_090_909,
        protocol_surplus=11_363_636_363_636_364,
        user_rebate=22_727_272_727_272_727,
    )

    assert machine.remaining_output == 100_000_000
    # Rebate returned immediately even on partial fill
    assert machine.user_rebate_returned == 22_727_272_727_272_727
    machine.assert_state()


def test_filler_disadvantaged_detection_in_value_model():
    """Filler-side protection is handled in the USD-value model, not the state machine.
    This test just verifies the state machine allows the fill to proceed and conserves value."""
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=100_000_000,
    )

    machine.fill(
        output_amount=100_000_000,
        gross_input_slice=ONE,
        filler_payout=ONE,
    )

    assert machine.remaining_output == 0
    assert machine.filler_payout_total == ONE
    machine.assert_state()


def test_cancel_returns_remaining_after_partial_surplus_fill():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=200_000_000,
    )

    machine.fill(
        output_amount=100_000_000,
        gross_input_slice=500_000_000_000_000_000,
        filler_payout=465_909_090_909_090_909,
        protocol_surplus=11_363_636_363_636_364,
        user_rebate=22_727_272_727_272_727,
    )
    refund = machine.cancel()

    assert refund > 0
    machine.assert_state()


def test_batch_equivalence_for_two_independent_orders():
    a = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=988_000_000_000_000_000,
        initial_protocol_fee=12_000_000_000_000_000,
    )
    b = AsyncSwapStateMachine.open_order(
        original_input=2 * ONE,
        original_output=1_976_000_000_000_000_000,
        initial_protocol_fee=24_000_000_000_000_000,
    )

    a.fill(
        output_amount=988_000_000_000_000_000,
        gross_input_slice=988_000_000_000_000_000,
        filler_payout=988_000_000_000_000_000,
    )
    b.fill(
        output_amount=1_976_000_000_000_000_000,
        gross_input_slice=1_976_000_000_000_000_000,
        filler_payout=1_976_000_000_000_000_000,
    )

    a.assert_state()
    b.assert_state()
    assert a.filler_payout_total + b.filler_payout_total == 2_964_000_000_000_000_000


def test_invalid_fill_that_exceeds_remaining_input_reverts():
    machine = AsyncSwapStateMachine.open_order(original_input=ONE, original_output=100)

    with pytest.raises(ValueError, match="total_charged exceeds remaining_input"):
        machine.fill(
            output_amount=100,
            gross_input_slice=ONE + 1,
            filler_payout=ONE,
            user_rebate=1,
        )


def test_expired_order_cannot_be_filled():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=988_000_000_000_000_000,
        deadline=1000,
        current_time=500,
    )

    machine.warp(1001)

    with pytest.raises(ValueError, match="order expired"):
        machine.fill(
            output_amount=988_000_000_000_000_000,
            gross_input_slice=988_000_000_000_000_000,
            filler_payout=988_000_000_000_000_000,
        )


def test_keeper_can_cancel_expired_order():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=988_000_000_000_000_000,
        deadline=1000,
        current_time=500,
    )

    machine.warp(1001)
    refund = machine.cancel(caller="keeper", swapper="alice")

    assert refund == ONE
    machine.assert_state()


def test_non_swapper_cannot_cancel_before_expiry():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=988_000_000_000_000_000,
        deadline=1000,
        current_time=500,
    )

    with pytest.raises(ValueError, match="only swapper"):
        machine.cancel(caller="keeper", swapper="alice")


def test_already_expired_deadline_rejected_at_creation():
    with pytest.raises(ValueError, match="deadline must be in the future"):
        AsyncSwapStateMachine.open_order(
            original_input=ONE,
            original_output=988_000_000_000_000_000,
            deadline=500,
            current_time=500,
        )


def test_below_minimum_fill_threshold_reverts():
    machine = AsyncSwapStateMachine.open_order(
        original_input=ONE,
        original_output=1000,
    )

    with pytest.raises(ValueError, match="minimum fill threshold"):
        machine.fill(
            output_amount=400,
            gross_input_slice=400_000_000_000_000_000,
            filler_payout=400_000_000_000_000_000,
        )
