import pytest
from decimal import Decimal
from uv4.liquidity import (
    Liquidity,
    liquidity_y_from_sqrt_prices,
    liquidity_y_from_prices,
    liquidity_y_from_ticks,
    percentage_slippage_to_tick_bounds,
)
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


def test_liquidity_method(liq):
    x = Decimal("100")
    y = Decimal("100")
    expected = Decimal(x * y).sqrt()
    assert liq.liquidity(x, y) == expected


def test_l_x(liq):
    p = Decimal("1.0001")
    x = Decimal("100")
    pb = Decimal("1.0002")
    expected = x * (p.sqrt() * pb.sqrt() / pb.sqrt() - p.sqrt())
    assert liq.l_x(p, x, pb) == expected


def test_l_y(liq):
    p = Decimal("1.0001")
    y = Decimal("100")
    pa = Decimal("1.0000")
    expected = y / (p.sqrt() - pa.sqrt())
    assert liq.l_y(p, y, pa) == expected


def test_calculate_position_holdings_out_of_range_high(liq, tm):
    position_liquidity = Decimal("1000000")
    price = Decimal("1.001")  # above upper
    price_upper = Decimal("1.0005")
    price_lower = Decimal("1.0001")
    token0, token1 = liq.calculate_position_holdings(
        position_liquidity, price, price_upper, price_lower
    )
    assert token0 == 0
    assert token1 != 0


def test_calculate_position_holdings_out_of_range_low(liq, tm):
    position_liquidity = Decimal("1000000")
    price = Decimal("0.999")  # below lower
    price_upper = Decimal("1.0005")
    price_lower = Decimal("1.0001")
    token0, token1 = liq.calculate_position_holdings(
        position_liquidity, price, price_upper, price_lower
    )
    assert token0 != 0
    assert token1 == 0


def test_calculate_uncollected_fees(liq):
    # Mock values
    position_liquidity = Decimal("1000")
    feeGrowthGlobal0 = Decimal("100")
    feeGrowthGlobal1 = Decimal("200")
    feeGrowthOutside0_l = Decimal("10")
    feeGrowthOutside0_u = Decimal("20")
    feeGrowthInside0 = Decimal("5")
    feeGrowthOutside1_l = Decimal("15")
    feeGrowthOutside1_u = Decimal("25")
    feeGrowthInside1 = Decimal("10")
    tick_lower = -100
    tick_upper = 100
    tick = 50  # in range
    fees0, fees1 = liq.calculate_uncollected_fees(
        position_liquidity,
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
    )
    # Calculate expected manually
    f0_b = feeGrowthOutside0_l
    f1_b = feeGrowthOutside1_l
    f0_a = feeGrowthOutside0_u
    f1_a = feeGrowthOutside1_u
    f0_r = feeGrowthGlobal0 - f0_b - f0_a
    f1_r = feeGrowthGlobal1 - f1_b - f1_a
    expected_fees0 = position_liquidity * ((f0_r - feeGrowthInside0) / 2**128)
    expected_fees1 = position_liquidity * ((f1_r - feeGrowthInside1) / 2**128)
    assert fees0 == expected_fees0
    assert fees1 == expected_fees1


def test_calculate_uncollected_fees_tick_below_lower(liq):
    # Mock values
    position_liquidity = Decimal("1000")
    feeGrowthGlobal0 = Decimal("100")
    feeGrowthGlobal1 = Decimal("200")
    feeGrowthOutside0_l = Decimal("10")
    feeGrowthOutside0_u = Decimal("20")
    feeGrowthInside0 = Decimal("5")
    feeGrowthOutside1_l = Decimal("15")
    feeGrowthOutside1_u = Decimal("25")
    feeGrowthInside1 = Decimal("10")
    tick_lower = -100
    tick_upper = 100
    tick = -150  # below lower
    fees0, fees1 = liq.calculate_uncollected_fees(
        position_liquidity,
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
    )
    # Calculate expected manually
    f0_b = feeGrowthGlobal0 - feeGrowthOutside0_l
    f1_b = feeGrowthGlobal1 - feeGrowthOutside1_l
    f0_a = feeGrowthOutside0_u
    f1_a = feeGrowthOutside1_u
    f0_r = feeGrowthGlobal0 - f0_b - f0_a
    f1_r = feeGrowthGlobal1 - f1_b - f1_a
    expected_fees0 = position_liquidity * ((f0_r - feeGrowthInside0) / 2**128)
    expected_fees1 = position_liquidity * ((f1_r - feeGrowthInside1) / 2**128)
    assert fees0 == expected_fees0
    assert fees1 == expected_fees1


def test_liquidity_y_from_sqrt_prices():
    p = Decimal("1.0001")
    x = Decimal("100")
    p_a = Decimal("1.0000")
    p_b = Decimal("1.0002")
    result = liquidity_y_from_sqrt_prices(p, x, p_a, p_b)
    # Manual calc
    l_x = x * (p * p_b) / (p_b - p)
    y = l_x * (p - p_a)
    assert result == y


def test_liquidity_y_from_prices():
    p = Decimal("1.0001")
    x = Decimal("100")
    p_a = Decimal("1.0000")
    p_b = Decimal("1.0002")
    result = liquidity_y_from_prices(p, x, p_a, p_b)
    # Manual calc
    l_x = x * (p.sqrt() * p_b.sqrt()) / (p_b.sqrt() - p.sqrt())
    y = l_x * (p.sqrt() - p_a.sqrt())
    assert result == y


def test_liquidity_y_from_ticks():
    current_tick = Decimal("10")
    x = Decimal("100")
    tick_lower = Decimal("5")
    tick_upper = Decimal("15")
    result = liquidity_y_from_ticks(current_tick, x, tick_lower, tick_upper)
    p = TickMath(int(current_tick)).to_sqrt_price()
    p_a = TickMath(int(tick_lower)).to_sqrt_price()
    p_b = TickMath(int(tick_upper)).to_sqrt_price()
    l_x = x * (p * p_b) / (p_b - p)
    y = l_x * (p - p_a)
    assert result == y


def test_percentage_slippage_to_tick_bounds():
    price = Decimal("1.0001")
    rate = Decimal("0.01")
    low, high = percentage_slippage_to_tick_bounds(price, rate)
    tm = TickMath()
    mid = tm.from_price(price)
    expected_low = int(mid - rate * Decimal("100"))
    expected_high = int(mid + rate * Decimal("100"))
    assert low == expected_low
    assert high == expected_high
