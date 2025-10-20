from uv4.liquidity import Liquidity
import pytest
from uv4.tickmath import TickMath
from decimal import Decimal, getcontext

getcontext().prec = 96


@pytest.fixture
def liq():
    return Liquidity()


@pytest.mark.parametrize(
    ("liquidity", "tick_lower", "tick_upper", "sqrt_price"),
    # https://app.uniswap.org/positions/v3/ethereum/37
    [
        (10860507277202, 192180, 193380, 1906627091097897970122208862883908),
    ],
)
def test_position37v3(liq, liquidity, tick_lower, tick_upper, sqrt_price):
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


# https://app.uniswap.org/positions/v4/ethereum/1
@pytest.mark.parametrize(
    ("liquidity", "tick_lower", "tick_upper", "sqrt_price"),
    # https://app.uniswap.org/positions/v3/ethereum/37
    [
        (555103547015, -887270, 887270, 1260437594239115943190250841240651),
    ],
)
def test_position1v4(liq, liquidity, tick_lower, tick_upper, sqrt_price):
    tick = TickMath().from_sqrt_pricex96(sqrt_price)
    # position is not in range
    is_inrange = Liquidity().is_position_in_range(tick_lower, tick_upper, tick)
    assert is_inrange
    p = TickMath().to_price(tick)
    p_u = TickMath().to_price(tick_upper)
    p_l = TickMath().to_price(tick_lower)
    token0, token1 = liq.calculate_position_holdings(
        Decimal(is_inrange),
        Decimal(liquidity),
        Decimal(p),
        Decimal(p_u),
        Decimal(p_l),
    )
    assert token0 != 0
    assert token1 != 0
    assert int(token0) == 34893259  # USDC
    assert int(token1) == 8830930485638544  # ETH
