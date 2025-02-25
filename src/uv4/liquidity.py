from typing import Tuple
from decimal import Decimal
from .tickmath import TickMath


# (uint targetETH, uint targetUSDC) = LiquidityAmounts.getAmountsForLiquidity(current, lower, upper, liquidity);
#
# uint k = FullMath.mulDiv(targetETH, WAD, targetUSDC);
#
# Richard Tiutiun (Feb 21, 2025, 8:51 AM)
# assume eth is X and usdc is Y...
# our formula is (x - ky)/(1 + kp);
#
# we are selling X to buy Y, where
# p is the price of eth, and the
# derivation steps: assume n
# is amount being swapped...
#
# (x - n)/(y + np) = k target
# x - n = ky + knp
# x - ky = n + knp
# x - ky = n(1 + kp)
#
# liquidity = LiquidityAmounts.getLiquidityForAmount1(current, upper, eth);


def liquidity_y_from_sqrt_prices(
    p: Decimal, x: Decimal, p_a: Decimal, p_b: Decimal
) -> Decimal:
    """
    ETH/USDC
    p: <decimal> current price of token0 e.g. 2000 USDC
    x: <decimal> input amount of token token0 e.g. 2ETH
    p_a: <decimal> lower liquidity bound token1 e.g. 1500 USDC
    p_b: <decimal> upper liquidity bound token1 e.g. 2500 USDC
    """
    # liquidity of x
    l_x = x * (p * p_b) / (p_b - p)
    y = l_x * (p - p_a)
    return y


def liquidity_y_from_prices(
    p: Decimal, x: Decimal, p_a: Decimal, p_b: Decimal
) -> Decimal:
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


def liquidity_y_from_ticks(
    current_tick: Decimal, x: Decimal, tick_lower: Decimal, tick_upper: Decimal
) -> Decimal:
    """
    ETH/USDC
    p: <decimal> current price of token0 e.g. 2000 USDC
    x: <decimal> input amount of token token0 e.g. 2ETH
    p_a: <decimal> lower liquidity bound token1 e.g. 1500 USDC
    p_b: <decimal> upper liquidity bound token1 e.g. 2500 USDC
    """
    p = TickMath(int(current_tick)).to_sqrt_price()
    p_a = TickMath(int(tick_lower)).to_sqrt_price()
    p_b = TickMath(int(tick_upper)).to_sqrt_price()

    # liquidity of x
    l_x = x * (p * p_b) / (p_b - p)
    y = l_x * (p - p_a)
    return y


def percentage_slippage_to_tick_bounds(
    price: Decimal, rate: Decimal
) -> Tuple[int, int]:
    mid = TickMath().from_price(price)
    assert rate >= Decimal("0.01")
    low = mid - rate * Decimal("100")  # multiply by 100 to mormalize to tick
    high = mid + rate * Decimal("100")  # multiply by 100 to mormalize to tick
    return int(low), int(high)
