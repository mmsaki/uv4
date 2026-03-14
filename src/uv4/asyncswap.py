from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, getcontext

from .async_accounting import (
    AsyncOrderAccounting,
    fee_amount_from_input,
    open_order as open_order_accounting,
)
from .async_accounting import partial_fill as partial_fill_accounting
from .async_accounting import cancel_order as cancel_order_accounting
from .swap import (
    compute_amount_from_tick,
    price_from_sqrt_price_x96,
    sqrt_price_x96_from_tick,
)

getcontext().prec = 80


class AsyncSwapError(ValueError):
    pass


class FeeMode:
    UPFRONT = "upfront"
    ON_FILL = "on_fill"


@dataclass(frozen=True)
class OracleQuote:
    tick: int
    updated_at: int


@dataclass(frozen=True)
class OracleConfig:
    max_deviation_bps: int
    max_age_seconds: int
    user_capture_bps: int = 5_000
    filler_capture_bps: int = 2_500
    protocol_capture_bps: int = 2_500


@dataclass(frozen=True)
class PoolKey:
    pool_id: str
    currency0: str
    currency1: str
    fee: int


@dataclass(frozen=True)
class Order:
    pool_id: str
    swapper: str
    tick: int


@dataclass(frozen=True)
class SwapParams:
    zero_for_one: bool
    amount_specified: int


@dataclass(frozen=True)
class SwapData:
    user: str
    key: PoolKey
    tick: int
    amount_in: int
    zero_for_one: bool
    min_amount_out: int
    value: int = 0


class PoolManager:
    def __init__(self) -> None:
        self.claim_balances: dict[tuple[str, str], int] = defaultdict(int)
        self.router_obligations: list[tuple[str, int]] = []
        self.swap_calls: list[tuple[PoolKey, SwapParams, tuple[Order, int]]] = []

    def mint(self, recipient: str, currency: str, amount: int) -> None:
        self.claim_balances[(recipient, currency)] += amount

    def burn(self, owner: str, currency: str, amount: int) -> None:
        key = (owner, currency)
        if self.claim_balances[key] < amount:
            raise AsyncSwapError("insufficient claims")
        self.claim_balances[key] -= amount

    def transfer(self, sender: str, recipient: str, currency: str, amount: int) -> None:
        self.burn(sender, currency, amount)
        self.mint(recipient, currency, amount)

    def balance_of(self, owner: str, currency: str) -> int:
        return self.claim_balances[(owner, currency)]

    def swap(
        self, key: PoolKey, params: SwapParams, hook_data: tuple[Order, int]
    ) -> tuple[int, int]:
        self.swap_calls.append((key, params, hook_data))
        specified = -abs(params.amount_specified)
        unspecified = 0
        self.router_obligations.append(
            (key.currency0 if params.zero_for_one else key.currency1, abs(specified))
        )
        return specified, unspecified


class AsyncRouter:
    def __init__(self, pool_manager: PoolManager, hook: "AsyncSwap") -> None:
        self.pool_manager = pool_manager
        self.hook = hook
        self.settlements: list[tuple[str, str, int, int]] = []

    def execute_swap(self, data: SwapData, msg_value: int = 0) -> Order:
        input_currency = data.key.currency0 if data.zero_for_one else data.key.currency1
        if input_currency == "native":
            if msg_value != data.amount_in or data.value != data.amount_in:
                raise AsyncSwapError("INVALID_NATIVE_VALUE")
        else:
            if msg_value != 0 or data.value != 0:
                raise AsyncSwapError("INVALID_NATIVE_VALUE")

        return self.unlock_callback(data)

    def unlock_callback(self, data: SwapData) -> Order:
        order = Order(pool_id=data.key.pool_id, swapper=data.user, tick=data.tick)
        params = SwapParams(
            zero_for_one=data.zero_for_one, amount_specified=-data.amount_in
        )
        hook_data = (order, data.min_amount_out)

        specified, unspecified = self.pool_manager.swap(data.key, params, hook_data)
        if specified != -data.amount_in or unspecified != 0:
            raise AsyncSwapError("SWAP_NOT_NOOPED")

        input_currency = data.key.currency0 if data.zero_for_one else data.key.currency1
        self._settle_exact_input(input_currency, data.user, data.amount_in, data.value)
        self.hook.before_swap(
            sender="router", key=data.key, params=params, hook_data=hook_data
        )
        return order

    def _settle_exact_input(
        self, input_currency: str, payer: str, amount: int, value: int
    ) -> None:
        if input_currency == "native":
            if value != amount:
                raise AsyncSwapError("INVALID_NATIVE_VALUE")
        else:
            if value != 0:
                raise AsyncSwapError("INVALID_NATIVE_VALUE")
        self.settlements.append((input_currency, payer, amount, value))


class AsyncSwap:
    def __init__(
        self,
        fee_ppm: int = 12_000,
        owner: str = "owner",
        hook_address: str = "hook",
        fee_mode: str = FeeMode.UPFRONT,
    ) -> None:
        if fee_mode not in (FeeMode.UPFRONT, FeeMode.ON_FILL):
            raise AsyncSwapError("INVALID_FEE_MODE")
        self.minimum_fee = fee_ppm
        self.protocol_owner = owner
        self.pending_owner: str | None = None
        self.hook_address = hook_address
        self.fee_mode = fee_mode
        self.pool_manager = PoolManager()
        self.router = AsyncRouter(self.pool_manager, self)
        self.pools: dict[str, PoolKey] = {}
        self.orders: dict[Order, AsyncOrderAccounting] = {}
        self.balances_in: dict[tuple[Order, bool], int] = defaultdict(int)
        self.balances_out: dict[tuple[Order, bool], int] = defaultdict(int)
        self.protocol_fees: dict[str, int] = defaultdict(int)
        self.native_balances: dict[str, int] = defaultdict(int)
        self.erc20_balances: dict[tuple[str, str], int] = defaultdict(int)
        self.oracle_quotes: dict[str, OracleQuote] = {}
        self.oracle_configs: dict[str, OracleConfig] = {}
        self.current_time = 0
        self.protocol_surplus: dict[str, int] = defaultdict(int)

    def warp(self, timestamp: int) -> None:
        self.current_time = timestamp

    def set_oracle_quote(
        self, pool_id: str, tick: int, updated_at: int | None = None
    ) -> None:
        self.oracle_quotes[pool_id] = OracleQuote(
            tick=tick,
            updated_at=self.current_time if updated_at is None else updated_at,
        )

    def set_oracle_config(
        self,
        pool_id: str,
        max_deviation_bps: int,
        max_age_seconds: int,
        user_capture_bps: int = 5_000,
        filler_capture_bps: int = 2_500,
        protocol_capture_bps: int = 2_500,
    ) -> None:
        self.oracle_configs[pool_id] = OracleConfig(
            max_deviation_bps=max_deviation_bps,
            max_age_seconds=max_age_seconds,
            user_capture_bps=user_capture_bps,
            filler_capture_bps=filler_capture_bps,
            protocol_capture_bps=protocol_capture_bps,
        )

    @staticmethod
    def _price_at_tick(tick: int) -> Decimal:
        sqrt_price_x96 = sqrt_price_x96_from_tick(tick)
        return price_from_sqrt_price_x96(sqrt_price_x96)

    def _oracle_deviation_bps(self, user_tick: int, oracle_tick: int) -> int:
        user_price = self._price_at_tick(user_tick)
        oracle_price = self._price_at_tick(oracle_tick)
        if oracle_price == 0:
            raise AsyncSwapError("INVALID_ORACLE_PRICE")
        deviation = abs(user_price - oracle_price) / oracle_price
        return int(deviation * Decimal(10_000))

    def _oracle_capture_adjustment(
        self,
        order: Order,
        key: PoolKey,
        zero_for_one: bool,
        fill_amount: int,
        gross_input_share: int,
        filler_share: int,
    ) -> tuple[int, int, int]:
        """Return (user_rebate, adjusted_filler_share, protocol_surplus_capture).

        No-revert policy: if oracle data is missing/stale, skip capture and leave the fill unchanged.
        Surplus is only captured when the user's quoted price is meaningfully worse than the oracle.
        """
        config = self.oracle_configs.get(key.pool_id)
        quote = self.oracle_quotes.get(key.pool_id)
        if config is None or quote is None:
            return 0, filler_share, 0
        if self.current_time - quote.updated_at > config.max_age_seconds:
            return 0, filler_share, 0

        deviation_bps = self._oracle_deviation_bps(order.tick, quote.tick)
        if deviation_bps <= config.max_deviation_bps:
            return 0, filler_share, 0

        oracle_amount_in, _ = compute_amount_from_tick(
            quote.tick, fill_amount, zero_for_one
        )
        fair_share = oracle_amount_in
        if self.fee_mode == FeeMode.ON_FILL:
            fair_share -= fee_amount_from_input(oracle_amount_in, key.fee)
        if fair_share >= filler_share:
            return 0, filler_share, 0

        surplus = filler_share - fair_share
        user_take = (surplus * config.user_capture_bps) // 10_000
        filler_bonus = (surplus * config.filler_capture_bps) // 10_000
        protocol_take = (surplus * config.protocol_capture_bps) // 10_000
        adjusted_filler = fair_share + filler_bonus
        return user_take, adjusted_filler, protocol_take

    def before_initialize(self, sender: str, key: PoolKey) -> None:
        if sender != self.protocol_owner:
            raise AsyncSwapError("NOT HOOK OWNER")
        if key.fee < self.minimum_fee:
            raise AsyncSwapError("FEE SET TOO LOW")

    def after_initialize(self, sender: str, key: PoolKey) -> None:
        if sender != self.protocol_owner:
            raise AsyncSwapError("NOT HOOK OWNER")
        self.pools[key.pool_id] = key

    def initialize_pool(self, key: PoolKey, sender: str | None = None) -> None:
        actual_sender = self.protocol_owner if sender is None else sender
        self.before_initialize(actual_sender, key)
        self.after_initialize(actual_sender, key)

    def transfer_ownership(self, caller: str, new_owner: str) -> None:
        if caller != self.protocol_owner:
            raise AsyncSwapError("NOT OWNER")
        self.pending_owner = new_owner

    def accept_ownership(self, caller: str) -> None:
        if caller != self.pending_owner:
            raise AsyncSwapError("NOT_PENDING_OWNER")
        self.protocol_owner = caller
        self.pending_owner = None

    def swap(
        self,
        key: PoolKey,
        user: str,
        zero_for_one: bool,
        amount_in: int,
        tick: int,
        min_amount_out: int,
        value: int = 0,
    ) -> Order:
        if amount_in <= 0:
            raise AsyncSwapError("ZERO_AMOUNT")
        data = SwapData(
            user=user,
            key=key,
            tick=tick,
            amount_in=amount_in,
            zero_for_one=zero_for_one,
            min_amount_out=min_amount_out,
            value=value,
        )
        return self.router.execute_swap(data, msg_value=value)

    def before_swap(
        self,
        sender: str,
        key: PoolKey,
        params: SwapParams,
        hook_data: tuple[Order, int],
    ) -> tuple[int, int, int]:
        if sender != "router":
            raise AsyncSwapError("UNTRUSTED ROUTER")
        if params.amount_specified >= 0:
            raise AsyncSwapError("EXACT INPUT ONLY")

        amount_in = abs(params.amount_specified)
        self._process_order(hook_data, key, params.zero_for_one, amount_in)
        return (-params.amount_specified, 0, key.fee)

    def _process_order(
        self,
        hook_data: tuple[Order, int],
        key: PoolKey,
        zero_for_one: bool,
        amount_in: int,
    ) -> None:
        order, min_amount_out = hook_data
        if order.pool_id != key.pool_id:
            raise AsyncSwapError("POOL_MISMATCH")

        fee_amount = fee_amount_from_input(amount_in, key.fee)
        _, amount_out = compute_amount_from_tick(
            order.tick, -(amount_in - fee_amount), zero_for_one
        )
        accounting = open_order_accounting(amount_in, amount_out, key.fee)
        if accounting.total_output < min_amount_out:
            raise AsyncSwapError("SLIPPAGE")

        balances_key = (order, zero_for_one)
        if self.fee_mode == FeeMode.UPFRONT:
            self.balances_in[balances_key] += amount_in - fee_amount
        else:
            self.balances_in[balances_key] += amount_in
        self.balances_out[balances_key] += accounting.total_output
        if self.fee_mode == FeeMode.UPFRONT:
            self.protocol_fees[self.input_currency(zero_for_one)] += (
                accounting.fee_amount
            )
        self.pool_manager.mint(
            self.hook_address, self.input_currency(zero_for_one), amount_in
        )

        if order in self.orders:
            existing_acc = self.orders[order]
            merged = AsyncOrderAccounting(
                gross_input=existing_acc.gross_input + accounting.gross_input,
                fee_amount=existing_acc.fee_amount + accounting.fee_amount,
                net_input=existing_acc.net_input + accounting.net_input,
                total_output=existing_acc.total_output + accounting.total_output,
                remaining_input=existing_acc.remaining_input
                + accounting.remaining_input,
                remaining_output=existing_acc.remaining_output
                + accounting.remaining_output,
                accrued_fee=existing_acc.accrued_fee + accounting.accrued_fee,
                filled_input=existing_acc.filled_input,
                delivered_output=existing_acc.delivered_output,
            )
            self.orders[order] = merged
        else:
            self.orders[order] = accounting

    def fill(
        self,
        order: Order,
        zero_for_one: bool,
        fill_amount: int,
        filler: str,
        value: int = 0,
    ) -> int:
        key = self.pools.get(order.pool_id)
        if key is None:
            raise AsyncSwapError("UNKNOWN_POOL")

        balances_key = (order, zero_for_one)
        remaining_out = self.balances_out[balances_key]
        if remaining_out == 0:
            raise AsyncSwapError("ORDER_ALREADY_FILLED")
        if fill_amount > remaining_out:
            raise AsyncSwapError("FILL_EXCEEDS_REMAINING")

        min_fill = (remaining_out + 1) // 2
        if fill_amount < min_fill:
            raise AsyncSwapError("FILL_AMOUNT_TOO_SMALL")

        remaining_in = self.balances_in[balances_key]
        gross_input_share = (fill_amount * remaining_in) // remaining_out

        output_currency = key.currency1 if zero_for_one else key.currency0
        if output_currency == "native":
            if value != fill_amount:
                raise AsyncSwapError("INVALID_NATIVE_OUTPUT_VALUE")
            self.native_balances[order.swapper] += fill_amount
        else:
            if value != 0:
                raise AsyncSwapError("INVALID_NATIVE_OUTPUT_VALUE")
            self.erc20_balances[(order.swapper, output_currency)] += fill_amount

        if self.fee_mode == FeeMode.UPFRONT:
            filler_share = gross_input_share
        else:
            fee_share = fee_amount_from_input(gross_input_share, key.fee)
            filler_share = gross_input_share - fee_share
            self.protocol_fees[self.input_currency(zero_for_one)] += fee_share

        user_rebate, filler_share, protocol_surplus = self._oracle_capture_adjustment(
            order, key, zero_for_one, fill_amount, gross_input_share, filler_share
        )

        self.balances_out[balances_key] = remaining_out - fill_amount
        self.balances_in[balances_key] = remaining_in - (
            gross_input_share - user_rebate
        )
        if protocol_surplus > 0:
            self.protocol_surplus[self.input_currency(zero_for_one)] += protocol_surplus

        self.pool_manager.transfer(
            self.hook_address, filler, self.input_currency(zero_for_one), filler_share
        )
        return filler_share

    def cancel_order(
        self, order: Order, zero_for_one: bool, caller: str
    ) -> tuple[int, str]:
        if caller != order.swapper:
            raise AsyncSwapError("NOT_ORDER_OWNER")
        key = self.pools.get(order.pool_id)
        if key is None:
            raise AsyncSwapError("UNKNOWN_POOL")

        balances_key = (order, zero_for_one)
        remaining_in = self.balances_in[balances_key]
        if remaining_in == 0:
            raise AsyncSwapError("NOTHING_TO_CANCEL")

        self.balances_in[balances_key] = 0
        self.balances_out[balances_key] = 0
        input_currency = self.input_currency(zero_for_one)
        self.pool_manager.burn(self.hook_address, input_currency, remaining_in)
        return remaining_in, input_currency

    @staticmethod
    def input_currency(zero_for_one: bool) -> str:
        return "token0" if zero_for_one else "token1"

    @staticmethod
    def output_currency(zero_for_one: bool) -> str:
        return "token1" if zero_for_one else "token0"

    def get_balance_in(self, order: Order, zero_for_one: bool) -> int:
        return self.balances_in[(order, zero_for_one)]

    def get_balance_out(self, order: Order, zero_for_one: bool) -> int:
        return self.balances_out[(order, zero_for_one)]


AsyncSwapModel = AsyncSwap
PoolManagerModel = PoolManager
AsyncOrder = Order
