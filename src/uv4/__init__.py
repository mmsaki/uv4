import optparse

from uv4.tickmath import (
    Decimal,
    pricex96_at_tick,
    price_at_tick,
    liquidity_y,
    percentage_to_tick_bounds,
)


def main() -> None:
    print("Hello from uv4!")
    parser = optparse.OptionParser()
    parser.add_option(
        "--sqrt_ratio_at_tick", "-s", type=int, help="Get square root ration at tick"
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
        sqrt = "sqrt_ratio_at_tick"
        if d[sqrt]:
            value = d[sqrt]
            if value is not None:
                print(f"{sqrt}({value}) = {pricex96_at_tick(value)}")

        price = "price_at_tick"
        if d[price]:
            value = d[price]
            if value is not None:
                print(f"{price}({value}) = {price_at_tick(value)}")

        liquidity = "liquidity"
        if d[liquidity]:
            values = [Decimal(i) for i in d[liquidity]]
            if values is not None:
                print(f"{liquidity}({values}) = {liquidity_y(*values)}")
        ticks = "tick_bounds"
        if d[ticks]:
            values = [Decimal(i) for i in d[ticks]]
            if values is not None:
                print(f"{ticks}({values}) = {percentage_to_tick_bounds(*values)}")


def get_values(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(","))
