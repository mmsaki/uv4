import pytest
from uv4.utils import integer_to_binary_string


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, "0b0"),
        (1, "0b1"),
        (2, "0b10"),
        (3, "0b11"),
        (4, "0b100"),
        (10, "0b1010"),
    ],
)
def test_integer_to_binary_string(n, expected):
    assert integer_to_binary_string(n) == expected