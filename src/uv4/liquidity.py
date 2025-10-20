from typing import Tuple
from decimal import Decimal
from .tickmath import TickMath


class Liquidity:
    def liquidity(self, x_virtual: Decimal, y_virtual: Decimal):
        """liqudity"""
        return Decimal(x_virtual * y_virtual).sqrt()

    def l_x(self, p: Decimal, x: Decimal, pb: Decimal):
        """liquidity of x reserves"""
        return x * (p.sqrt() * pb.sqrt() / pb.sqrt() - p.sqrt())

    def l_y(self, p: Decimal, y: Decimal, pa: Decimal):
        """liquidity of y reserves"""
        return y / (p.sqrt() - pa.sqrt())

    def is_position_in_range(self, tick_lower: int, tick_upper: int, tick_current: int):
        return tick_lower <= tick_current < tick_upper

    def calculate_position_holdings(
        self,
        is_position_inrange: bool,
        liquidity: Decimal,
        p: Decimal,
        p_upper: Decimal,
        p_lower: Decimal,
    ):
        """
        is_position_inrange - is position in range
        liquidity - the liquidity in the pool
        p - the current price
        p_upper - the price of the upper bound tick
        p_lower - the price of the lower bound tick
        """
        token0, token1 = 0, 0
        if is_position_inrange:
            token0 = (
                liquidity * (p_upper.sqrt() - p.sqrt()) / (p.sqrt() * p_upper.sqrt())
            )
            token1 = liquidity * (p.sqrt() - p_lower.sqrt())
            return token0, token1
        else:
            if p <= p_lower:
                token0 = (
                    liquidity
                    * (p_upper.sqrt() - p_lower.sqrt())
                    / (p_lower.sqrt() * p_upper.sqrt())
                )
            if p_upper <= p:
                token1 = liquidity * (p_upper.sqrt() - p_lower.sqrt())

            return token0, token1

    def calculate_uncollected_fees(
        self,
        liquidity,
        feeGrowthGlobal,
        f_r_u,
        f_r_l,
        feeGrowthInside,
        tick_upper,
        tick_lower,
        tick,
    ):
        fees0, fees1 = 0, 0

        # fees0 = liquidity * (f_r_l - ) / 2**128
        return fees0, fees1


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
