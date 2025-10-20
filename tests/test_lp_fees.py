import pytest
from uv4.liquidity import Liquidity


@pytest.fixture
def liq():
    return Liquidity()


# https://app.uniswap.org/positions/v3/ethereum/37
@pytest.mark.parametrize(
    (
        "position_liquidity",
        "feeGrowthGlobal0",
        "feeGrowthGlobal1",
        "feeGrowthOutside0_lower",
        "feeGrowthOutside0_upper",
        "feeGrowthInside0",
        "feeGrowthOutside1_lower",
        "feeGrowthOutside1_upper",
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
    liq,
    position_liquidity,
    feeGrowthGlobal0,
    feeGrowthGlobal1,
    feeGrowthOutside0_lower,
    feeGrowthOutside0_upper,
    feeGrowthInside0,
    feeGrowthOutside1_lower,
    feeGrowthOutside1_upper,
    feeGrowthInside1,
    tick_lower,
    tick_upper,
    tick,
):
    fees0, fees1 = liq.calculate_uncollected_fees(
        position_liquidity,
        feeGrowthGlobal0,
        feeGrowthGlobal1,
        feeGrowthOutside0_lower,
        feeGrowthOutside0_upper,
        feeGrowthInside0,
        feeGrowthOutside1_lower,
        feeGrowthOutside1_upper,
        feeGrowthInside1,
        tick_lower,
        tick_upper,
        tick,
    )
    assert int(fees0) == 10901302
    assert int(fees1) == 2585395589026349
    assert round(float(fees1) / 10**18, 3) == float(0.003)
