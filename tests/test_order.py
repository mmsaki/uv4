import pytest


# zeroForOne == True => Selling token zero
# zeroForOne == False => Buying token zero
@pytest.mark.parametrize(
    ("orders", "amount"),
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
def test_order(orders, amount):
    # NOTE: In an adverserial setting, a user can
    #       - insert transactions /
    #       - sandwich orders.
    #       - Backrun transction
    # Suggestion:
    #   - make it easy to sort
    #   - make it easy to verify sort
    #   - make it hard to insert
    #   - What is the computation of order insertions
    #     - Determines how easy it is to insert orders
    #     - To calculate insertions, how to solve this?
    #   - validate how algorithm picks transactions
    def validate(buys, sells, cumulative=0):
        # assert buys and sells are sorted

        if len(buys) + len(sells) == 0:
            return

        order = None
        if not buys:
            if sells:
                order = sells[0]
                assert not sells[0][0]
        if not sells:
            if buys:
                order = buys[0]
                assert buys[0][0]

        if buys and sells:
            if buys[0][1] < sells[0][1]:
                order = buys[0]
            else:
                order = sells[0]

        while order:
            # 1. process current order
            zeroForOne, amount = order

            if zeroForOne:
                cumulative += amount
                buys = buys[1:]
            else:
                cumulative -= amount
                sells = sells[1:]
            print(cumulative)

            # 2. pick next order
            if cumulative > 0:
                if sells:
                    order = sells[0]
                    assert not order[0]
                else:
                    if buys:
                        order = buys[0]
                        assert order[0]
                    return
            else:
                if buys:
                    order = buys[0]
                    assert order[0]
                else:
                    if sells:
                        order = sells[0]
                        assert not order[0]
                    else:
                        return

    (buys, sells) = orders
    validate(buys, sells)
