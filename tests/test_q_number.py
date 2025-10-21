import pytest
from typing import Tuple
from uv4.q_number import QNumber, Q6496, Q128128


@pytest.fixture
def q() -> Tuple[float, QNumber]:
    num = 1.0001
    return num, QNumber(num, 64, 96)


@pytest.mark.parametrize(
    ("num", "m", "n"),
    [
        (1.0001, 64, 96),
        (64.5, 7, 6),
    ],
)
def test_integer_bit_string(num, m, n):
    q = QNumber(num, m, n)
    assert int(f"0b{q.get_integer_bit_string()}", 2) == int(num)


@pytest.mark.parametrize(
    ("num", "m", "n", "expected"),
    [
        (0.25, 4, 6, "010000"),
        (64.5, 8, 6, "100000"),
    ],
)
def test_fraction_bit_string(num, m, n, expected):
    q = QNumber(num, m, n)
    assert q.get_fraction_bit_string() == expected


@pytest.mark.parametrize(
    ("num", "m", "n", "expected"),
    [
        (0.25, 4, 6, "0b0000010000"),
        (64.5, 8, 6, "0b01000000100000"),
    ],
)
def test_q_number_to_binary_string(num, m, n, expected):
    q = QNumber(num, m, n)
    assert q.to_binary_string() == expected


@pytest.mark.parametrize(
    ("num", "m", "n", "expected"),
    [
        (0.25, 4, 6, 0b0000010000),
        (64.5, 8, 6, 0b01000000100000),
    ],
)
def test_q_number_from_decimal(num, m, n, expected):
    q = QNumber(num, m, n)
    assert q.from_decimal() == expected


@pytest.mark.parametrize(
    ("num", "m", "n", "expected"),
    [
        (0.25, 4, 6, 0.25),
        (64.5, 8, 6, 64.5),
        (1.0001, 8, 16, 1.000091552734375),
    ],
)
def test_q_number_to_decimal(num, m, n, expected):
    q = QNumber(num, m, n)
    assert q.to_decimal() == expected


@pytest.mark.parametrize(
    ("num", "m", "n"),
    [
        pytest.param(65.5, 4, 96, marks=pytest.mark.xfail),
    ],
)
def test_q_number_fails_initiaze_larger_integer_than_possible(num, m, n):
    QNumber(num, m, n)


def test_q6496():
    q = Q6496(1.0001)
    assert q.M == 64
    assert q.N == 96
    assert q.get_64_bits_string() == q.get_integer_bit_string()
    assert q.get_96_bits_string() == q.get_fraction_bit_string()


def test_q128128():
    q = Q128128(1.0001)
    assert q.M == 128
    assert q.N == 128
    assert q.get_128_integer_bits_string() == q.get_integer_bit_string()
    assert q.get_128_fraction_bits_string() == q.get_fraction_bit_string()
