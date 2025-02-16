import optparse
from decimal import Decimal

from .tickmath import TickMath
from .liquidity import (
    liquidity_y,
    percentage_slippage_to_tick_bounds,
)
from eth_abi.abi import encode


def main() -> None:
    # print("Hello from uv4!")
    t = TickMath()
    parser = optparse.OptionParser()
    parser.add_option(
        "--get_sqrt_price_at_tick",
        "-s",
        type="string",
        help="Get square root ratin at tick",
    )
    parser.add_option("--price_at_tick", "-p", type=int, help="Get price at tick")
    parser.add_option(
        "--liquidity",
        "-l",
        type="string",
        action="callback",
        callback=get_values,
        help="""Get liquididity y between price range
            <price>,<amount_in>,<min_price>,<max_price>
            price p, amount x, liquidity range [p_a, p_b]
        """,
    )

    parser.add_option(
        "--tick_bounds",
        "-t",
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
        sqrt = "get_sqrt_price_at_tick"
        if d[sqrt]:
            tick = d[sqrt]
            if tick is not None:
                sqrtx96 = t.to_sqrt_price_x96(tick)
                print(f"0x{encode(['uint160'], [sqrtx96]).hex()}")

        price = "price_at_tick"
        if d[price]:
            tick = d[price]
            if tick is not None:
                print(f"{price}({tick}) = {t.to_price(tick)}")

        liquidity = "liquidity"
        if d[liquidity]:
            values = [Decimal(i) for i in d[liquidity]]
            if values is not None:
                print(f"{liquidity}({values}) = {liquidity_y(*values)}")
        ticks = "tick_bounds"
        if d[ticks]:
            values = [Decimal(i) for i in d[ticks]]
            if values is not None:
                print(
                    f"{ticks}({values}) = {percentage_slippage_to_tick_bounds(*values)}"
                )


def get_values(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))
