from typing import Tuple
import pytest

from uv4.q_number import QNumber


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
def test_64_bits_equals_int_floor(num, m, n):
    q = QNumber(num, m, n)
    assert eval(f"0b{q.get_integer_bit_string()}") == int(num)


@pytest.mark.parametrize(
    ("num", "m", "n"),
    [
        pytest.param(65.5, 4, 96, marks=pytest.mark.xfail),
    ],
)
def test_fails_initiate_larger_integer_than_possible(num, m, n):
    QNumber(num, m, n)
