import pytest


@pytest.fixture
def k():
    return 5


@pytest.mark.parametrize(
    ("current_tick", "ticks"),
    [
        (5, (7, 6, 5, 4, 3, 1)),
        (5, (1, 3, 4, 5, 6, 7)),
        (5, (7, 6, 5, 4, -1, -3)),
        (5, (-3, -1, 4, 5, 6, 7)),
        (5, (6, 5, 4, -1, -3, 7)),
    ],
)
def test_clvr(k, current_tick, ticks):
    acummulator = 0
    assert k < len(ticks)
    for i in range(k, len(ticks)):
        a = 0
        b = ticks[i]
        if i == k:
            a = current_tick
        else:
            a = ticks[i - k]
        diff = b - a
        diff_sqrd = diff**2
        acummulator += diff_sqrd

    print("\ncumm", acummulator)
    volatility = acummulator / (len(ticks) - k)
    print("volatility", volatility)
