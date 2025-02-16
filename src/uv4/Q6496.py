from decimal import Decimal
from typing import Union


class Q6496:
    def __init__(self, value: Union[Decimal, int, float]) -> None:
        assert value < 2**64

        self.value = Decimal(str(value))
        self.q_number =  eval(self.to_Q6496_binary_string())

    def to_decimal(self) -> Decimal:
        """Converts Q64.96 integer fixed point to decimal
            - e.g 99035203142830421991929937920 to 1.25

        @params n: int
        @return Decimal
        """

        d = Decimal("0")
        for i in range(96, 0, -1):
            if self.q_number & 1 == 1:
                d += Decimal("2") ** -Decimal(str(i))
            self.q_number >>= 1

        return self.q_number + d

    def from_decimal(self) -> int:
        """Convert decimal to Q64.96 integer
            - e.g 1.25 to 99035203142830421991929937920
            - returns a Q64.96 fixed point integer

        @params d: Decimal
        @return int
        """

        q_number = eval(self.to_Q6496_binary_string())
        assert int(self.value * 2**96) == q_number

        return q_number

    def to_Q6496_binary_string(self) -> str:
        """Convert decimal to Q64.96 binary string
            - e.g. 0b000011110100000...
            -        |       |
            -       int(15) fraction(0.25)
            - Integer == 64 bits, fraction == 96 bits

        @params d: Decimal constraint 2^64 > d < 2^-96
        @return str: '0b00000100000101' Q64.96 format
        """

        m = self.get_64_bits_string()
        n = self.get_96_bits_precision_string()

        return "0b" + m + n

    def get_64_bits_string(self) -> str:
        """Covert integer to 64 bit string

        @params n: int constraint 2^64 > n < 0
        @return str -> '000000000000101' (64 length)
        """
        d_int = int(self.value)
        assert d_int < 2**64

        return f"{d_int:064b}"

    def get_96_bits_precision_string(self) -> str:
        """Converts fraction decimal to 96 bits
            - e.g. 0.xxxxx to '0001010111'
            - Intended to be used in Q64.96 fixed point format

        @params d: Decimal constraint 0 > d < 2^-96
        @return str: 96 bit string
        """
        d_int = int(self.value)
        d_fraction = self.value - d_int

        assert d_fraction < 1

        s = ""
        for _ in range(96):
            d_fraction *= 2
            if d_fraction >= 1:
                s += "1"
                d_fraction -= 1
            else:
                s += "0"

        return s
