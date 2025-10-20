from uv4.liquidity import Liquidity
import pytest
from uv4.tickmath import TickMath


@pytest.fixture
def liq():
    return Liquidity()


@pytest.fixture
def tm():
    return TickMath()


# https://app.uniswap.org/positions/v3/ethereum/37
@pytest.mark.parametrize(
    ("position_liquidity", "tick_lower", "tick_upper", "sqrt_price"),
    [
        (10860507277202, 192180, 193380, 1906627091097897970122208862883908),
    ],
)
def test_position37v3(
    liq: Liquidity, tm: TickMath, position_liquidity, tick_lower, tick_upper, sqrt_price
):
    tick = tm.from_sqrt_pricex96(sqrt_price)
    # position is not in range
    is_in_range = liq.is_position_in_range(tick_lower, tick_upper, tick)
    assert not is_in_range
    token0, token1 = liq.calculate_position_holdings(
        position_liquidity,
        tm.to_price(tick),
        tm.to_price(tick_upper),
        tm.to_price(tick_lower),
    )
    assert token0 == 0
    assert token1 != 0
    assert int(token1) == 9999999999999133


# https://app.uniswap.org/positions/v4/ethereum/1
@pytest.mark.parametrize(
    ("position_liquidity", "tick_lower", "tick_upper", "sqrt_price"),
    [
        (555103547015, -887270, 887270, 1260437594239115943190250841240651),
    ],
)
def test_position1v4(
    liq: Liquidity, tm: TickMath, position_liquidity, tick_lower, tick_upper, sqrt_price
):
    tick = tm.from_sqrt_pricex96(sqrt_price)
    # position is not in range
    is_in_range = liq.is_position_in_range(tick_lower, tick_upper, tick)
    assert is_in_range
    price = tm.to_price(tick)
    price_upper = tm.to_price(tick_upper)
    price_lower = tm.to_price(tick_lower)
    token0, token1 = liq.calculate_position_holdings(
        position_liquidity,
        price,
        price_upper,
        price_lower,
    )
    assert token0 != 0
    assert token1 != 0
    assert int(token0) == 34893259  # USDC
    assert int(token1) == 8830930485638544  # ETH
