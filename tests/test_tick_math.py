import pytest
from decimal import Decimal
from uv4.tickmath import TickMath


@pytest.fixture
def tickmath():
    return TickMath()


def test_price_at_tick(tickmath):
    tickmath.tick = 0
    assert tickmath.to_price() == Decimal("1")

    tickmath.tick = 1
    assert tickmath.to_price() == Decimal("1.0001")


def test_get_sqrt_price_at_tick(tickmath):
    tickmath.tick = 0
    assert tickmath.to_sqrt_price() == Decimal("1")

    tickmath.tick = 1
    assert tickmath.to_sqrt_price() == Decimal("1.0001").sqrt()


def test_get_sqrt_pricex96_at_tick(tickmath):
    tickmath.tick = 0
    assert tickmath.to_sqrt_price_x96() == 79228162514264337593543950336

    tickmath.tick = 1
    assert tickmath.to_sqrt_price_x96() == 79232123823359799118286999568

    tickmath.tick = tickmath.MIN_TICK
    assert tickmath.to_sqrt_price_x96() == tickmath.MIN_SQRT_PRICE

    # tickmath.tick = tickmath.MAX_TICK
    # assert tickmath.to_sqrt_price_x96() == tickmath.MAX_SQRT_PRICE


def test_get_tick_at_sqrt_price(tickmath):
    price = Decimal("1")
    assert tickmath.from_sqrt_price(price) == 0
    assert tickmath.from_sqrt_price(Decimal("4")) == 27727


def test_get_tick_from_sqrtx96(tickmath):
    assert tickmath.from_sqrt_pricex96(79228162514264337593543950336) == 0
    assert tickmath.from_sqrt_pricex96(79232123823359799118286999568) == 1
    assert tickmath.from_sqrt_pricex96(4295128739) == -887272
    # assert (
    #     tickmath.from_sqrt_pricex96(1461373636630004318706518188784493106690254656249)
    #     == 887272
    # )
