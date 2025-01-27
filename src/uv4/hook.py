from uv4.constants import *  # noqa: F403


def get_hook_flags(address: int) -> str:
    return format(address & 0x3FFF, "b").zfill(14)


def has_all_flags(address: int) -> bool:
    flags = get_hook_flags(address)
    return flags == "11111111111111"


def has_before_initialize(address: int) -> bool:
    # flags = get_hook_flags(address)
    # before_intilize = flags[0]
    # print(flags)
    # return before_intilize == "1"
    mask = address & BEFORE_INITIALIZE_FLAG
    return mask == BEFORE_INITIALIZE_FLAG


def has_after_initialize_flag(address: int) -> bool:
    mask = address & AFTER_INITIALIZE_FLAG
    return mask == AFTER_INITIALIZE_FLAG


def has_before_add_liquidity_flag(address: int) -> bool:
    mask = address & BEFORE_ADD_LIQUIDITY_FLAG
    return mask == BEFORE_ADD_LIQUIDITY_FLAG


def has_after_add_liquidity_flag(address: int) -> bool:
    mask = address & AFTER_ADD_LIQUIDITY_FLAG
    return mask == AFTER_ADD_LIQUIDITY_FLAG


def has_before_remove_liquidity_flag(address: int) -> bool:
    mask = address & BEFORE_REMOVE_LIQUIDITY_FLAG
    return mask == BEFORE_REMOVE_LIQUIDITY_FLAG


def has_after_remove_liquidity_flag(address: int) -> bool:
    mask = address & AFTER_REMOVE_LIQUIDITY_FLAG
    return mask == AFTER_REMOVE_LIQUIDITY_FLAG


def has_before_swap_flag(address: int) -> bool:
    mask = address & BEFORE_SWAP_FLAG
    return mask == BEFORE_SWAP_FLAG


def has_after_swap_flag(address: int) -> bool:
    mask = address & AFTER_SWAP_FLAG
    return mask == AFTER_SWAP_FLAG


def has_before_donate_flag(address: int) -> bool:
    mask = address & BEFORE_DONATE_FLAG
    return mask == BEFORE_DONATE_FLAG


def has_after_donate_flag(address: int) -> bool:
    mask = address & AFTER_DONATE_FLAG
    return mask == AFTER_DONATE_FLAG


def has_before_swap_returns_delta_flag(address: int) -> bool:
    mask = address & BEFORE_SWAP_RETURNS_DELTA_FLAG
    return mask == BEFORE_SWAP_RETURNS_DELTA_FLAG


def has_after_swap_returns_delta_flag(address: int) -> bool:
    mask = address & AFTER_SWAP_RETURNS_DELTA_FLAG
    return mask == AFTER_SWAP_RETURNS_DELTA_FLAG


def has_after_add_liquidity_returns_delta_flag(address: int) -> bool:
    mask = address & AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG
    return mask == AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG


def has_after_remove_liquidity_returns_delta_flag(address: int) -> bool:
    mask = address & AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG
    return mask == AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG
