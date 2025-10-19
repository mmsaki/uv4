from decimal import Decimal, getcontext
from math import ceil, floor

getcontext().prec = 96


class TickMath:
    MIN_TICK = -887272
    MAX_TICK = 887272
    MIN_TICK_SPACING = 1
    MAX_TICK_SPACING = 32767
    MIN_SQRT_PRICE = 4295128739
    MAX_SQRT_PRICE = 1461446703485210103287273052203988822378723970342

    def __init__(self, tick: int = 0, tick_spacing: int = 1):
        self.tick = tick
        self.tick_spacing = tick_spacing
        self.base = Decimal("1.0001")

    def max_usable_tick(self):
        return (self.MAX_TICK / self.tick_spacing) * self.tick_spacing

    def mix_usable_tick(self):
        return (self.MIN_TICK / self.tick_spacing) * self.tick_spacing

    def to_price(self, tick: int = 0) -> Decimal:
        """Returns price at tick

        price = 1.0001^tick

        @params tick: int
        @return price: Decimal
        """
        if tick:
            return self.base ** Decimal(str(tick))
        else:
            return self.base ** Decimal(str(self.tick))

    def to_sqrt_price(self) -> Decimal:
        price = self.to_price()
        sqrt_price = price.sqrt()
        return sqrt_price

    def to_sqrt_price_x96(self) -> int:
        """Returns pricex96 at a given tick

        @params tick: int
        @return price96: int
        """
        sqrt_price = self.to_sqrt_price()
        return ceil(sqrt_price * Decimal("2") ** Decimal("96"))

    def from_price(self, price: Decimal) -> int:
        """Returns tick at price

        tick = log(price) / log(1.0001)

        @params price: Decimal
        @return tick: int
        """
        return floor(price.log10() / self.base.log10())

    def from_sqrt_price(self, sqrt_price: Decimal) -> int:
        price = sqrt_price ** Decimal("2")
        tick = self.from_price(price)
        return tick

    def from_sqrt_pricex96(self, sqrt_pricex96: int) -> int:
        sqrt_price = Decimal(str(sqrt_pricex96)) / (2**96)
        price = sqrt_price ** Decimal("2")
        tick = self.from_price(price)
        return tick

    def price_to_sqrtpricex96(self, price: Decimal) -> int:
        sqrt_price = price.sqrt()
        sqrtx96 = sqrt_price * Decimal("2") ** Decimal("96")
        return int(sqrtx96)
