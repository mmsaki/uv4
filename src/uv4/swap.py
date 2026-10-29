from typing import Tuple
from decimal import Decimal, getcontext

getcontext().prec = 96

Q96 = Decimal("2") ** Decimal("96")


class Swap:
    """Quote-style swap calculator for Uniswap V4.

    Computes expected output amounts for a given input amount within
    a single liquidity range (no tick-crossing). Supports LP fee
    deduction from the input amount before computing the swap.

    Usage:
        >>> from uv4 import Swap, TickMath
        >>> tm = TickMath(tick=0)
        >>> sqrt_price_x96 = tm.to_sqrt_price_x96()
        >>> s = Swap(sqrt_price_x96, liquidity=1_000_000 * 10**18, fee=10000)
        >>> amount_out, new_sqrt_price_x96 = s.quote_exact_input(
        ...     amount_in=1 * 10**18, zero_for_one=True
        ... )
    """

    # fee is in hundredths of a bip (1e-6), same as Uniswap V4
    # e.g. 3000 = 0.30%, 10000 = 1.00%, 12000 = 1.20%
    MAX_FEE = 1_000_000  # 100%

    def __init__(
        self,
        sqrt_price_x96: int,
        liquidity: int,
        fee: int = 0,
    ) -> None:
        """Initialize a swap quote calculator.

        @param sqrt_price_x96 - current pool sqrtPriceX96 (Q64.96 encoded)
        @param liquidity - current in-range liquidity (L)
        @param fee - LP fee in hundredths of a bip (e.g. 3000 = 0.30%, 12000 = 1.20%)
        """
        assert sqrt_price_x96 > 0, "sqrt_price_x96 must be positive"
        assert liquidity > 0, "liquidity must be positive"
        assert 0 <= fee < self.MAX_FEE, f"fee must be in [0, {self.MAX_FEE})"

        self.sqrt_price_x96 = sqrt_price_x96
        self.liquidity = Decimal(str(liquidity))
        self.fee = Decimal(str(fee))
        self.sqrt_price = Decimal(str(sqrt_price_x96)) / Q96

    def _apply_fee(self, amount_in: Decimal) -> Tuple[Decimal, Decimal]:
        """Deduct LP fee from input amount.

        @param amount_in - raw input amount
        @return (amount_in_after_fee, fee_amount)
        """
        fee_rate = self.fee / Decimal(str(self.MAX_FEE))
        fee_amount = amount_in * fee_rate
        return amount_in - fee_amount, fee_amount

    def quote_exact_input(self, amount_in: int, zero_for_one: bool) -> Tuple[int, int]:
        """Compute the expected output amount for an exact input swap.

        This is a single-tick-range quote (does not cross initialized ticks).
        The fee is deducted from amount_in before computing the output.

        zeroForOne = True:  selling token0, receiving token1 (price decreases)
            new_sqrtP = (L * sqrtP) / (L + amount_in_net * sqrtP)
            amount_out = L * (sqrtP - new_sqrtP)

        zeroForOne = False: selling token1, receiving token0 (price increases)
            new_sqrtP = sqrtP + amount_in_net / L
            amount_out = L * (1/sqrtP - 1/new_sqrtP)

        @param amount_in - exact input amount (in token raw units)
        @param zero_for_one - True if swapping token0 -> token1
        @return (amount_out, new_sqrt_price_x96)
        """
        amount_in_d = Decimal(str(amount_in))
        amount_in_net, fee_amount = self._apply_fee(amount_in_d)

        assert amount_in_net > 0, "amount_in_net must be positive after fee"

        sqrtP = self.sqrt_price
        L = self.liquidity

        if zero_for_one:
            # selling token0 for token1, price goes down
            # delta(1/sqrtP) = amount_in_net / L
            # new_sqrtP = (L * sqrtP) / (L + amount_in_net * sqrtP)
            new_sqrtP = (L * sqrtP) / (L + amount_in_net * sqrtP)
            assert new_sqrtP > 0, "price underflow"

            # amount_out of token1 = L * (sqrtP - new_sqrtP)
            amount_out = L * (sqrtP - new_sqrtP)
        else:
            # selling token1 for token0, price goes up
            # delta(sqrtP) = amount_in_net / L
            # new_sqrtP = sqrtP + amount_in_net / L
            new_sqrtP = sqrtP + amount_in_net / L

            # amount_out of token0 = L * (1/sqrtP - 1/new_sqrtP)
            amount_out = L * (1 / sqrtP - 1 / new_sqrtP)

        new_sqrt_price_x96 = int(new_sqrtP * Q96)

        return int(amount_out), new_sqrt_price_x96

    def quote_exact_output(
        self, amount_out: int, zero_for_one: bool
    ) -> Tuple[int, int]:
        """Compute the required input amount for an exact output swap.

        zeroForOne = True:  want exact token1 out, paying token0
            new_sqrtP = sqrtP - amount_out / L
            amount_in = L * (1/new_sqrtP - 1/sqrtP)

        zeroForOne = False: want exact token0 out, paying token1
            new_sqrtP = (L * sqrtP) / (L - amount_out * sqrtP)
            amount_in = L * (new_sqrtP - sqrtP)

        Fee is added on top of the computed raw input.

        @param amount_out - exact desired output amount
        @param zero_for_one - True if swapping token0 -> token1
        @return (amount_in_with_fee, new_sqrt_price_x96)
        """
        amount_out_d = Decimal(str(amount_out))
        sqrtP = self.sqrt_price
        L = self.liquidity

        if zero_for_one:
            # want exact token1 out, pay token0
            # new_sqrtP = sqrtP - amount_out / L
            new_sqrtP = sqrtP - amount_out_d / L
            assert new_sqrtP > 0, "price underflow: output exceeds available liquidity"

            # amount_in (before fee) = L * (1/new_sqrtP - 1/sqrtP)
            amount_in_raw = L * (1 / new_sqrtP - 1 / sqrtP)
        else:
            # want exact token0 out, pay token1
            # new_sqrtP = (L * sqrtP) / (L - amount_out * sqrtP)
            denominator = L - amount_out_d * sqrtP
            assert denominator > 0, "output exceeds available liquidity"
            new_sqrtP = (L * sqrtP) / denominator

            # amount_in (before fee) = L * (new_sqrtP - sqrtP)
            amount_in_raw = L * (new_sqrtP - sqrtP)

        # Add fee on top: amount_in_with_fee = amount_in_raw / (1 - fee_rate)
        fee_rate = self.fee / Decimal(str(self.MAX_FEE))
        if fee_rate > 0:
            amount_in_with_fee = amount_in_raw / (1 - fee_rate)
        else:
            amount_in_with_fee = amount_in_raw

        new_sqrt_price_x96 = int(new_sqrtP * Q96)

        return int(amount_in_with_fee) + 1, new_sqrt_price_x96  # +1 for rounding up


# ---------------------------------------------------------------------------
# AsyncSwap: Intent-based swap calculations (no liquidity curve)
# ---------------------------------------------------------------------------
#
# In AsyncSwap, the hook intercepts the swap in beforeSwap and handles
# all accounting itself. There is no AMM liquidity — fillers/solvers
# provide the other side. The price comes from the Order's tick or
# sqrtPrice field.
#
# The math is simpler than an AMM swap because we're just converting
# at a fixed price point, not sliding along a liquidity curve.
#
# Uniswap V4 convention:
#   amountSpecified < 0  =>  exact input  (user specifies what they GIVE)
#   amountSpecified > 0  =>  exact output (user specifies what they WANT)
#   zeroForOne = True    =>  selling token0 for token1 (price goes DOWN)
#   zeroForOne = False   =>  selling token1 for token0 (price goes UP)
#
# Price definition:
#   price = token1 / token0
#   sqrtPriceX96 = sqrt(price) * 2^96
#   price = (sqrtPriceX96 / 2^96)^2
#
# Amount conversions at a fixed price:
#   token0 -> token1:  amount1 = amount0 * price
#   token1 -> token0:  amount0 = amount1 / price
#
# In Solidity using Q64.96 math (FullMath.mulDiv):
#   // token0 -> token1:
#   amount1 = FullMath.mulDiv(
#       FullMath.mulDiv(amount0, sqrtPriceX96, Q96),
#       sqrtPriceX96, Q96
#   );
#   // token1 -> token0:
#   amount0 = FullMath.mulDiv(
#       FullMath.mulDiv(amount1, Q96, sqrtPriceX96),
#       Q96, sqrtPriceX96
#   );
# ---------------------------------------------------------------------------


def price_from_sqrt_price_x96(sqrt_price_x96: int) -> Decimal:
    """Convert sqrtPriceX96 (Q64.96) to a human-readable price.

    price = (sqrtPriceX96 / 2^96)^2

    @param sqrt_price_x96: The Q64.96 encoded sqrt price.
    @return: The price as token1/token0.
    """
    sqrt_price = Decimal(str(sqrt_price_x96)) / Q96
    return sqrt_price**2


def sqrt_price_x96_from_tick(tick: int) -> int:
    """Convert a tick to sqrtPriceX96.

    sqrtPriceX96 = ceil(sqrt(1.0001^tick) * 2^96)
    """
    from .tickmath import TickMath

    return TickMath(tick).to_sqrt_price_x96()


def compute_amount_from_price(
    sqrt_price_x96: int,
    amount_specified: int,
    zero_for_one: bool,
) -> Tuple[int, int]:
    """Compute input/output amounts for an intent-based swap at a fixed price.

    This is the core calculation for AsyncSwap's beforeSwap hook.
    Given a price point (from the Order's tick/sqrtPrice) and the user's
    amountSpecified, it determines how much the user pays and receives.

    The 4 edge cases:

    CASE 1: zeroForOne=True, amountSpecified < 0 (exact input)
        User: "I'm giving X of token0"
        => amount_out = X * price  (they receive token1)
        Hook action: take token0, record debt of token1

    CASE 2: zeroForOne=True, amountSpecified > 0 (exact output / intent)
        User: "I want Y of token1"
        => amount_in = Y / price  (they must pay token0)
        Hook action: calculate token0 required, take it in beforeSwap

    CASE 3: zeroForOne=False, amountSpecified < 0 (exact input)
        User: "I'm giving X of token1"
        => amount_out = X / price  (they receive token0)
        Hook action: take token1, record debt of token0

    CASE 4: zeroForOne=False, amountSpecified > 0 (exact output / intent)
        User: "I want Y of token0"
        => amount_in = Y * price  (they must pay token1)
        Hook action: calculate token1 required, take it in beforeSwap

    @param sqrt_price_x96: The Q64.96 sqrt price at which to execute.
    @param amount_specified: Negative for exact input, positive for exact output.
    @param zero_for_one: True if swapping token0 -> token1.
    @return: (amount_in, amount_out) — both as positive integers.
    """
    if amount_specified == 0:
        return (0, 0)

    sqrt_p = Decimal(str(sqrt_price_x96))
    price = (sqrt_p / Q96) ** 2

    if amount_specified < 0:
        # EXACT INPUT: user specifies how much they are giving
        amount_in = abs(amount_specified)
        if zero_for_one:
            # Selling token0 for token1: amount_out = amount_in * price
            amount_out = int(Decimal(str(amount_in)) * price)
        else:
            # Selling token1 for token0: amount_out = amount_in / price
            if price == 0:
                raise ValueError("price is zero, cannot compute swap")
            amount_out = int(Decimal(str(amount_in)) / price)
        return (amount_in, amount_out)
    else:
        # EXACT OUTPUT (intent): user specifies how much they want
        amount_out = amount_specified
        if zero_for_one:
            # Want token1, must pay token0: amount_in = amount_out / price
            if price == 0:
                raise ValueError("price is zero, cannot compute swap")
            amount_in = int(Decimal(str(amount_out)) / price)
        else:
            # Want token0, must pay token1: amount_in = amount_out * price
            amount_in = int(Decimal(str(amount_out)) * price)
        return (amount_in, amount_out)


def compute_amount_from_tick(
    tick: int,
    amount_specified: int,
    zero_for_one: bool,
) -> Tuple[int, int]:
    """Same as compute_amount_from_price but takes a tick instead of sqrtPriceX96.

    Convenience wrapper: converts tick -> sqrtPriceX96, then delegates.

    @param tick: The tick value from the Order struct.
    @param amount_specified: Negative for exact input, positive for exact output.
    @param zero_for_one: True if swapping token0 -> token1.
    @return: (amount_in, amount_out) — both as positive integers.
    """
    sqrt_price_x96 = sqrt_price_x96_from_tick(tick)
    return compute_amount_from_price(sqrt_price_x96, amount_specified, zero_for_one)


def compute_amount_q96(
    sqrt_price_x96: int,
    amount_specified: int,
    zero_for_one: bool,
) -> Tuple[int, int]:
    """Same as compute_amount_from_price but uses pure integer Q64.96 arithmetic.

    This mirrors the Solidity implementation using FullMath.mulDiv.
    No floating point — only integer division matching EVM behavior.

    Solidity equivalent:
        // token0 -> token1 (multiply by price):
        amount1 = FullMath.mulDiv(
            FullMath.mulDiv(amount0, sqrtPriceX96, Q96),
            sqrtPriceX96, Q96
        );
        // token1 -> token0 (divide by price):
        amount0 = FullMath.mulDiv(
            FullMath.mulDiv(amount1, Q96, sqrtPriceX96),
            Q96, sqrtPriceX96
        );

    @param sqrt_price_x96: The Q64.96 sqrt price.
    @param amount_specified: Negative for exact input, positive for exact output.
    @param zero_for_one: True if swapping token0 -> token1.
    @return: (amount_in, amount_out) — both as positive integers.
    """
    if amount_specified == 0:
        return (0, 0)

    Q = 2**96  # integer version

    def mul_div(a: int, b: int, d: int) -> int:
        """FullMath.mulDiv: (a * b) / d, rounded down."""
        return (a * b) // d

    def token0_to_token1(amount0: int) -> int:
        """amount1 = amount0 * sqrtP / 2^96 * sqrtP / 2^96"""
        return mul_div(mul_div(amount0, sqrt_price_x96, Q), sqrt_price_x96, Q)

    def token1_to_token0(amount1: int) -> int:
        """amount0 = amount1 * 2^96 / sqrtP * 2^96 / sqrtP"""
        return mul_div(mul_div(amount1, Q, sqrt_price_x96), Q, sqrt_price_x96)

    if amount_specified < 0:
        # EXACT INPUT
        amount_in = abs(amount_specified)
        if zero_for_one:
            amount_out = token0_to_token1(amount_in)
        else:
            amount_out = token1_to_token0(amount_in)
        return (amount_in, amount_out)
    else:
        # EXACT OUTPUT
        amount_out = amount_specified
        if zero_for_one:
            # Want token1, pay token0: invert the price direction
            amount_in = token1_to_token0(amount_out)
        else:
            # Want token0, pay token1: invert the price direction
            amount_in = token0_to_token1(amount_out)
        return (amount_in, amount_out)
