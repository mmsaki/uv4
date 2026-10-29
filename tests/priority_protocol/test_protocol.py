from copy import deepcopy
from fractions import Fraction
import random
import pytest
from eth_keys import keys
from uv4.priority_protocol import *
from uv4.priority_protocol.arithmetic import U256, U128, I128, mul_div, trade_fee, tick_at_sqrt_price
from uv4.priority_protocol.identity import address
from uv4.priority_protocol.scenarios import setup, fund, collision_case
from uv4.priority_protocol import signatures


@pytest.fixture
def world():
    m, pid = setup()
    for who in ("alice", "bob", "filler", "lp"):
        fund(m, pid, who)
    return m, pid


def unchanged(m, operation, error):
    before = deepcopy(m.__dict__)
    with pytest.raises(Revert, match=error):
        operation()
    assert m.__dict__ == before
    m.assert_invariants()


def test_immediate_escrow_and_cancel_forfeits_bid(world):
    m, p = world
    old = m.ledger.balances["alice", "ASSET"]
    oid = m.create(p, "alice", False, 10**18, 10**9)
    assert m.ledger.claims[HOOK, "ASSET"] == 10**18
    assert m.ledger.claims[HOOK, "USDC"] == 100_000
    assert m.ledger.balances["alice", "ASSET"] == old - 10**18
    m.cancel(p, oid, "alice")
    assert m.ledger.balances["alice", "ASSET"] == old
    assert m.ledger.claims[VAULT, "USDC"] == 100_000
    assert m.collect_fees(m.owner, "USDC", "treasury") == 100_000


def test_match_proportional_remaining_bid_and_minimum(world):
    m, p = world
    sell = m.create(p, "alice", False, 2 * 10**18, 2 * 10**9, 200_000)
    m.create(p, "bob", True, 10**9, 10**18)
    o = m.pools[p].orders[sell]
    assert (o.amount_in, o.minimum_out, o.priority_fee) == (10**18, 10**9, 100_000)
    assert o.sequence == 1
    # Both bids' filled shares, plus 0.02% of each side's proceeds.
    assert m.ledger.claims[VAULT, "USDC"] == 200_000 + trade_fee(10**9)
    assert m.ledger.claims[VAULT, "ASSET"] == trade_fee(10**18)
    assert m.ledger.claims["alice", "USDC"] == 10**9 - trade_fee(10**9)
    assert m.ledger.claims["bob", "ASSET"] == 10**18 - trade_fee(10**18)


def test_price_improvement_not_credited_to_remainder(world):
    m, p = world
    m.create(p, "bob", True, 1500 * 10**6, 10**18)
    oid = m.create(p, "alice", False, 2 * 10**18, 2000 * 10**6)
    o = m.pools[p].orders[oid]
    assert o.amount_in == 10**18
    assert o.minimum_out == 1000 * 10**6  # not 500 USDC


def test_dust_refund_closes_and_spends_remaining_bid(world):
    m, p = world
    m.set_minimum(m.owner, 500 * 10**6, p)
    old = m.ledger.balances["alice", "ASSET"]
    sell = m.create(p, "alice", False, 10**18, 1000 * 10**6)
    m.create(p, "bob", True, 750 * 10**6, 75 * 10**16)
    assert sell not in m.pools[p].orders
    assert m.ledger.balances["alice", "ASSET"] == old - 10**18
    assert m.ledger.claims["alice", "ASSET"] == 25 * 10**16  # refunds pay no trade fee
    assert m.ledger.claims[VAULT, "USDC"] == 200_000 + trade_fee(750 * 10**6)
    assert m.ledger.claims[VAULT, "ASSET"] == trade_fee(75 * 10**16)
    assert m.events[-1][-2:] == (25 * 10**16, 0)


def test_reprice_resets_sequence_and_checks_minimum(world):
    m, p = world
    oid = m.create(p, "alice", False, 10**18, 10**9)
    initial = m.pools[p].orders[oid].sequence
    m.update_price(p, oid, "alice", 10**9)
    assert m.pools[p].orders[oid].sequence > initial
    unchanged(m, lambda: m.update_price(p, oid, "bob", 10**9), "NotOrderOwner")
    unchanged(m, lambda: m.update_price(p, oid, "alice", 1), "BelowMinimumOrder")


def test_reprice_cannot_raise_sell_bid_floor(world):
    m, p = world
    m.set_minimum(m.owner, 0, p)
    oid = m.create(p, "alice", False, 10**18, 999, 0)
    unchanged(m, lambda: m.update_price(p, oid, "alice", 100 * 10**6), "PriorityFeeTooSmall")
    small = m.create(p, "alice", False, 2 * 10**18, 10 * 10**6, 10_000)
    unchanged(m, lambda: m.update_price(p, small, "alice", 1000 * 10**6), "PriorityFeeTooSmall")
    m.update_price(p, small, "alice", 5 * 10**6)
    assert m.pools[p].orders[small].minimum_out == 5 * 10**6


def test_reprice_keeps_pro_rated_bid_above_cap(world):
    m, p = world
    sell = m.create(p, "alice", False, 2 * 10**18, 1000 * 10**6)
    m.create(p, "bob", True, 500 * 10**6, 10**18)
    o = m.pools[p].orders[sell]
    assert o.priority_fee == 50_000
    unchanged(m, lambda: m.update_price(p, sell, "alice", 600 * 10**6), "PriorityFeeTooSmall")
    m.update_price(p, sell, "alice", 400 * 10**6)
    assert m.pools[p].orders[sell].minimum_out == 400 * 10**6


def test_reprice_buy_bid_floor_follows_input(world):
    m, p = world
    bid = m.create(p, "bob", True, 50 * 10**6, 1, 50_000)
    m.update_price(p, bid, "bob", 10**18)
    assert m.pools[p].orders[bid].minimum_out == 10**18


def test_priority_rekeys_after_partial_fill(world):
    m, p = world
    first = m.create(p, "alice", False, 2 * 10**18, 2 * 10**9, 200_000)
    second = m.create(p, "alice", False, 10**18, 10**9, 150_000)
    assert m.pools[p].best(False).id == first
    m.create(p, "bob", True, 10**9, 10**18)
    assert m.pools[p].best(False).id == second


def test_authorization_and_failed_escrow_roll_back(world):
    m, p = world
    m.set_executor(p, "alice", allow=False)
    unchanged(m, lambda: m.create(p, "alice", False, 10**18, 10**9), "NotAuthorizedExecutor")
    m.set_executor(p, "alice")
    m.ledger.approve("alice", ROUTER, "USDC", 0)
    unchanged(m, lambda: m.create(p, "alice", False, 10**18, 10**9), "insufficient allowance")


def test_fill_window_and_live_price(world):
    m, p = world
    oid = m.create(p, "alice", False, 2 * 10**18, 2 * 10**9, 200_000)
    m.create(p, "bob", True, 10**9, 10**18)
    unchanged(m, lambda: m.fill(p, oid, "filler", 3 * 10**9, 2 * 10**18), "Input below")
    m.update_price(p, oid, "alice", 1500 * 10**6)
    unchanged(m, lambda: m.fill(p, oid, "filler", 10**9), "Price exceeds")
    assert protocol_fee(1500 * 10**6) == 0  # the filler pays exactly the minimum
    filler_asset = m.ledger.balances["filler", "ASSET"]
    m.fill(p, oid, "filler", 1500 * 10**6, 10**18)
    assert oid not in m.pools[p].orders
    # Bids, the match's quote fee, and the maker's 0.02% of its fill proceeds.
    assert m.ledger.claims[VAULT, "USDC"] == 300_000 + trade_fee(10**9) + trade_fee(1500 * 10**6)
    assert m.ledger.claims[VAULT, "ASSET"] == trade_fee(10**18) + trade_fee(10**18)
    assert m.ledger.balances["filler", "ASSET"] - filler_asset == 10**18 - trade_fee(10**18)


def test_blocked_payout_matches_and_failed_redemption_preserves_claims(world):
    m, p = world
    m.create(p, "alice", False, 10**18, 10**9)
    m.ledger.blocked.add(("alice", "USDC"))
    m.create(p, "bob", True, 10**9, 10**18)
    assert not m.pools[p].orders
    owed = 10**9 - trade_fee(10**9)
    assert m.ledger.claims["alice", "USDC"] == owed
    assert m.ledger.claims["bob", "ASSET"] == 10**18 - trade_fee(10**18)
    m.ledger.claim_allowances["alice", "token-claims", "USDC"] = owed
    unchanged(m, lambda: m.redeem_claims("alice", "USDC", "alice", owed), "recipient rejected")
    m.ledger.blocked.remove(("alice", "USDC"))
    m.redeem_claims("alice", "USDC", "alice", owed)
    assert m.ledger.claims["alice", "USDC"] == 0


def test_native_claim_redemption_and_revert():
    m, p = setup(asset=NATIVE)
    fund(m, p, "alice"); fund(m, p, "filler")
    oid = m.create(p, "alice", True, 10**9, 10**18)
    fee = protocol_fee(10**18)
    unchanged(m, lambda: m.fill(p, oid, "filler", 2 * 10**18, msg_value=0), "msg.value")
    m.fill(p, oid, "filler", 2 * 10**18, msg_value=10**18 + fee)
    owed = 10**18 - trade_fee(10**18)
    assert m.ledger.claims["alice", NATIVE] == owed
    assert m.ledger.claims[VAULT, NATIVE] == trade_fee(10**18)
    m.ledger.claim_allowances["alice", "native-claims", NATIVE] = owed
    m.ledger.blocked.add(("receiver", NATIVE))
    unchanged(m, lambda: m.redeem_native("alice", "receiver", owed), "recipient rejected")
    m.ledger.blocked.clear()
    m.redeem_native("alice", "receiver", owed)
    assert m.ledger.balances["receiver", NATIVE] == owed


def test_native_input_exact_value():
    m, p = setup(asset=NATIVE)
    fund(m, p, "alice")
    unchanged(m, lambda: m.create(p, "alice", False, 10**18, 10**9), "msg.value")
    oid = m.create(p, "alice", False, 10**18, 10**9, msg_value=10**18)
    m.cancel(p, oid, "alice")
    assert m.ledger.claims["alice", NATIVE] == 10**18


def test_admin_and_sweep_do_not_spend_claims(world):
    m, p = world
    m.create(p, "alice", False, 10**18, 10**9)
    m.ledger.mint_test_tokens(HOOK, "ASSET", 123)
    unchanged(m, lambda: m.sweep("alice", "ASSET", "alice"), "NotOwner")
    assert m.sweep(m.owner, "ASSET", "treasury") == 123
    assert m.ledger.claims[HOOK, "ASSET"] == 10**18
    m.transfer_ownership(m.owner, "new-owner")
    unchanged(m, lambda: m.accept_ownership("alice"), "NotOwner")
    m.accept_ownership("new-owner")
    assert m.owner == "new-owner"


def test_uv4_liquidity_quote_and_fee_restore(world):
    m, p = world
    pool = m.pools[p]
    adapter = Uv4SingleRange(pool.sqrt_price_x96 // 2, pool.sqrt_price_x96 * 2)
    m.configure_liquidity(p, "lp", 10**30, 10**45, 10**45, adapter)
    m.pools[p].lp_fee = 12345
    oid = m.create(p, "alice", False, 10**18, 900 * 10**6)
    assert oid not in m.pools[p].orders
    assert m.pools[p].lp_fee == 12345
    assert any(e[0] == "LiquidityFilled" for e in m.events)
    assert any(e[0] == "PriorityFeeForfeited" for e in m.events)
    assert m.ledger.claims[VAULT, "USDC"] == minimum_bid(900 * 10**6)  # the bid goes to the FeeVault
    # The protocol takes 0.01% of the input; the rest is swapped, at the 0.02% LP fee.
    protocol_share = (10**18 + 9_999) // 10_000
    assert m.ledger.claims[VAULT, "ASSET"] == protocol_share
    assert next(e for e in m.events if e[0] == "LiquidityFilled")[3] == 10**18 - protocol_share
    assert m.ledger.claims[HOOK, "ASSET"] == 0


def test_cancel_charges_no_trade_fee(world):
    m, p = world
    old = m.ledger.balances["alice", "ASSET"]
    oid = m.create(p, "alice", False, 10**18, 10**9)
    assert m.pools[p].orders[oid].amount_in == 10**18
    m.cancel(p, oid, "alice")
    assert m.ledger.balances["alice", "ASSET"] == old
    assert m.ledger.claims[VAULT, "ASSET"] == 0


def test_exactly_touching_limits_match_and_both_sides_pay(world):
    m, p = world
    m.create(p, "alice", False, 10**18, 10**9)
    m.create(p, "bob", True, 10**9, 10**18)
    assert not m.pools[p].orders
    assert m.ledger.claims["alice", "USDC"] + m.ledger.claims[VAULT, "USDC"] - 200_000 == 10**9
    assert m.ledger.claims["bob", "ASSET"] + m.ledger.claims[VAULT, "ASSET"] == 10**18


def test_incoming_order_takes_the_pool_when_it_beats_the_book(world):
    m, p = world
    pool = m.pools[p]
    adapter = Uv4SingleRange(pool.sqrt_price_x96 // 2, pool.sqrt_price_x96 * 2)
    m.configure_liquidity(p, "lp", 10**30, 10**45, 10**45, adapter)
    # Pool spot is 1000 USDC per asset; this ask wants 1100, so it rests.
    ask = m.create(p, "alice", False, 10**18, 1100 * 10**6)
    assert ask in m.pools[p].orders
    m.create(p, "bob", True, 1100 * 10**6, 9 * 10**17)
    assert ask in m.pools[p].orders  # the worse ask is left resting
    assert not any(e[0] == "Matched" for e in m.events)
    assert any(e[0] == "LiquidityFilled" for e in m.events)


def test_failed_lp_attempt_preserves_order_and_pool(world):
    m, p = world
    pool = m.pools[p]
    adapter = Uv4SingleRange(pool.sqrt_price_x96 - 1, pool.sqrt_price_x96 + 1)
    m.configure_liquidity(p, "lp", 10**15, 10**30, 10**30, adapter)
    oid = m.create(p, "alice", False, 10**18, 10**9)
    before = deepcopy(m.__dict__)
    assert not m.fill_from_pool_liquidity(p, oid)
    assert m.__dict__ == before


def test_partial_amm_execution_reverts(world):
    class Partial:
        def quote(self, pool, amount, zfo):
            return Quote(amount - 1, 10**9, pool.sqrt_price_x96)
    m, p = world
    m.configure_liquidity(p, "lp", 10**30, 10**40, 10**40, Partial())
    oid = m.create(p, "alice", False, 10**18, 10**9)
    assert oid in m.pools[p].orders
    assert not m.fill_from_pool_liquidity(p, oid)


def sign(private, value):
    result = private.sign_msg_hash(value)
    return result.r.to_bytes(32, "big") + result.s.to_bytes(32, "big") + bytes([result.v + 27])


def signing_world():
    m, p = setup()
    private = keys.PrivateKey((123).to_bytes(32, "big"))  # public test-only key
    maker = private.public_key.to_checksum_address()
    fund(m, p, maker)
    return m, p, maker, private


def test_signed_grant_reprice_cancel_and_nonce_domains():
    m, p, maker, private = signing_world()
    m.set_executor(p, maker, allow=False)
    d = signatures.executor_digest(m.chain_id, m.pools[p], maker, ROUTER, True, 7, 100)
    sig = sign(private, d)
    m.set_executor_with_sig(p, maker, ROUTER, True, 7, 100, sig)
    unchanged(m, lambda: m.set_executor_with_sig(p, maker, ROUTER, True, 7, 100, sig), "NonceAlreadyUsed")
    oid = m.create(p, maker, False, 10**18, 10**9)
    d = signatures.action_digest(m.chain_id, m.pools[p], m.pools[p].orders[oid], 8, 100, 2 * 10**9)
    m.update_price_with_sig(p, oid, 2 * 10**9, 8, 100, sign(private, d))
    d = signatures.action_digest(m.chain_id, m.pools[p], m.pools[p].orders[oid], 7, 100)
    # Signed cancels share the hook's nonces: nonce 7 was burnt by the executor grant.
    unchanged(m, lambda: m.cancel_with_sig(p, oid, 7, 100, sign(private, d)), "NonceAlreadyUsed")
    d = signatures.action_digest(m.chain_id, m.pools[p], m.pools[p].orders[oid], 9, 100)
    m.cancel_with_sig(p, oid, 9, 100, sign(private, d))
    assert not m.pools[p].orders
    assert (maker, 9) in m.nonces


def test_invalidate_nonce_revokes_signed_cancel():
    m, p, maker, private = signing_world()
    oid = m.create(p, maker, False, 10**18, 10**9)
    d = signatures.action_digest(m.chain_id, m.pools[p], m.pools[p].orders[oid], 3, 100)
    sig = sign(private, d)
    m.invalidate_nonce(maker, 3)
    unchanged(m, lambda: m.cancel_with_sig(p, oid, 3, 100, sig), "NonceAlreadyUsed")
    assert oid in m.pools[p].orders


def test_signed_reprice_rollback_and_wrong_chain():
    m, p, maker, private = signing_world()
    oid = m.create(p, maker, False, 10**18, 10**9)
    order = m.pools[p].orders[oid]
    value = signatures.action_digest(m.chain_id + 1, m.pools[p], order, 1, 100, 2 * 10**9)
    unchanged(m, lambda: m.update_price_with_sig(p, oid, 2 * 10**9, 1, 100, sign(private, value)), "InvalidSignature")
    value = signatures.action_digest(m.chain_id, m.pools[p], order, 1, 100, 1)
    unchanged(m, lambda: m.update_price_with_sig(p, oid, 1, 1, 100, sign(private, value)), "BelowMinimumOrder")
    m.invalidate_nonce(maker, 1)
    unchanged(m, lambda: m.invalidate_nonce(maker, 1), "NonceAlreadyUsed")


def test_permit2_witness_binds_bid_and_amount():
    m, p, maker, private = signing_world()
    pool = m.pools[p]
    m.ledger.approve(maker, signatures.PERMIT2, pool.asset, U256)
    d = signatures.permit_digest(m.chain_id, pool, maker, False, 10**18, 10**9, 100_000, 1, 100)
    sig = sign(private, d)
    unchanged(m, lambda: m.create_with_sig(p, maker, False, 10**18, 10**9, 100_001, 1, 100, sig), "InvalidSignature")
    oid = m.create_with_sig(p, maker, False, 10**18, 10**9, 100_000, 1, 100, sig)
    assert oid in m.pools[p].orders
    unchanged(m, lambda: m.create_with_sig(p, maker, False, 10**18, 10**9, 100_000, 1, 100, sig), "NonceAlreadyUsed")


def test_multi_pool_and_default_minimum(world):
    m, p = world
    m.set_minimum(m.owner, 5_000_000)
    currencies = sorted(("OTHER", "USDC"), key=lambda x: int(address(x), 16))
    other = m.initialize(*currencies)
    fund(m, other, "alice")
    m.create(p, "alice", False, 10**18, 10**9)
    m.create(other, "alice", True, 10**9, 10**18)
    assert m.pools[p].minimum_order == 1_000_000
    assert m.pools[other].minimum_order == 5_000_000
    m.assert_invariants()


def test_colliding_salt_walk_and_no_match_cap_bypass(world):
    m, p = world
    ids = [m.create(p, "alice", False, 10**18, 10**9) for _ in range(10)]
    assert len(set(ids)) == 10
    m.create(p, "bob", True, 10 * 10**9, 10 * 10**18)
    assert sum(e[0] == "Matched" for e in m.events) == 8
    assert m.match_book(p, 8) == 2
    assert not m.pools[p].orders


@pytest.mark.parametrize("bad", [0, 9, 255])
def test_match_bound(world, bad):
    m, p = world
    unchanged(m, lambda: m.match_book(p, bad), "InvalidMatchBound")


def test_normal_bucket_blocking():
    result = collision_case("test", Fraction(1000), 2 * 10**15 - 1, 2_000_000, 10**18, 10**9, 20, 100)
    assert result["blocked_quote_USDC"] == "20000"
    assert result["matches_before_cancel"] == 0
    assert result["matches_after_cancel"] == 20


def test_uint_bounds_and_tiered_fee():
    assert price_key(False, True, 10**40, 1) == 1  # below the v4 range: the lowest tick
    assert price_key(False, True, 1, 10**40) == 2 * 887272 + 1  # above it: the highest tick
    assert minimum_bid(999) == 0
    assert minimum_bid(1_000_000) == 1000
    assert minimum_bid(100_000_000) == 100_000
    with pytest.raises(Revert):
        mul_div(U256, U256, 1)


def test_random_arithmetic_price_and_escrow_safety():
    r = random.Random(87123)
    for _ in range(5000):
        a, q, Q, A = [r.randrange(1, 2**r.randrange(2, 120)) for _ in range(4)]
        sell = Order("s", "s", False, True, a, q, 100000, 1)
        buy = Order("b", "b", True, False, Q, A, 100000, 2)
        assert crosses(buy, sell) == (Q * a >= q * A)
        for resting in (True, False):
            m = match_amounts(sell, buy, resting)
            if m:
                assert m.asset <= a and m.quote <= Q
                assert m.quote * a >= m.asset * q
                assert m.asset * Q >= m.quote * A


def test_random_lifecycle_campaign(world):
    m, p = world
    r = random.Random(12345)
    for _ in range(500):
        action = r.randrange(6)
        orders = list(m.pools[p].orders.values())
        before = deepcopy(m.__dict__)
        try:
            if action <= 1:
                buy = bool(action)
                asset = r.randrange(1, 11) * 10**16
                price = r.randrange(900, 1101)
                quote = asset * price // 10**12
                m.create(p, r.choice(["alice", "bob"]), buy, quote if buy else asset, asset if buy else quote)
            elif action == 2:
                m.match_book(p)
            elif orders:
                o = r.choice(orders)
                if action == 3:
                    m.cancel(p, o.id, o.owner)
                elif action == 4:
                    m.update_price(p, o.id, o.owner, o.minimum_out * r.randrange(90, 111) // 100)
                else:
                    m.fill(p, o.id, "filler", o.minimum_out + protocol_fee(o.minimum_out), o.amount_in)
        except Revert:
            assert m.__dict__ == before
        m.assert_invariants()


def test_permit2_compact_signature_and_atomic_grant():
    m, p, maker, private = signing_world()
    m.set_executor(p, maker, allow=False)
    pool = m.pools[p]
    grant_value = signatures.executor_digest(m.chain_id, pool, maker, ROUTER, True, 9, 100)
    grant = (9, 100, sign(private, grant_value))
    d = signatures.permit_digest(m.chain_id, pool, maker, False, 10**18, 10**9, 100_000, 3, 100)
    sig = private.sign_msg_hash(d)
    compact = sig.r.to_bytes(32, 'big') + (sig.s | sig.v << 255).to_bytes(32, 'big')
    unchanged(m, lambda: m.create_with_sig(p, maker, False, 10**18, 10**9, 100_000, 3, 100,
                                          compact, grant), "insufficient allowance")
    assert (maker, 9) not in m.nonces
    m.ledger.approve(maker, signatures.PERMIT2, pool.asset, U256)
    m.create_with_sig(p, maker, False, 10**18, 10**9, 100_000, 3, 100, compact, grant)
    assert (maker, 9) in m.nonces


def test_signature_expiry_and_contract_verifier():
    m, p, maker, private = signing_world()
    value = signatures.executor_digest(m.chain_id, m.pools[p], maker, ROUTER, True, 10, 0)
    unchanged(m, lambda: m.set_executor_with_sig(p, maker, ROUTER, True, 10, 0, sign(private, value)), "SignatureExpired")
    value = signatures.executor_digest(m.chain_id, m.pools[p], maker, ROUTER, False, 10, 100)
    m.contract_signature_verifiers[maker] = lambda h, sig: h == value and sig == b'valid'
    m.set_executor_with_sig(p, maker, ROUTER, False, 10, 100, b'valid')
    assert (maker, ROUTER) not in m.pools[p].executors


def test_direct_owner_cancel_after_revoking_router(world):
    m, p = world
    oid = m.create(p, "alice", False, 10**18, 10**9)
    m.set_executor(p, "alice", allow=False)
    unchanged(m, lambda: m.cancel(p, oid, "alice"), "NotAuthorizedExecutor")
    m.cancel_direct(p, oid, "alice")
    assert oid not in m.pools[p].orders


def test_former_clamp_collisions_get_distinct_ticks():
    # Under WAD keys these blockers shared the clamped lowest/highest key with honest orders and
    # outranked them by bid. Ticks span the whole v4 range, so each lands on its own worse level.
    for price, blocker_in, blocker_out, asset, quote in (
        (Fraction(1, 10**12), 2 * 10**30, 3_800_000 * 10**6, 10**36, 10**12),
        (Fraction(10**42), 1, 10**36, 1, 10**30),
    ):
        m, p = setup(price, minimum=0)
        for who in ("blocker", "honest", "buyer"):
            fund(m, p, who)
        blocker = m.create(p, "blocker", False, blocker_in, blocker_out, 100_001)
        sells = [m.create(p, "honest", False, asset, quote, 100_000) for _ in range(3)]
        assert m.pools[p].orders[blocker].price > m.pools[p].orders[sells[0]].price
        for _ in range(3):
            m.create(p, "buyer", True, quote, asset, 100_000)
        assert list(m.pools[p].orders) == [blocker]
    assert bucket_width(18, 6) == bucket_width(6, 6) == bucket_width(24, 6) == Fraction(1, 10_000)


def test_unused_cancel_cannot_cancel_replacement_incarnation():
    m, p, maker, private = signing_world()
    oid = m.create(p, maker, False, 10**18, 10**9)
    order = m.pools[p].orders[oid]
    d = signatures.action_digest(m.chain_id, m.pools[p], order, 77, 100)
    sig = sign(private, d)
    generation = order.created_sequence
    m.cancel(p, oid, maker)
    replacement = m.create(p, maker, False, 10**18, 10**9)
    assert replacement == oid
    assert m.pools[p].orders[replacement].created_sequence > generation
    unchanged(m, lambda: m.cancel_with_sig(p, replacement, 77, 100, sig), "InvalidSignature")


def test_unused_reprice_cannot_change_replacement_incarnation():
    m, p, maker, private = signing_world()
    oid = m.create(p, maker, False, 10**18, 10**9)
    order = m.pools[p].orders[oid]
    digest = signatures.action_digest(m.chain_id, m.pools[p], order, 78, 100, 2 * 10**9)
    old_sig = sign(private, digest)
    generation = order.created_sequence
    m.cancel(p, oid, maker)
    replacement = m.create(p, maker, False, 10**18, 10**9)
    assert replacement == oid
    current = m.pools[p].orders[replacement]
    assert current.created_sequence > generation
    unchanged(m, lambda: m.update_price_with_sig(p, replacement, 2 * 10**9, 78, 100, old_sig), "InvalidSignature")
    assert m.pools[p].orders[replacement].minimum_out == 10**9
    fresh = signatures.action_digest(m.chain_id, m.pools[p], current, 78, 100, 2 * 10**9)
    m.update_price_with_sig(p, replacement, 2 * 10**9, 78, 100, sign(private, fresh))
    assert m.pools[p].orders[replacement].minimum_out == 2 * 10**9
    assert (maker, 78) in m.nonces


def test_stale_signed_reprice_cannot_undo_a_direct_reprice():
    m, p, maker, private = signing_world()
    oid = m.create(p, maker, False, 10**18, 10**9)
    stale = sign(private, signatures.action_digest(m.chain_id, m.pools[p], m.pools[p].orders[oid], 91, 100, 9 * 10**8))
    m.update_price(p, oid, maker, 2 * 10**9)
    unchanged(m, lambda: m.update_price_with_sig(p, oid, 9 * 10**8, 91, 100, stale), "InvalidSignature")
    assert m.pools[p].orders[oid].minimum_out == 2 * 10**9


def test_dynamic_fee_ordering_charges_half_the_gap_a_backrun_closes(world):
    m, p = world
    pool = m.pools[p]
    adapter = Uv4SingleRange(pool.sqrt_price_x96 // 2, pool.sqrt_price_x96 * 2)
    m.configure_liquidity(p, "lp", 10**17, 10**45, 10**45, adapter)
    asset, usdc = pool.asset, pool.numeraire
    vault_before = m.ledger.claims[VAULT, asset]
    reserves_before = m.ledger.reserves[p, asset]
    # A large sell moves the price down; the first pool fill sets the window's reference tick.
    m.create(p, "alice", False, 10**20, 10 * 10**6)
    ref = pool.ref_tick
    assert tick_at_sqrt_price(pool.sqrt_price_x96) < ref - 10
    # Bob buys back in the same block and pays the dynamic fee in the asset, half to LPs, half to the vault.
    m.create(p, "bob", True, 50_000 * 10**6, 1)
    dynamic_fee_to_vault = m.ledger.claims[VAULT, asset] - vault_before
    assert dynamic_fee_to_vault > 0
    m.assert_invariants()
    # A backrun that lands after the window pays nothing: the old price is no longer a reference.
    m.create(p, "alice", False, 10**20, 10 * 10**6)
    m.block += 3
    vault = m.ledger.claims[VAULT, asset]
    m.create(p, "bob", True, 50_000 * 10**6, 1)
    assert m.ledger.claims[VAULT, asset] == vault
    m.assert_invariants()

