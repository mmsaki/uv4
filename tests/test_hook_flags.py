import pytest
from uv4.hook import Hook

ALL_FLAGS = 0b11111111111111


@pytest.fixture
def hook():
    return Hook(0)


def test_get_hook_flags(hook):
    hook.address = ALL_FLAGS
    flags = hook.get_hook_flags()
    assert flags == "11111111111111"


def test_has_all_flags(hook):
    hook.address = ALL_FLAGS

    result = hook.has_all_flags()
    assert result is True

    hook.address = 0b11111111111110
    assert hook.has_all_flags() is False


def test_has_before_intialize_flag(hook):
    hook.address = 0b10000000000000
    result = hook.has_before_initialize()
    assert result is True


def test_has_after_intialize_flag(hook):
    hook.address = 0b01000000000000
    result = hook.has_after_initialize_flag()
    assert result is True


def test_has_before_add_liquidity_flag(hook):
    hook.address = 0b10100000000000
    result = hook.has_before_add_liquidity_flag()
    assert result is True


def test_has_after_add_liquidity_flag(hook):
    hook.address = 0b01010000000000
    result = hook.has_after_add_liquidity_flag()
    assert result is True


def test_has_before_remove_liquidity_flag(hook):
    hook.address = 0b10101000000000
    result = hook.has_before_remove_liquidity_flag()
    assert result is True


def test_has_after_remove_liquidity_flag(hook):
    hook.address = 0b01010100000000
    result = hook.has_after_remove_liquidity_flag()
    assert result is True


def test_has_before_swap_flag(hook):
    hook.address = 0b10101010000000
    result = hook.has_before_swap_flag()
    assert result is True


def test_has_after_swap_flag(hook):
    hook.address = 0b01010101000000
    result = hook.has_after_swap_flag()
    assert result is True


def test_has_before_donate_flag(hook):
    hook.address = 0b10101010100000
    result = hook.has_before_donate_flag()
    assert result is True


def test_has_after_donate_flag(hook):
    hook.address = 0b01010101010000
    result = hook.has_after_donate_flag()
    assert result is True


def test_has_before_swap_returns_delta_flag(hook):
    hook.address = 0b10101010101000
    result = hook.has_before_swap_returns_delta_flag()
    assert result is True


def test_has_after_swap_returns_delta_flag(hook):
    hook.address = 0b01010101010100
    result = hook.has_after_swap_returns_delta_flag()
    assert result is True


def test_has_before_add_liquidity_returns_delta_flag(hook):
    hook.address = 0b10101010101010
    result = hook.has_after_add_liquidity_returns_delta_flag()
    assert result is True


def test_has_after_add_liquidity_returns_delta_flag(hook):
    hook.address = 0b01010101010101
    result = hook.has_after_remove_liquidity_returns_delta_flag()
    assert result is True
