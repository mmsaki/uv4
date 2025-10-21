import uv4.constants as constants


def test_constants():
    assert constants.MIN_TICK == -887272
    assert constants.MAX_TICK == 887272
    assert constants.MIN_TICK_SPACING == 1
    assert constants.MAX_TICK_SPACING == 32767
    assert constants.BEFORE_INITIALIZE_FLAG == 1 << 13
    assert constants.AFTER_INITIALIZE_FLAG == 1 << 12
    assert constants.BEFORE_ADD_LIQUIDITY_FLAG == 1 << 11
    assert constants.AFTER_ADD_LIQUIDITY_FLAG == 1 << 10
    assert constants.BEFORE_REMOVE_LIQUIDITY_FLAG == 1 << 9
    assert constants.AFTER_REMOVE_LIQUIDITY_FLAG == 1 << 8
    assert constants.BEFORE_SWAP_FLAG == 1 << 7
    assert constants.AFTER_SWAP_FLAG == 1 << 6
    assert constants.BEFORE_DONATE_FLAG == 1 << 5
    assert constants.AFTER_DONATE_FLAG == 1 << 4
    assert constants.BEFORE_SWAP_RETURNS_DELTA_FLAG == 1 << 3
    assert constants.AFTER_SWAP_RETURNS_DELTA_FLAG == 1 << 2
    assert constants.AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG == 1 << 1
    assert constants.AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG == 1 << 0