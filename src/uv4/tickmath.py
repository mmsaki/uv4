from typing import Tuple
from decimal import Decimal, getcontext

getcontext().prec = 35
D = Decimal


def price_at_tick(tick: D) -> D:
    return D("1.0001") ** tick


def tick_at_price(price: D) -> Decimal:
    return D(price.log10() / D("1.0001").log10()).to_integral()


def price_at_sqrt_ratio(sqrt_price: D) -> D:
    return sqrt_price / D("2") ** D("96")


def sqrt_ratio_at_price(price: D) -> D:
    return sqrt64_96(price)


def sqrt_ratio_at_tick(tick: D) -> D:
    return sqrt64_96(price_at_tick(tick))


def tick_at_sqrt_ratio(sqrt_price: D) -> D:
    price = sqrt_price / (D("2") ** D("96"))
    return tick_at_price(price)


def sqrt64_96(d_n: D) -> D:
    k = D("96")
    q_n = d_n * (D("2") ** k)
    return q_n


def liquidity_y(p: D, x: D, p_a: D, p_b: D) -> D:
    """
    ETH/USDC
    p: <decimal> current price of token0 e.g. 2000 USDC
    x: <decimal> input amount of token token0 e.g. 2ETH
    p_a: <decimal> lower liquidity bound token1 e.g. 1500 USDC
    p_b: <decimal> upper liquidity bound token1 e.g. 2500 USDC
    """
    # liquidity of x
    l_x = x * (p.sqrt() * p_b.sqrt()) / (p_b.sqrt() - p.sqrt())
    y = l_x * (p.sqrt() - p_a.sqrt())
    return y


def percentage_to_tick_bounds(price: D, rate: D) -> Tuple[D, D]:
    mid = tick_at_price(price)
    assert rate >= D("0.01")
    low = mid - rate * D("100")
    high = mid + rate * D("100")
    return low, high
