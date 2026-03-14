import pytest

from uv4.asyncswap import AsyncSwap, AsyncSwapError, FeeMode, Order, PoolKey, SwapParams


ONE = 10**18


@pytest.fixture
def token_pool_key():
    return PoolKey(pool_id="pool-1", currency0="token0", currency1="token1", fee=12_000)


@pytest.fixture
def native_pool_key():
    return PoolKey(
        pool_id="pool-native", currency0="native", currency1="token1", fee=12_000
    )


def test_swap_initializes_order_like_contract(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)

    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    assert order == Order(pool_id="pool-1", swapper="alice", tick=0)
    assert model.get_balance_in(order, True) == 988_000_000_000_000_000
    assert model.get_balance_out(order, True) == 988_000_000_000_000_000
    assert model.pool_manager.balance_of("hook", "token0") == ONE
    assert model.protocol_fees["token0"] == 12_000_000_000_000_000


def test_same_user_same_tick_same_pool_accumulates(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)

    order1 = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )
    order2 = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=2 * ONE,
        tick=0,
        min_amount_out=0,
    )

    assert order1 == order2
    assert model.get_balance_in(order1, True) == 2_964_000_000_000_000_000
    assert model.get_balance_out(order1, True) == 2_964_000_000_000_000_000
    assert model.protocol_fees["token0"] == 36_000_000_000_000_000


def test_fill_pays_proportional_input_share_from_full_claim_pool(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    input_share = model.fill(order, True, 494_000_000_000_000_000, filler="bob")

    assert input_share == 494_000_000_000_000_000
    assert model.pool_manager.balance_of("bob", "token0") == 494_000_000_000_000_000
    assert model.pool_manager.balance_of("hook", "token0") == 506_000_000_000_000_000
    assert model.get_balance_in(order, True) == 494_000_000_000_000_000
    assert model.get_balance_out(order, True) == 494_000_000_000_000_000


def test_cancel_burns_remaining_claims_and_returns_input_currency(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )
    model.fill(order, True, 494_000_000_000_000_000, filler="bob")

    refund, currency = model.cancel_order(order, True, caller="alice")

    assert refund == 494_000_000_000_000_000
    assert currency == "token0"
    assert model.pool_manager.balance_of("hook", "token0") == 12_000_000_000_000_000
    assert model.get_balance_in(order, True) == 0
    assert model.get_balance_out(order, True) == 0


def test_native_input_requires_exact_value(native_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(native_pool_key)

    with pytest.raises(AsyncSwapError, match="INVALID_NATIVE_VALUE"):
        model.swap(
            native_pool_key,
            user="alice",
            zero_for_one=True,
            amount_in=ONE,
            tick=0,
            min_amount_out=0,
            value=ONE - 1,
        )

    order = model.swap(
        native_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
        value=ONE,
    )
    assert model.get_balance_in(order, True) == 988_000_000_000_000_000


def test_native_output_fill_requires_exact_value(native_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(native_pool_key)
    order = model.swap(
        native_pool_key,
        user="alice",
        zero_for_one=False,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )
    fill_amount = model.get_balance_out(order, False)

    with pytest.raises(AsyncSwapError, match="INVALID_NATIVE_OUTPUT_VALUE"):
        model.fill(order, False, fill_amount, filler="bob", value=fill_amount - 1)

    input_share = model.fill(order, False, fill_amount, filler="bob", value=fill_amount)
    assert input_share == 988_000_000_000_000_000
    assert model.native_balances["alice"] == fill_amount


def test_before_swap_untrusted_router_reverts(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)

    with pytest.raises(AsyncSwapError, match="UNTRUSTED ROUTER"):
        model.before_swap(
            sender="attacker",
            key=token_pool_key,
            params=SwapParams(zero_for_one=True, amount_specified=-ONE),
            hook_data=(Order("pool-1", "alice", 0), 0),
        )


def test_fill_unknown_pool_reverts(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)
    unknown_order = Order(pool_id="missing", swapper="alice", tick=0)

    with pytest.raises(AsyncSwapError, match="UNKNOWN_POOL"):
        model.fill(unknown_order, True, 1, filler="bob")


def test_cancel_wrong_owner_reverts(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    with pytest.raises(AsyncSwapError, match="NOT_ORDER_OWNER"):
        model.cancel_order(order, True, caller="mallory")


def test_transfer_ownership_sets_pending_owner():
    model = AsyncSwap(fee_ppm=12_000, owner="alice")

    model.transfer_ownership(caller="alice", new_owner="bob")

    assert model.protocol_owner == "alice"
    assert model.pending_owner == "bob"


def test_transfer_ownership_wrong_owner_reverts():
    model = AsyncSwap(fee_ppm=12_000, owner="alice")

    with pytest.raises(AsyncSwapError, match="NOT OWNER"):
        model.transfer_ownership(caller="mallory", new_owner="bob")


def test_accept_ownership_completes_two_step_transfer():
    model = AsyncSwap(fee_ppm=12_000, owner="alice")
    model.transfer_ownership(caller="alice", new_owner="bob")

    model.accept_ownership(caller="bob")

    assert model.protocol_owner == "bob"
    assert model.pending_owner is None


def test_accept_ownership_non_pending_owner_reverts():
    model = AsyncSwap(fee_ppm=12_000, owner="alice")
    model.transfer_ownership(caller="alice", new_owner="bob")

    with pytest.raises(AsyncSwapError, match="NOT_PENDING_OWNER"):
        model.accept_ownership(caller="mallory")


def test_fee_mode_upfront_cancel_keeps_fee(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.UPFRONT)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    refund, currency = model.cancel_order(order, True, caller="alice")

    assert refund == 988_000_000_000_000_000
    assert currency == "token0"
    assert model.protocol_fees["token0"] == 12_000_000_000_000_000


def test_fee_mode_on_fill_cancel_returns_full_unfilled_input(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.ON_FILL)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    refund, currency = model.cancel_order(order, True, caller="alice")

    assert refund == ONE
    assert currency == "token0"
    assert model.protocol_fees["token0"] == 0


def test_fee_mode_on_fill_partial_fill_accrues_fee_only_on_filled_share(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.ON_FILL)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    fill_amount = model.get_balance_out(order, True) // 2
    filler_share = model.fill(order, True, fill_amount, filler="bob")

    gross_share = 500_000_000_000_000_000
    fee_share = 6_000_000_000_000_000
    assert filler_share == gross_share - fee_share
    assert model.protocol_fees["token0"] == fee_share
    assert model.get_balance_in(order, True) == ONE - gross_share


def test_fee_mode_comparison_upfront_vs_on_fill_partial_fill(token_pool_key):
    upfront = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.UPFRONT)
    on_fill = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.ON_FILL)
    upfront.initialize_pool(token_pool_key)
    on_fill.initialize_pool(token_pool_key)

    upfront_order = upfront.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )
    on_fill_order = on_fill.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    fill_amount = upfront.get_balance_out(upfront_order, True) // 2
    upfront_filler_share = upfront.fill(upfront_order, True, fill_amount, filler="bob")
    on_fill_filler_share = on_fill.fill(on_fill_order, True, fill_amount, filler="bob")

    assert upfront_filler_share == 494_000_000_000_000_000
    assert on_fill_filler_share == 494_000_000_000_000_000
    assert upfront.protocol_fees["token0"] == 12_000_000_000_000_000
    assert on_fill.protocol_fees["token0"] == 6_000_000_000_000_000


def test_fee_mode_invariant_upfront_half_fill(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.UPFRONT)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    fill_amount = model.get_balance_out(order, True) // 2
    filler_share = model.fill(order, True, fill_amount, filler="bob")
    refundable_remainder = model.get_balance_in(order, True)
    upfront_fee = model.protocol_fees["token0"]

    # 1.0 = 0.012 + 0.494 + 0.494
    assert upfront_fee == 12_000_000_000_000_000
    assert filler_share == 494_000_000_000_000_000
    assert refundable_remainder == 494_000_000_000_000_000
    assert upfront_fee + filler_share + refundable_remainder == ONE


def test_fee_mode_invariant_on_fill_half_fill(token_pool_key):
    model = AsyncSwap(fee_ppm=12_000, fee_mode=FeeMode.ON_FILL)
    model.initialize_pool(token_pool_key)
    order = model.swap(
        token_pool_key,
        user="alice",
        zero_for_one=True,
        amount_in=ONE,
        tick=0,
        min_amount_out=0,
    )

    fill_amount = model.get_balance_out(order, True) // 2
    filler_share = model.fill(order, True, fill_amount, filler="bob")
    refundable_remainder = model.get_balance_in(order, True)
    filled_fee = model.protocol_fees["token0"]

    # 1.0 = 0.006 + 0.494 + 0.5
    assert filled_fee == 6_000_000_000_000_000
    assert filler_share == 494_000_000_000_000_000
    assert refundable_remainder == 500_000_000_000_000_000
    assert filled_fee + filler_share + refundable_remainder == ONE
