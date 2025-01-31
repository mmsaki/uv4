from typing import Tuple
from decimal import Decimal, getcontext


getcontext().prec = 35


def price_at_tick(tick: int) -> Decimal:
    """Returns price at tick
    - price = 1.0001^tick

    @params tick: int
    @return price: Decimal
    """

    return Decimal("1.0001") ** Decimal(str(tick))


def tick_at_price(price: Decimal) -> int:
    """Returns tick at price
        - tick = log(price) / log(1.0001)

    @params price: Decimal
    @return tick: int
    """

    return int(price.log10() / Decimal("1.0001").log10())


def pricex96_at_tick(tick: int) -> int:
    """Returns pricex96 at a given tick

    @params tick: int
    @return price96: int
    """
    price = price_at_tick(tick)
    return price_to_pricex96(price)


def tick_at_pricex96(sqrt_price: Decimal) -> int:
    price = pricex96_to_price(sqrt_price)
    return tick_at_price(price)


def price_to_pricex96(price: Decimal) -> int:
    sqrt_price = price * (Decimal("2") ** Decimal("96"))
    return int(sqrt_price)


def pricex96_to_price(price_x96: Decimal) -> Decimal:
    return price_x96 / Decimal("2") ** Decimal("96")


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


def percentage_to_tick_bounds(price: Decimal, rate: Decimal) -> Tuple[int, int]:
    mid = tick_at_price(price)
    assert rate >= Decimal("0.01")
    low = mid - rate * Decimal("100")  # multiply by 100 to mormalize to tick
    high = mid + rate * Decimal("100")  # multiply by 100 to mormalize to tick
    return int(low), int(high)
