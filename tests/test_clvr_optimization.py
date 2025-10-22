import pytest


@pytest.fixture
def k():
    return 5


@pytest.mark.parametrize(
    ("initial_tick", "ticks"),
    [
        (5, (7, 6, 5, 4, 3, 1)),
        (5, (1, 3, 4, 5, 6, 7)),
        (5, (7, 6, 5, 4, -1, -3)),
        (5, (-3, -1, 4, 5, 6, 7)),
        (5, (6, 5, 4, -1, -3, 7)),
    ],
)
def test_clvr(k, initial_tick, ticks):
    accumulator = 0
    assert k < len(ticks)
    for i in range(k, len(ticks)):
        previous_tick = 0
        current_tick = ticks[i]
        if i == k:
            previous_tick = initial_tick
        else:
            previous_tick = ticks[i - k]
        diff = current_tick - previous_tick
        diff_sqrd = diff**2
        accumulator += diff_sqrd

    print("\naccumulator", accumulator)
    volatility = accumulator / (len(ticks) - k)
    print("volatility", volatility)
