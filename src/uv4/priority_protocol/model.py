"""Executable priority-only Async Swap lifecycle, with explicit external AMM/signature adapters.

Monetary arithmetic, matching, priority and escrow use Solidity integer rules. The ordered
book uses a sort instead of reproducing the radix allocator. Atomic calls snapshot the world.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from functools import wraps
from .arithmetic import (Order, Revert, require, uint, price_key, crosses, match_amounts, tick_at_sqrt_price,
                         MIN_TICK, MAX_TICK,
                         minimum_bid, mul_div, protocol_fee, trade_fee, Q96, I128, U64)
from .ledger import Ledger, HOOK, ROUTER, VAULT, PM, NATIVE
from .identity import address, pool_id, order_id, creation_salt, digest
from . import signatures


def atomic(fn):
    @wraps(fn)
    def run(self, *args, **kwargs):
        before = deepcopy(self.__dict__)
        outer = self._depth == 0
        self._depth += 1
        try:
            result = fn(self, *args, **kwargs)
            self._depth -= 1
            if outer:
                self.assert_invariants()
            return result
        except Exception:
            self.__dict__.clear()
            self.__dict__.update(before)
            raise
    return run


@dataclass
class Pool:
    id: bytes
    currency0: str
    currency1: str
    numeraire: str
    minimum_order: int
    sqrt_price_x96: int
    fee: int = 0x800000
    tick_spacing: int = 60
    lp_fee: int = 3000
    liquidity: int = 0
    next_sequence: int = 0
    orders: dict = field(default_factory=dict)
    executors: set = field(default_factory=set)
    quote_adapter: object = None
    legacy_priority: bool = False

    @property
    def asset(self):
        return self.currency1 if self.currency0 == self.numeraire else self.currency0

    def tokens(self, is_buy):
        return (self.numeraire, self.asset) if is_buy else (self.asset, self.numeraire)

    def best(self, is_buy):
        side = [o for o in self.orders.values() if o.is_buy == is_buy]
        return min(side, key=lambda o: ((-o.price if is_buy else o.price) if self.legacy_priority else (-o.exact_price if is_buy else o.exact_price), -o.priority_key), default=None)

    def level(self, is_buy, price):
        return sorted((o for o in self.orders.values() if o.is_buy == is_buy and o.price == price),
                      key=lambda o: -o.priority_key)

    def eligible(self, is_buy, price, limit):
        # Independent oracle: filter rational prices then sort. No Solidity trie logic.
        return next((o for o in self.level(is_buy, price)
                     if (o.exact_price >= limit if is_buy else o.exact_price <= limit)), None)

    def sequence(self):
        self.next_sequence = uint(self.next_sequence + 1, 64)
        return self.next_sequence


@dataclass(frozen=True)
class Quote:
    consumed: int
    output: int
    sqrt_price_x96: int


@dataclass
class Uv4SingleRange:
    """uv4.Swap Decimal quote; NOT a bit-exact v4 tick-crossing engine.

    Restrict the configured interval to one constant-liquidity range. Attempts to leave it
    fail instead of extrapolating liquidity. Swap's rounding may differ from on-chain v4.
    """
    lower: int
    upper: int

    def quote(self, pool, amount, zero_for_one):
        from uv4.swap import Swap
        out, after = Swap(pool.sqrt_price_x96, pool.liquidity, pool.lp_fee).quote_exact_input(amount, zero_for_one)
        require(self.lower < after < self.upper, "AMM quote crosses configured range")
        return Quote(amount, out, after)


class Protocol:
    def __init__(self, owner="governance", numeraire="USDC", chain_id=1, legacy_matching=False):
        require(owner != "" and address(owner) != address(NATIVE), "ZeroAddress")
        require(numeraire != NATIVE, "InvalidNumeraire")
        self.owner = owner
        self.pending_owner = None
        self.numeraire = numeraire
        self.chain_id = chain_id
        self.timestamp = 1
        self.block = 1
        self.default_minimum_order = 0
        self.pools = {}
        self.ledger = Ledger()
        self.nonces = set()
        self.permit_nonces = set()
        self.events = []
        self.contract_signature_verifiers = {}
        self._depth = 0
        self._claim_batch = None
        self.legacy_matching = legacy_matching

    @atomic
    def initialize(self, currency0, currency1, sqrt_price_x96=Q96, fee=0x800000, tick_spacing=60):
        require(currency0 != currency1 and self.numeraire in (currency0, currency1), "NumeraireRequired")
        require(fee == 0x800000, "DynamicFeeRequired")
        require(4295128739 <= sqrt_price_x96 < 1461446703485210103287273052203988822378723970342, "InvalidSqrtPrice")
        require(1 <= tick_spacing <= 32767, "TickSpacingOutOfBounds")
        require(int(address(currency0), 16) < int(address(currency1), 16), "CurrenciesOutOfOrder")
        pid = pool_id(currency0, currency1, fee, tick_spacing, HOOK)
        require(pid not in self.pools, "PoolAlreadyInitialized")
        self.pools[pid] = Pool(pid, currency0, currency1, self.numeraire, self.default_minimum_order,
                               sqrt_price_x96, fee, tick_spacing)
        return pid

    @atomic
    def set_executor(self, pid, caller, executor=ROUTER, allow=True):
        pair = caller, executor
        if allow:
            self.pools[pid].executors.add(pair)
        else:
            self.pools[pid].executors.discard(pair)
        self.events.append(("ExecutorSet", pid.hex(), caller, executor, allow))

    def _authorized(self, pool, owner, executor):
        require((owner, executor) in pool.executors, "NotAuthorizedExecutor")

    def _minimum(self, pool, is_buy, zfo, amount, minimum):
        threshold = pool.minimum_order
        if threshold == 0:
            return
        if is_buy:
            require(amount >= threshold, "BelowMinimumOrder")
            return
        require(minimum >= threshold, "BelowMinimumOrder")
        p = pool.sqrt_price_x96
        value = (mul_div(mul_div(amount, p, Q96), p, Q96) if zfo
                 else mul_div(mul_div(amount, Q96, p), Q96, p))
        require(value >= threshold, "BelowMinimumOrder")

    @atomic
    def create(self, pid, caller, is_buy, amount_in, minimum_out, bid=None, msg_value=0):
        """Router.swap: input and bid settle before automatic matching and an optional LP attempt."""
        return self._create(pid, caller, is_buy, amount_in, minimum_out, bid, msg_value)

    def _create(self, pid, maker, is_buy, amount_in, minimum_out, bid, msg_value, spender=ROUTER):
        pool = self.pools[pid]
        pool.legacy_priority = self.legacy_matching
        self._authorized(pool, maker, ROUTER)
        uint(amount_in); uint(minimum_out)
        require(0 < amount_in <= I128 and minimum_out > 0, "ZeroAmountOrInputOverflow")
        token_in, _ = pool.tokens(is_buy)
        zfo = token_in == pool.currency0
        require(msg_value == (amount_in if token_in == NATIVE else 0), "invalid msg.value")
        self._minimum(pool, is_buy, zfo, amount_in, minimum_out)
        notional = amount_in if is_buy else minimum_out
        if bid is None:
            bid = minimum_bid(notional)
        uint(bid, 64)
        require(bid >= minimum_bid(notional), "PriorityFeeTooSmall")
        salt = creation_salt(self.timestamp, self.block, PM, maker, amount_in, minimum_out, bid)
        oid = order_id(self.chain_id, pid, maker, zfo, salt)
        while oid in pool.orders:
            salt = digest(["bytes32"], [salt])
            oid = order_id(self.chain_id, pid, maker, zfo, salt)
        # Immediate claim mint creates unlock debt, exactly as in beforeSwap/addOrder.
        self.ledger.mint_claim(HOOK, HOOK, token_in, amount_in)
        self.ledger.mint_claim(HOOK, HOOK, self.numeraire, bid)
        order = Order(oid, maker, is_buy, zfo, amount_in, minimum_out, bid, pool.sequence(), salt)
        order.created_sequence = order.sequence
        pool.orders[oid] = order
        self.events.append(("Created", pid.hex(), deepcopy(order)))
        self.ledger.settle(maker, HOOK, token_in, amount_in, spender)
        if bid:
            self.ledger.settle(maker, HOOK, self.numeraire, bid, ROUTER)
        # The better venue goes first, then the other, each only while the order is open.
        pool_first = self._pool_beats_book(self.pools[pid], is_buy)
        for step in range(2):
            if oid not in self.pools[pid].orders:
                break
            if (step == 0) == pool_first:
                self._try_liquidity(pid, oid)
            else:
                self._match_incoming(pid, oid)
        return oid

    def _pool_beats_book(self, pool, is_buy):
        """AsyncSwap._poolBeatsBook: active liquidity and a spot price strictly better than the best
        opposite level, compared as TickPrice keys (numeraire per asset)."""
        side = [o.price for o in pool.orders.values() if o.is_buy != is_buy]
        if not side or pool.liquidity == 0:
            return False
        tick = tick_at_sqrt_price(pool.sqrt_price_x96)
        key = tick - MIN_TICK + 1 if pool.currency1 == pool.numeraire else MAX_TICK - tick + 1
        return key < min(side) if is_buy else key > max(side)

    def _settle_bid(self, pool, amount):
        if not amount:
            return
        self._credit_claim(VAULT, self.numeraire, amount)
        self.events.append(("PriorityFeeForfeited", pool.id.hex(), amount))

    def _reduce(self, pool, oid, used):
        order = pool.orders[oid]
        require(used <= order.amount_in, "input overuse")
        old_price, old_bid = order.price, order.priority_fee
        remainder = order.amount_in - used
        filled_bid = mul_div(old_bid, used, order.amount_in)
        self._settle_bid(pool, filled_bid)
        unfilled_bid = old_bid - filled_bid
        minimum = mul_div(order.minimum_out, remainder, order.amount_in, True)
        if remainder == 0 or (remainder if order.is_buy else minimum) < pool.minimum_order:
            self._settle_bid(pool, unfilled_bid)
            del pool.orders[oid]
            return remainder
        order.amount_in = remainder
        order.minimum_out = minimum
        order.priority_fee = unfilled_bid
        if order.price != old_price:
            order.sequence = pool.sequence()
        # Sorting reads the new bid, equivalent to remove/reinsert even at an unchanged price.
        return 0

    def _credit_claim(self, recipient, token, amount):
        if not amount:
            return
        if self._claim_batch is None or recipient == HOOK:
            self.ledger.transfer_claim(HOOK, recipient, token, amount)
            return
        key = recipient, token
        self._claim_batch[key] = uint(self._claim_batch.get(key, 0) + amount)
        require(len(self._claim_batch) <= 34, "claim batch overflow")

    def _escrow_payout(self, recipient, token, amount, claims=False):
        if claims:
            self._credit_claim(recipient, token, amount)
        else:
            self.ledger.burn_claim(HOOK, HOOK, token, amount)
            self.ledger.payout(HOOK, recipient, token, amount)

    def _pair(self, pool, first, second):
        if first.id not in pool.orders or second.id not in pool.orders or first.is_buy == second.is_buy:
            return False
        sell, buy = (second, first) if first.is_buy else (first, second)
        amounts = match_amounts(sell, buy, (first if first.created_sequence < second.created_sequence else second).is_buy)
        if not amounts:
            return False
        seller, buyer, sid, bid = sell.owner, buy.owner, sell.id, buy.id
        sell_refund = self._reduce(pool, sid, amounts.asset)
        buy_refund = self._reduce(pool, bid, amounts.quote)
        # Each side receives its proceeds less the 0.02% trade fee, which goes to the vault.
        asset_fee, quote_fee = trade_fee(amounts.asset), trade_fee(amounts.quote)
        self._escrow_payout(buyer, pool.asset, amounts.asset - asset_fee, claims=True)
        self._escrow_payout(seller, pool.numeraire, amounts.quote - quote_fee, claims=True)
        self._credit_claim(VAULT, pool.asset, asset_fee)
        self._credit_claim(VAULT, pool.numeraire, quote_fee)
        if sell_refund:
            self._escrow_payout(seller, pool.asset, sell_refund, claims=True)
        if buy_refund:
            self._escrow_payout(buyer, pool.numeraire, buy_refund, claims=True)
        self.events.append(("Matched", pool.id.hex(), sid, bid, amounts.asset, amounts.quote, sell_refund, buy_refund))
        return True

    def _match_incoming(self, pid, oid):
        if not self.legacy_matching:
            return self.match_book(pid, 8)
        pool = self.pools[pid]
        matched = 0
        while matched < 8 and oid in pool.orders:
            incoming = pool.orders[oid]
            opposing = pool.best(not incoming.is_buy)
            if opposing is None:
                break
            buy, sell = (incoming, opposing) if incoming.is_buy else (opposing, incoming)
            if not crosses(buy, sell):
                if self.legacy_matching or incoming.price != opposing.price:
                    break
                opposing = pool.eligible(not incoming.is_buy, opposing.price, incoming.exact_price)
                if opposing is None:
                    break
            if not self._pair(pool, incoming, opposing):
                break
            matched += 1
        return matched

    @atomic
    def match_book(self, pid, max_matches=8):
        require(1 <= max_matches <= 8, "InvalidMatchBound")
        pool, matched = self.pools[pid], 0
        self._claim_batch = {}
        while matched < max_matches:
            buy, sell = pool.best(True), pool.best(False)
            if buy is None or sell is None or buy.price < sell.price:
                break
            if not crosses(buy, sell):
                if self.legacy_matching:
                    break
                ask_price = sell.price
                minimum_ask = min(o.exact_price for o in pool.level(False, ask_price))
                buy = pool.eligible(True, buy.price, minimum_ask)
                if buy is None:
                    break
                sell = pool.eligible(False, ask_price, buy.exact_price)
                assert sell is not None
            if not self._pair(pool, buy, sell):
                break
            matched += 1
        for (recipient, token), amount in self._claim_batch.items():
            self.ledger.transfer_claim(HOOK, recipient, token, amount)
        self._claim_batch = None
        return matched

    @atomic
    def cancel(self, pid, oid, caller):
        pool = self.pools[pid]
        order = self._order(pid, oid)
        require(caller == order.owner, "Only owner can cancel")
        self._authorized(pool, order.owner, ROUTER)
        self._cancel(pool, order)

    def _cancel(self, pool, order):
        del pool.orders[order.id]
        self._escrow_payout(order.owner, pool.tokens(order.is_buy)[0], order.amount_in)
        self._settle_bid(pool, order.priority_fee)
        self.events.append(("Cancelled", pool.id.hex(), order.id))

    @atomic
    def cancel_direct(self, pid, oid, executor):
        pool, order = self.pools[pid], self._order(pid, oid)
        if executor != order.owner:
            self._authorized(pool, order.owner, executor)
        self._cancel(pool, order)

    def _order(self, pid, oid):
        require(oid in self.pools[pid].orders, "OrderNotFound")
        return self.pools[pid].orders[oid]

    @atomic
    def update_price(self, pid, oid, caller, minimum_out):
        pool, order = self.pools[pid], self._order(pid, oid)
        require(caller == order.owner, "NotOrderOwner")
        uint(minimum_out)
        require(minimum_out > 0, "ZeroAmount")
        self._minimum(pool, order.is_buy, order.zero_for_one, order.amount_in, minimum_out)
        if not order.is_buy:
            required = minimum_bid(minimum_out)
            require(minimum_out <= order.minimum_out or order.priority_fee >= required,
                    "PriorityFeeTooSmall")
        order.minimum_out = minimum_out
        order.sequence = pool.sequence()
        self.events.append(("Repriced", pid.hex(), oid, minimum_out))

    @atomic
    def fill(self, pid, oid, filler, max_price, minimum_input=0, msg_value=0):
        pool, order = self.pools[pid], deepcopy(self._order(pid, oid))
        self._authorized(pool, order.owner, ROUTER)
        uint(max_price); uint(minimum_input)
        require(order.amount_in >= minimum_input, "Input below order.amountIn")
        fee = protocol_fee(order.minimum_out)
        gross = uint(order.minimum_out + fee)
        require(gross <= max_price, "Price exceeds maxPrice")
        token_in, token_out = pool.tokens(order.is_buy)
        require(msg_value == (gross if token_out == NATIVE else 0), "invalid msg.value")
        # Router pays before calling executeOrder; amounts are captured and checked.
        self.ledger.settle(filler, HOOK, token_out, gross, ROUTER)
        del pool.orders[oid]
        self._settle_bid(pool, order.priority_fee)
        fee_out, fee_in = trade_fee(order.minimum_out), trade_fee(order.amount_in)
        self.ledger.payout(HOOK, order.owner, token_out, order.minimum_out - fee_out)
        self.ledger.mint_claim(HOOK, VAULT, token_out, fee + fee_out)
        self._escrow_payout(filler, token_in, order.amount_in - fee_in)
        self._credit_claim(VAULT, token_in, fee_in)
        self.events.append(("Filled", pid.hex(), oid, filler, order.amount_in, order.minimum_out, fee))

    @atomic
    def _liquidity_fill(self, pid, oid):
        pool, order = self.pools[pid], deepcopy(self._order(pid, oid))
        del pool.orders[oid]
        require(pool.liquidity > 0, "NoActiveLiquidity")
        require(pool.quote_adapter is not None, "No AMM quote adapter configured")
        token_in, token_out = pool.tokens(order.is_buy)
        # The protocol takes 0.01% of the input; the rest is swapped at a 0.02% LP fee.
        protocol_share = (order.amount_in + 9_999) // 10_000
        self._credit_claim(VAULT, token_in, protocol_share)
        swapped = order.amount_in - protocol_share
        self.ledger.burn_claim(HOOK, HOOK, token_in, swapped)
        previous_fee = pool.lp_fee
        pool.lp_fee = 200
        quote = pool.quote_adapter.quote(pool, swapped, order.zero_for_one)
        pool.lp_fee = previous_fee
        require(quote.consumed == swapped, "PartialLiquidityFill")
        require(0 < quote.output <= I128 and quote.output >= order.minimum_out, "LimitPriceNotMet")
        self.ledger.into_pool(HOOK, pid, token_in, quote.consumed)
        self.ledger.out_of_pool(HOOK, pid, token_out, quote.output)
        pool.sqrt_price_x96 = quote.sqrt_price_x96
        self.ledger.payout(HOOK, order.owner, token_out, quote.output)
        self._settle_bid(pool, order.priority_fee)
        self.events.append(("LiquidityFilled", pid.hex(), oid, swapped, quote.output))

    def _try_liquidity(self, pid, oid):
        try:
            self._liquidity_fill(pid, oid)
            return True
        except Revert:
            return False

    @atomic
    def fill_from_pool_liquidity(self, pid, oid):
        pool, order = self.pools[pid], self._order(pid, oid)
        self._authorized(pool, order.owner, ROUTER)
        return self._try_liquidity(pid, oid)

    @atomic
    def configure_liquidity(self, pid, provider, liquidity, amount0, amount1, adapter):
        """Fixture/external-v4 boundary: deposit backing and set active liquidity and quoting.

        Does not claim to implement v4 positions, tick crossing or LP fee growth accounting.
        """
        pool = self.pools[pid]
        uint(liquidity, 128)
        for token, amount in ((pool.currency0, amount0), (pool.currency1, amount1)):
            self.ledger.settle(provider, provider, token, amount)
            self.ledger.into_pool(provider, pid, token, amount)
        pool.liquidity = liquidity
        pool.quote_adapter = adapter

    @atomic
    def redeem_claims(self, caller, token, recipient, amount):
        require(recipient and amount > 0, "InvalidRedemption")
        self.ledger.burn_claim("token-claims", caller, token, amount)
        self.ledger.take("token-claims", recipient, token, amount)

    @atomic
    def redeem_native(self, caller, recipient, amount):
        require(recipient and address(recipient) != address(NATIVE) and amount > 0, "InvalidRedemption")
        self.ledger.burn_claim("native-claims", caller, NATIVE, amount)
        self.ledger.take("native-claims", recipient, NATIVE, amount)
        self.events.append(("NativeRedeemed", caller, recipient, amount))

    @atomic
    def collect_fees(self, caller, token, recipient):
        self._owner(caller)
        require(recipient and address(recipient) != address(NATIVE), "ZeroAddress")
        amount = self.ledger.claims[VAULT, token]
        if amount:
            self.ledger.burn_claim(VAULT, VAULT, token, amount)
            self.ledger.take(VAULT, recipient, token, amount)
        self.events.append(("FeesCollected", token, recipient, amount))
        return amount

    def _owner(self, caller):
        require(caller == self.owner, "NotOwner")

    @atomic
    def transfer_ownership(self, caller, nominee):
        self._owner(caller)
        require(nominee and address(nominee) != address(NATIVE), "ZeroAddress")
        self.pending_owner = nominee

    @atomic
    def accept_ownership(self, caller):
        require(caller == self.pending_owner, "NotOwner")
        self.owner, self.pending_owner = caller, None

    @atomic
    def set_minimum(self, caller, amount, pid=None):
        self._owner(caller)
        uint(amount)
        if pid is None:
            self.default_minimum_order = amount
        else:
            self.pools[pid].minimum_order = amount

    @atomic
    def sweep(self, caller, token, recipient):
        self._owner(caller)
        require(recipient and address(recipient) != address(NATIVE), "ZeroAddress")
        amount = self.ledger.balances[HOOK, token]
        self.ledger.transfer(HOOK, recipient, token, amount)
        return amount

    @atomic
    def invalidate_nonce(self, caller, nonce):
        uint(nonce)
        require((caller, nonce) not in self.nonces, "NonceAlreadyUsed")
        self.nonces.add((caller, nonce))

    def _verify_signature(self, maker, value, signature, nonce, deadline, nonce_set, permit2=False):
        uint(nonce); uint(deadline)
        require(self.timestamp <= deadline, "SignatureExpired")
        require((maker, nonce) not in nonce_set, "NonceAlreadyUsed")
        nonce_set.add((maker, nonce))
        verifier = self.contract_signature_verifiers.get(maker)
        valid = verifier(value, signature) if verifier else signatures.verify(maker, value, signature, permit2)
        require(valid, "InvalidSignature")

    @atomic
    def set_executor_with_sig(self, pid, maker, executor, allow, nonce, deadline, signature):
        value = signatures.executor_digest(self.chain_id, self.pools[pid], maker, executor, allow, nonce, deadline)
        self._verify_signature(maker, value, signature, nonce, deadline, self.nonces)
        self.set_executor(pid, maker, executor, allow)

    @atomic
    def update_price_with_sig(self, pid, oid, minimum, nonce, deadline, signature):
        order = self._order(pid, oid)
        value = signatures.action_digest(self.chain_id, self.pools[pid], order, nonce, deadline, minimum)
        self._verify_signature(order.owner, value, signature, nonce, deadline, self.nonces)
        self.update_price(pid, oid, order.owner, minimum)

    @atomic
    def cancel_with_sig(self, pid, oid, nonce, deadline, signature):
        pool, order = self.pools[pid], self._order(pid, oid)
        value = signatures.action_digest(self.chain_id, pool, order, nonce, deadline)
        # The Router burns the nonce through AsyncSwap.useNonce, which requires it to be the
        # maker's executor; cancel nonces share the hook's store, so invalidate_nonce revokes them.
        require(self.timestamp <= uint(deadline), "SignatureExpired")
        self._authorized(pool, order.owner, ROUTER)
        self._verify_signature(order.owner, value, signature, nonce, deadline, self.nonces)
        self._cancel(pool, order)

    @atomic
    def create_with_sig(self, pid, maker, is_buy, amount, minimum, bid, nonce, deadline, signature,
                        executor_grant=None):
        pool = self.pools[pid]
        require(pool.tokens(is_buy)[0] != NATIVE, "Native input needs swap()")
        if executor_grant and (maker, ROUTER) not in pool.executors:
            grant_nonce, grant_deadline, grant_signature = executor_grant
            self.set_executor_with_sig(pid, maker, ROUTER, True, grant_nonce, grant_deadline, grant_signature)
        value = signatures.permit_digest(self.chain_id, pool, maker, is_buy, amount, minimum, bid, nonce, deadline)
        self._verify_signature(maker, value, signature, nonce, deadline, self.permit_nonces, permit2=True)
        return self._create(pid, maker, is_buy, amount, minimum, bid, 0, signatures.PERMIT2)

    def assert_invariants(self):
        self.ledger.assert_invariants()
        obligations = {}
        for pool in self.pools.values():
            assert len(pool.orders) <= U64
            sequences = set()
            for order in pool.orders.values():
                assert order.amount_in > 0 and order.minimum_out > 0
                assert order.sequence not in sequences
                sequences.add(order.sequence)
                assert 0 <= order.priority_fee <= U64
                token = pool.tokens(order.is_buy)[0]
                obligations[token] = obligations.get(token, 0) + order.amount_in
                obligations[self.numeraire] = obligations.get(self.numeraire, 0) + order.priority_fee
        for c in set(obligations) | {c for who, c in self.ledger.claims if who == HOOK}:
            assert self.ledger.claims[HOOK, c] == obligations.get(c, 0), (c, "escrow mismatch")
