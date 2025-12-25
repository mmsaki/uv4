import pytest


# zeroForOne == True => Selling token zero
# zeroForOne == False => Buying token zero
@pytest.mark.parametrize(
    ("orders", "failure"),
    # intial price p0, top of block, the previous p n - k
    # define the picking methodology.
    # - previous direction
    # - previous amount
    # - cummulative values
    [
        (
            [
                [
                    (True, 1),
                    (True, 4),
                    (True, 80),
                    (True, 99),
                    (True, 999),
                    (True, 999),
                    (True, 999_999),
                    (True, 1_000_000),
                ],
                [
                    (False, 2),
                    (False, 7),
                    (False, 20),
                    (False, 30),
                    (False, 70),
                    (False, 100),
                    (False, 101),
                    (False, 999),
                    (False, 1001),
                    (False, 1_000_000),
                ],
            ],
            False,
        ),
        (
            [
                [
                    (True, 1),
                ],
                [
                    (False, 101),
                    (False, 1001),
                ],
            ],
            False,
        ),
        (
            [
                [],
                [],
            ],
            False,
        ),
        (
            [
                [],
                [
                    (False, 101),
                    (False, 1001),
                ],
            ],
            False,
        ),
        # (
        #     [
        #         [
        #             (False, 1),
        #         ],
        #         [],
        #     ],
        #     True,
        # ),
        # (
        #     [
        #         [
        #             (False, 1),
        #             (False, 1001),
        #         ],
        #         [
        #             (True, 101),
        #             (True, 1001),
        #         ],
        #     ],
        #     True,
        # ),
        # (
        #     [
        #         [
        #             (False, 1),
        #             (False, 1001),
        #         ],
        #         [
        #             (False, 101),
        #             (False, 1001),
        #         ],
        #     ],
        #     True,
        # ),
    ],
)
def test_order(orders, failure):
    # NOTE: In an adverserial setting, a user can
    #       - insert transactions /
    #       - sandwich orders.
    #       - Backrun transction
    # Suggestion:
    #   - make it easy to sort
    #   - make it easy to verify sort
    #   - make it hard to insert
    #   - If you can make it hard to calculate inser
    #     - computationally infiseable
    #     - to calculate insrtions
    def validate(buys, sells, dir=None, c=0):
        # assert buys and sells are sorted

        if len(orders) == 0:
            return

        o = None
        if not buys:
            if sells:
                o = sells[0]
                assert not sells[0][0]
        if not sells:
            if buys:
                o = buys[0]
                assert buys[0][0]

        if buys and sells:
            if buys[0][1] < sells[0][1]:
                o = buys[0]
            else:
                o = sells[0]

        i = 0
        while o:
            if o:
                z, a = o
            else:
                return
            if z:
                c += a
                buys = buys[i + 1 :]
            else:
                c -= a
                sells = sells[i + 1 :]
            print(c)

            if c > 0:
                if sells:
                    o = sells[0]
                    assert not o[0]
                else:
                    if buys:
                        o = buys[0]
                        assert o[0]
                    return
            else:
                if buys:
                    o = buys[0]
                    assert o[0]
                else:
                    if sells:
                        o = sells[0]
                        assert not o[0]
                    else:
                        return

    (buys, sells) = orders
    validate(buys, sells)
