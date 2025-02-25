from decimal import Decimal


class FullMath:
    def __init__(self) -> None:
        pass

    def mul_div(self, a: Decimal, b: Decimal, denominator: Decimal) -> int:
        # prevent division by zero error
        assert denominator > 0

        res = a * b / denominator

        return int(res)
