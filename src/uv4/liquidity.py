
from typing import Tuple
from decimal import Decimal
from .tickmath import TickMath
def liquidity_y(p: Decimal, x: Decimal, p_a: Decimal, p_b: Decimal) -> Decimal:
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


def percentage_slippage_to_tick_bounds(
    price: Decimal, rate: Decimal
) -> Tuple[int, int]:
    mid = TickMath().from_price(price)
    assert rate >= Decimal("0.01")
    low = mid - rate * Decimal("100")  # multiply by 100 to mormalize to tick
    high = mid + rate * Decimal("100")  # multiply by 100 to mormalize to tick
    return int(low), int(high)
