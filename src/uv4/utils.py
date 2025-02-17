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
