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
    ("liquidity", "tick_lower", "tick_upper", "sqrt_price"),
    [
        (10860507277202, 192180, 193380, 1906627091097897970122208862883908),
    ],
)
def test_position37v3(
    liq: Liquidity, tm: TickMath, liquidity, tick_lower, tick_upper, sqrt_price
):
    tick = tm.from_sqrt_pricex96(sqrt_price)
    # position is not in range
    is_in_range = liq.is_position_in_range(tick_lower, tick_upper, tick)
    assert not is_in_range
    token0, token1 = liq.calculate_position_holdings(
        liquidity,
        tm.to_price(tick),
        tm.to_price(tick_upper),
        tm.to_price(tick_lower),
    )
    assert token0 == 0
    assert token1 != 0
    assert int(token1) == 9999999999999133


# https://app.uniswap.org/positions/v4/ethereum/1
@pytest.mark.parametrize(
    ("liquidity", "tick_lower", "tick_upper", "sqrt_price"),
    [
        (555103547015, -887270, 887270, 1260437594239115943190250841240651),
    ],
)
def test_position1v4(
    liq: Liquidity, tm: TickMath, liquidity, tick_lower, tick_upper, sqrt_price
):
    tick = tm.from_sqrt_pricex96(sqrt_price)
    # position is not in range
    is_in_range = liq.is_position_in_range(tick_lower, tick_upper, tick)
    assert is_in_range
    p = tm.to_price(tick)
    p_u = tm.to_price(tick_upper)
    p_l = tm.to_price(tick_lower)
    token0, token1 = liq.calculate_position_holdings(
        liquidity,
        p,
        p_u,
        p_l,
    )
    assert token0 != 0
    assert token1 != 0
    assert int(token0) == 34893259  # USDC
    assert int(token1) == 8830930485638544  # ETH


# https://app.uniswap.org/positions/v3/ethereum/37
@pytest.mark.parametrize(
    (
        "liquidity",
        "feeGrowthGlobal0",
        "feeGrowthGlobal1",
        "feeGrowthOutside0_l",
        "feeGrowthOutside0_u",
        "feeGrowthInside0",
        "feeGrowthOutside1_l",
        "feeGrowthOutside1_u",
        "feeGrowthInside1",
        "tick_lower",
        "tick_upper",
        "tick",
    ),
    [
        (
            10860507277202,
            5247194057753078598628514306485795,
            2233111119924828986464996298702686253189413,
            96197287712989292312469866057737,
            437757860306982806877467479294063,
            0,
            20741530393032227016498669306435785133483,
            101747371833570761666428696605043869042568,
            0,
            192180,
            193380,
            193397,
        ),
    ],
)
def test_position1v4_uncollected_fees(
    liquidity,
    feeGrowthGlobal0,
    feeGrowthGlobal1,
    feeGrowthOutside0_l,
    feeGrowthOutside0_u,
    feeGrowthInside0,
    feeGrowthOutside1_l,
    feeGrowthOutside1_u,
    feeGrowthInside1,
    tick_lower,
    tick_upper,
    tick,
):
    f0_a, f0_b, f1_a, f1_b, fees0, fees1 = 0, 0, 0, 0, 0, 0
    if tick >= tick_lower:
        f0_b = feeGrowthOutside0_l
        f1_b = feeGrowthOutside1_l
    else:
        f0_b = feeGrowthGlobal0 - feeGrowthOutside0_l
        f1_b = feeGrowthGlobal1 - feeGrowthOutside1_l

    if tick >= tick_upper:
        f0_a = feeGrowthGlobal0 - feeGrowthOutside0_u
        f1_a = feeGrowthGlobal1 - feeGrowthOutside1_u
    else:
        f0_a = feeGrowthOutside0_u
        f1_a = feeGrowthOutside1_u

    f0_r = feeGrowthGlobal0 - f0_b - f0_a
    f1_r = feeGrowthGlobal1 - f1_b - f1_a

    fees0 = liquidity * ((f0_r - feeGrowthInside0) / 2**128)
    fees1 = liquidity * ((f1_r - feeGrowthInside1) / 2**128)
    assert int(fees0) == 10901302
    assert int(fees1) == 2585395589026349
    assert round(float(fees1) / 10**18, 3) == float(0.003)
