"""Integer arithmetic from the priority-only Async Swap contracts (no floats)."""
from dataclasses import dataclass
from fractions import Fraction
from math import isqrt

WAD = 10**18
Q96 = 2**96
U64 = 2**64 - 1
U128 = 2**128 - 1
U256 = 2**256 - 1
I128 = 2**127 - 1

class Revert(ValueError):
    pass

def require(condition, reason):
    if not condition:
        raise Revert(reason)

def uint(value, bits=256):
    require(isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**bits, f"uint{bits} overflow")
    return value

def mul_div(a, b, d, ceil=False):
    uint(a); uint(b); uint(d)
    require(d > 0, "division by zero")
    q, r = divmod(a * b, d)
    return uint(q + int(ceil and r != 0))

MIN_TICK, MAX_TICK = -887272, 887272
MIN_SQRT_PRICE = 4295128739
MAX_SQRT_PRICE = 1461446703485210103287273052203988822378723970342
_TICK_FACTORS = (
    (0x2, 0xfff97272373d413259a46990580e213a), (0x4, 0xfff2e50f5f656932ef12357cf3c7fdcc),
    (0x8, 0xffe5caca7e10e4e61c3624eaa0941cd0), (0x10, 0xffcb9843d60f6159c9db58835c926644),
    (0x20, 0xff973b41fa98c081472e6896dfb254c0), (0x40, 0xff2ea16466c96a3843ec78b326b52861),
    (0x80, 0xfe5dee046a99a2a811c461f1969c3053), (0x100, 0xfcbe86c7900a88aedcffc83b479aa3a4),
    (0x200, 0xf987a7253ac413176f2b074cf7815e54), (0x400, 0xf3392b0822b70005940c7a398e4b70f3),
    (0x800, 0xe7159475a2c29b7443b29c7fa6e889d9), (0x1000, 0xd097f3bdfd2022b8845ad8f792aa5825),
    (0x2000, 0xa9f746462d870fdf8a65dc1f90e061e5), (0x4000, 0x70d869a156d2a1b890bb3df62baf32f7),
    (0x8000, 0x31be135f97d08fd981231505542fcfa6), (0x10000, 0x9aa508b5b7a84e1c677de54f3e99bc9),
    (0x20000, 0x5d6af8dedb81196699c329225ee604), (0x40000, 0x2216e584f5fa1ea926041bedfe98),
    (0x80000, 0x48a170391f7dc42444e8fa2),
)


def sqrt_price_at_tick(tick):
    """v4 TickMath.getSqrtPriceAtTick, bit for bit."""
    a = abs(tick)
    require(a <= MAX_TICK, "InvalidTick")
    price = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 1 else 1 << 128
    for bit, factor in _TICK_FACTORS:
        if a & bit:
            price = (price * factor) >> 128
    if tick > 0:
        price = U256 // price
    return (price + (1 << 32) - 1) >> 32


def tick_at_sqrt_price(sqrt_price):
    """v4 TickMath.getTickAtSqrtPrice: the greatest tick whose sqrt price is at most `sqrt_price`."""
    require(MIN_SQRT_PRICE <= sqrt_price < MAX_SQRT_PRICE, "InvalidSqrtPrice")
    lo, hi = MIN_TICK, MAX_TICK
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sqrt_price_at_tick(mid) <= sqrt_price:
            lo = mid
        else:
            hi = mid - 1
    return lo


def floor_tick(num, den):
    """TickPrice.floorTick: the largest tick priced at most num/den, clamped to the v4 range."""
    if num // den < 1 << 64:
        sqrt_price = isqrt(mul_div(num, 1 << 192, den))
    else:
        if num // den >= 1 << 128:
            return MAX_TICK
        sqrt_price = isqrt(mul_div(num, 1 << 128, den)) << 32
    if sqrt_price < MIN_SQRT_PRICE:
        return MIN_TICK
    if sqrt_price >= MAX_SQRT_PRICE:
        return MAX_TICK
    return tick_at_sqrt_price(sqrt_price)


def price_key(is_buy, zero_for_one, amount_in, minimum_out):
    """TickPrice.key: the floor tick of the exact currency1/currency0 limit, ordered by numeraire per asset."""
    tick = floor_tick(minimum_out, amount_in) if zero_for_one else floor_tick(amount_in, minimum_out)
    return tick - MIN_TICK + 1 if is_buy != zero_for_one else MAX_TICK - tick + 1


def minimum_bid(notional):
    return min(mul_div(notional, 10, 10_000), 100_000)

def protocol_fee(net):
    """AsyncSwap.calculatePoolFee: no surcharge on top of the minimum; the trade fee comes out of proceeds."""
    uint(net)
    return 0

def trade_fee(amount):
    """AsyncFiller.tradeFee: the protocol's 0.02% of a payment, rounded up."""
    return mul_div(amount, 2, 10_000, True)

@dataclass
class Order:
    id: str
    owner: str
    is_buy: bool
    zero_for_one: bool
    amount_in: int
    minimum_out: int
    priority_fee: int
    sequence: int
    salt: bytes = bytes(32)
    created_sequence: int = 0

    @property
    def price(self):
        return price_key(self.is_buy, self.zero_for_one, self.amount_in, self.minimum_out)

    @property
    def priority_key(self):
        return (uint(self.priority_fee, 64) << 64) | (U64 - uint(self.sequence, 64))

    @property
    def exact_price(self):
        return Fraction(self.amount_in, self.minimum_out) if self.is_buy else Fraction(self.minimum_out, self.amount_in)

@dataclass(frozen=True)
class Amounts:
    asset: int = 0
    quote: int = 0

    def __bool__(self):
        return self.asset > 0 and self.quote > 0

def crosses(buy, sell):
    if buy.price != sell.price:
        return buy.price > sell.price
    return mul_div(buy.amount_in, sell.amount_in, sell.minimum_out) >= buy.minimum_out

def match_amounts(sell, buy, resting_buy):
    if resting_buy:
        q = min(mul_div(sell.amount_in, buy.amount_in, buy.minimum_out), buy.amount_in)
        if q == 0:
            return Amounts()
        a = mul_div(q, buy.minimum_out, buy.amount_in, True)
        if a > sell.amount_in or q < mul_div(a, sell.minimum_out, sell.amount_in, True):
            return Amounts()
    else:
        a = min(mul_div(buy.amount_in, sell.amount_in, sell.minimum_out), sell.amount_in)
        if a == 0:
            return Amounts()
        q = mul_div(a, sell.minimum_out, sell.amount_in, True)
        if q > buy.amount_in or a < mul_div(q, buy.minimum_out, buy.amount_in, True):
            return Amounts()
    return Amounts(a, q)

def usdc_price(order, asset_decimals=18, usdc_decimals=6):
    return order.exact_price * Fraction(10**asset_decimals, 10**usdc_decimals)

def bucket_width(asset_decimals=18, usdc_decimals=6):
    """Relative width of one book level: a v4 tick, 0.01% at any price and any decimals."""
    return Fraction(1, 10_000)
