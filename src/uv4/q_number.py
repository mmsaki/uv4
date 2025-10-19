from decimal import Decimal
from typing import Union


class QNumber:
    """Q Number module
    Fixed point number representation in form of Q number notation. Defaults to Q64.96.
    See: https://en.wikipedia.org/wiki/Q_(number_format)

        @param value - decimal value you want to represent in Q notation
        @param? M - number of integer bits to represent fixed point Q number notation
        @param? N - number of fraction bits to represent the fraction portion of your decimal


    >>> q = QNumber('1.0001')
    >>> q = QNumber('1.0001', M=128, N=128)
    """

    def __init__(
        self, value: Union[Decimal, int, float], M: int = 64, N: int = 96
    ) -> None:
        """Initiliaze a decimal value"""
        self.M = M
        self.N = N

        assert value < 2**self.M

        self.value = Decimal(str(value))
        self.q_number = int(self.to_binary_string(), 2)

    def to_decimal(self) -> Decimal:
        """Converts Q64.96 integer fixed point to decimal
            - e.g 99035203142830421991929937920 to 1.25

        @params n: int
        @return Decimal
        """

        d = Decimal("0")
        q = self.q_number
        for i in range(self.N, 0, -1):
            if q & 1 == 1:
                d += Decimal("2") ** -Decimal(str(i))
            q >>= 1

        return q + d

    def from_decimal(self) -> int:
        """Convert decimal to Q64.96 integer
            - e.g 1.25 to 99035203142830421991929937920
            - returns a Q64.96 fixed point integer

        @params d: Decimal
        @return int
        """

        q_number = int(self.to_binary_string(), 2)
        assert int(self.value * 2**self.N) == q_number

        return q_number

    def to_binary_string(self) -> str:
        """Convert decimal to Q64.96 binary string
            - e.g. 0b000011110100000...
            -        |       |
            -       int(15) fraction(0.25)
            - Integer == 64 bits, fraction == 96 bits

        @params d: Decimal constraint 2^64 > d < 2^-96
        @return str: '0b00000100000101' Q64.96 format
        """

        m = self.get_integer_bit_string()
        n = self.get_fraction_bit_string()

        return "0b" + m + n

    def get_integer_bit_string(self) -> str:
        """Covert integer to 64 bit string

        @return str -> '000000000000101' (64 length)
        """
        m = int(self.value)
        assert m < 2**self.M

        return f"{m:0{self.M}b}"

    def get_fraction_bit_string(self) -> str:
        """Converts fraction decimal to 96 bits
            - e.g. 0.xxxxx to '0001010111'
            - Intended to be used in Q64.96 fixed point format

        @params d: Decimal constraint 0 > d < 2^-96
        @return str: 96 bit string
        """
        m = int(self.value)
        n = self.value - m

        assert n < 1

        s = ""
        for _ in range(self.N):
            n *= 2
            if n >= 1:
                s += "1"
                n -= 1
            else:
                s += "0"

        return s


class Q6496(QNumber):
    def __init__(self, value) -> None:
        super().__init__(value, M=64, N=96)

    def get_64_bits_string(self):
        return super().get_integer_bit_string()

    def get_96_bits_string(self):
        return super().get_fraction_bit_string()


class Q128128(QNumber):
    def __init__(self, value) -> None:
        super().__init__(value, M=128, N=128)

    def get_128_integer_bits_string(self):
        return super().get_integer_bit_string()

    def get_128_fraction_bits_string(self):
        return super().get_fraction_bit_string()
