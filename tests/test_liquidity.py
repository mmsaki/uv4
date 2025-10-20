from uv4.liquidity import Liquidity
import pytest
from uv4.tickmath import TickMath
from decimal import Decimal, getcontext
import math

getcontext().prec = 96


@pytest.fixture
def liq():
    return Liquidity()


@pytest.mark.parametrize(
    ("liquidity", "tick_upper", "tick_lower", "sqrt_price"),
    # https://app.uniswap.org/positions/v3/ethereum/37
    [
        (10860507277202, 193380, 192180, 1906627091097897970122208862883908),
    ],
)
def test_position37(liq, liquidity, tick_lower, tick_upper, sqrt_price):
    tick = TickMath().from_sqrt_pricex96(sqrt_price)
    # position is not in range
    is_inrange = liq.is_position_in_range(tick_lower, tick_upper, tick)
    assert not is_inrange
    token0, token1 = liq.calculate_position_holdings(
        Decimal(is_inrange),
        Decimal(liquidity),
        Decimal(TickMath().to_price(tick)),
        Decimal(TickMath().to_price(tick_upper)),
        Decimal(TickMath().to_price(tick_lower)),
    )
    assert token0 == 0
    assert int(token1) == 9999999999999133
