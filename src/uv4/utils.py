from decimal import Decimal


def integer_to_binary_string(n: int):
    """Covert integer to binary string

    @params n: int
    @return str e.g. '0b101'
    """
    s = ""
    if n == 0:
        return "0b0"

    while n != 0:
        if n & 1 == 0:
            s += "0"
        else:
            s += "1"
        n >>= 1
    return "0b" + s[::-1]


def integer_to_64_bits_string(n: int) -> str:
    """Covert integer to 64 bit string

    @params n: int constraint 2^64 > n < 0
    @return str -> '000000000000101' (64 length)
    """
    assert n < 2**64
    return f"{n:064b}"


def fraction_to_96_bits_precision(d: Decimal) -> str:
    """Converts fraction decimal to 96 bits
        - e.g. 0.xxxxx to '0001010111'
        - Intended to be used in Q64.96 fixed point format

    @params d: Decimal constraint 0 > d < 2^-96
    @return str: 96 bit string
    """
    assert d < 1

    s = ""
    for _ in range(96):
        d *= 2
        if d >= 1:
            s += "1"
            d -= 1
        else:
            s += "0"
    return s


def decimal_to_Q6496_binary_string(d: Decimal) -> str:
    """Convert decimal to Q64.96 binary string
        - e.g. 0b000011110100000...
        -        |       |
        -       int(15) fraction(0.25)
        - Integer == 64 bits, fraction == 96 bits

    @params d: Decimal constraint 2^64 > d < 2^-96
    @return str: '0b00000100000101' Q64.96 format
    """

    d_int = int(d)
    d_fraction = d - d_int
    m = integer_to_64_bits_string(d_int)
    n = fraction_to_96_bits_precision(d_fraction)

    return "0b" + m + n


def decimal_to_Q6496_integer(d: Decimal) -> int:
    """Convert decimal to Q64.96 integer
        - e.g 1.25 to 99035203142830421991929937920
        - returns a Q64.96 fixed point integer

    @params d: Decimal
    @return int
    """

    q_number = eval(decimal_to_Q6496_binary_string(d))
    assert int(d * 2**96) == q_number

    return q_number


def integer_Q6496_to_decimal(n: int) -> Decimal:
    """Converts Q64.96 integer fixed point to decimal"""

    d = Decimal("0")
    for i in range(96, 0, -1):
        if n & 1 == 1:
            d += Decimal("2") ** -Decimal(str(i))
        n >>= 1
    return n + d
