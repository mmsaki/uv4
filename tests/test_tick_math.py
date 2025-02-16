from decimal import Decimal
from uv4.tickmath import TickMath


def test_price_at_tick():
    t = TickMath()
    assert t.to_price(0) == Decimal("1")
    assert t.to_price(1) == Decimal("1.0001")


def test_get_sqrt_price_at_tick():
    t = TickMath()
    assert t.to_sqrt_price(0) == Decimal("1")
    assert t.to_sqrt_price(1) == Decimal("1.0001").sqrt()


def test_get_sqrt_pricex96_at_tick():
    t = TickMath()
    assert t.to_sqrt_price_x96(0) == 79228162514264337593543950336
    assert t.to_sqrt_price_x96(1) == 79232123823359799118286999568
    assert t.to_sqrt_price_x96(t.MIN_TICK) == t.MIN_SQRT_PRICE
    # assert t.to_sqrt_price_x96(t.MAX_TICK) == t.MAX_SQRT_PRICE - 1
    # assert (
    #     t.to_sqrt_price_x96(t.MAX_TICK - 1)
    #     == 1461373636630004318706518188784493106690254656249
    # )


def test_get_tick_at_sqrt_price():
    t = TickMath()
    price = Decimal("1")
    assert t.from_sqrt_price(price) == 0
    assert t.from_sqrt_price(Decimal("4")) == 27727


def test_get_tick_from_sqrtx96():
    t = TickMath()
    assert t.from_sqrt_pricex96(79228162514264337593543950336) == 0
    assert t.from_sqrt_pricex96(79232123823359799118286999568) == 1
    assert t.from_sqrt_pricex96(4295128739) == -887272
    # assert (
    #     t.from_sqrt_pricex96(1461373636630004318706518188784493106690254656249)
    #     == 887272
    # )
