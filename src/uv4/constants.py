from decimal import Decimal

MIN_TICK = int(
    Decimal(Decimal("2") ** -Decimal("128")).log10() / Decimal("1.0001").log10()
)
MAX_TICK = int(
    Decimal(Decimal("2") ** Decimal("128")).log10() / Decimal("1.0001").log10()
)
MIN_TICK_SPACING = 1
MAX_TICK_SPACING = 2**16 // 2 - 1  # type(int16).max

assert MIN_TICK == -887272
assert MAX_TICK == 887272
assert MAX_TICK_SPACING == 32767
