from uv4.hook import get_hook_flags
from uv4.hook import has_all_flags
from uv4.hook import has_before_initialize
from uv4.hook import has_after_initialize_flag
from uv4.hook import has_before_add_liquidity_flag
from uv4.hook import has_after_add_liquidity_flag
from uv4.hook import has_before_remove_liquidity_flag
from uv4.hook import has_after_remove_liquidity_flag
from uv4.hook import has_before_swap_flag
from uv4.hook import has_after_swap_flag
from uv4.hook import has_before_donate_flag
from uv4.hook import has_after_donate_flag
from uv4.hook import has_before_swap_returns_delta_flag
from uv4.hook import has_after_swap_returns_delta_flag
from uv4.hook import has_after_add_liquidity_returns_delta_flag
from uv4.hook import has_after_remove_liquidity_returns_delta_flag

ALL_FLAGS = 0b11111111111111


def test_get_hook_flags():
    address = ALL_FLAGS
    flags = get_hook_flags(address)
    assert flags == "11111111111111"


def test_has_all_flags():
    address = ALL_FLAGS
    result = has_all_flags(address)
    assert result is True
    assert has_all_flags(0b11111111111110) is False


def test_has_before_intialize_flag():
    address = 0b10000000000000
    result = has_before_initialize(address)
    assert result is True


def test_has_after_intialize_flag():
    address = 0b01000000000000
    result = has_after_initialize_flag(address)
    assert result is True


def test_has_before_add_liquidity_flag():
    address = 0b10100000000000
    result = has_before_add_liquidity_flag(address)
    assert result is True


def test_has_after_add_liquidity_flag():
    address = 0b01010000000000
    result = has_after_add_liquidity_flag(address)
    assert result is True


def test_has_before_remove_liquidity_flag():
    address = 0b10101000000000
    result = has_before_remove_liquidity_flag(address)
    assert result is True


def test_has_after_remove_liquidity_flag():
    address = 0b01010100000000
    result = has_after_remove_liquidity_flag(address)
    assert result is True


def test_has_before_swap_flag():
    address = 0b10101010000000
    result = has_before_swap_flag(address)
    assert result is True


def test_has_after_swap_flag():
    address = 0b01010101000000
    result = has_after_swap_flag(address)
    assert result is True


def test_has_before_donate_flag():
    address = 0b10101010100000
    result = has_before_donate_flag(address)
    assert result is True


def test_has_after_donate_flag():
    address = 0b01010101010000
    result = has_after_donate_flag(address)
    assert result is True


def test_has_before_swap_returns_delta_flag():
    address = 0b10101010101000
    result = has_before_swap_returns_delta_flag(address)
    assert result is True


def test_has_after_swap_returns_delta_flag():
    address = 0b01010101010100
    result = has_after_swap_returns_delta_flag(address)
    assert result is True


def test_has_before_add_liquidity_returns_delta_flag():
    address = 0b10101010101010
    result = has_after_add_liquidity_returns_delta_flag(address)
    assert result is True


def test_has_after_add_liquidity_returns_delta_flag():
    address = 0b01010101010101
    result = has_after_remove_liquidity_returns_delta_flag(address)
    assert result is True
