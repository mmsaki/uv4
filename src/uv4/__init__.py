import optparse
from decimal import Decimal

from .hook import Hook
from .q_number import QNumber, Q6496, Q128128
from .tickmath import TickMath
from .liquidity import (
    liquidity_y_from_prices,
    liquidity_y_from_ticks,
    liquidity_y_from_sqrt_prices,
    percentage_slippage_to_tick_bounds,
)
from .utils import (
    integer_to_binary_string,
)
from eth_abi.abi import encode


__all__ = [
    "Hook",
    "TickMath",
    "QNumber",
    "Q6496",
    "Q128128",
    "FullMath",
    "integer_to_binary_string",
    "liquidity_y_from_prices",
    "liquidity_y_from_ticks",
    "liquidity_y_from_sqrt_prices",
    "percentage_slippage_to_tick_bounds",
]


def main() -> None:
    # print("Hello from uv4!")
    t = TickMath()
    parser = optparse.OptionParser()
    parser.add_option(
        "--get_sqrt_price_x96_at_tick",
        "-s",
        type="string",
        help="Get square root ratin at tick",
    )
    parser.add_option(
        "--get_tick_at_sqrt_price_x96",
        "-t",
        type="string",
        help="Get square root ratin at tick",
    )
    parser.add_option("--price_at_tick", "-p", type=int, help="Get price at tick")
    parser.add_option(
        "--liquidity_from_prices",
        "-l",
        type="string",
        action="callback",
        callback=get_values,
        help="""Get liquididity y between price range
            <price>,<amount0_in>,<min_price>,<max_price>
            price p, amount0 x, liquidity range [p_a, p_b]
        """,
    )
    parser.add_option(
        "--liquidity_from_ticks",
        type="string",
        action="callback",
        callback=get_values,
        help="""Get liquididity y between price range
            <current_tick>,<amount0_in>,<tick_lower>,<tick_upper>
            tick p, amount0 x, liquidity range [p_a, p_b]
        """,
    )

    parser.add_option(
        "--tick_bounds",
        type="string",
        action="callback",
        callback=get_values,
        help="""Get percentage into tick bounds
            -t <price>,<rate>
            <price> e.g 1.01 <rate> e.g 0.01
        """,
    )
    opts, args = parser.parse_args()
    if opts:
        d = opts.__dict__
        sqrt_label = "get_sqrt_price_x96_at_tick"
        if d[sqrt_label]:
            tick = d[sqrt_label]
            if tick is not None:
                t.tick = int(tick)
                sqrtx96 = t.to_sqrt_price_x96()
                print(f"0x{encode(['uint160'], [sqrtx96]).hex()}")

        tick_label = "get_tick_at_sqrt_price_x96"
        if d[tick_label]:
            sqrtx96 = d[tick_label]
            if sqrtx96 is not None:
                sqrt_x96 = int(sqrtx96)
                tick = t.from_sqrt_pricex96(sqrt_x96)
                print(f"0x{encode(['int24'], [tick]).hex()}")

        price = "price_at_tick"
        if d[price]:
            tick = d[price]
            if tick is not None:
                t.tick = int(tick)
                price = t.to_price()
                print(f"0x{encode(['uin160'], [price]).hex()}")

        liquidity = "liquidity_from_prices"
        if d[liquidity]:
            values = [Decimal(i) for i in d[liquidity]]
            if values is not None:
                print(f"{liquidity_y_from_prices(*values)}")

        liquidity = "liquidity_from_ticks"
        if d[liquidity]:
            values = [Decimal(i) for i in d[liquidity]]
            if values is not None:
                print(f"{liquidity_y_from_ticks(*values)}")

        ticks = "tick_bounds"
        if d[ticks]:
            values = [Decimal(i) for i in d[ticks]]
            if values is not None:
                print(
                    f"{ticks}({values}) = {percentage_slippage_to_tick_bounds(*values)}"
                )


def get_values(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))
