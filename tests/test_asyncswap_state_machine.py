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


def test_surplus_split_50_25_25_keeps_user_value_recoverable():
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
    assert machine.remaining_input == 45_454_545_454_545_455
    machine.assert_state()


def test_cancel_returns_user_rebate_after_surplus_capture():
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
    refund = machine.cancel()

    assert refund == 45_454_545_454_545_455
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


def test_invalid_fill_that_breaks_conservation_reverts():
    machine = AsyncSwapStateMachine.open_order(original_input=ONE, original_output=100)

    try:
        machine.fill(
            output_amount=100,
            gross_input_slice=ONE,
            filler_payout=900_000_000_000_000_000,
            protocol_surplus=50_000_000_000_000_000,
            user_rebate=10,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass
