"""Reproducible coarse-key scenarios. Run: python -m uv4.priority_protocol.scenarios."""
import argparse
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from uv4.q_number import Q6496
from .arithmetic import U256, Q96, bucket_width, usdc_price, match_amounts, deposit_for
from .identity import address
from .model import Protocol
from .ledger import ROUTER


def setup(price=Fraction(1000), minimum=1_000_000, asset="ASSET", decimals=18):
    model = Protocol()
    model.set_minimum(model.owner, minimum)
    currencies = sorted((asset, "USDC"), key=lambda t: int(address(t), 16))
    ratio = price * Fraction(10**6, 10**decimals)
    if currencies[0] == "USDC":
        ratio = 1 / ratio
    with localcontext() as context:
        context.prec = 110
        sqrt = (Decimal(ratio.numerator) / Decimal(ratio.denominator)).sqrt()
        fixed = Q6496(sqrt)
        sqrt_x96 = int(fixed.from_decimal())
    pid = model.initialize(*currencies, sqrt_price_x96=sqrt_x96)
    return model, pid


def fund(model, pid, who, amount=10**60):
    pool = model.pools[pid]
    for currency in (pool.currency0, pool.currency1):
        model.ledger.mint_test_tokens(who, currency, amount)
        model.ledger.approve(who, ROUTER, currency, U256)
    model.set_executor(pid, who)


def display(value):
    with localcontext() as context:
        context.prec = 50
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def collision_case(name, price, blocker_in, blocker_out, trade_asset, trade_quote, count=20, retries=100):
    model, pid = setup(price)
    model.legacy_matching = True  # Preserve the historical counterexample explicitly.
    for who in ("blocker", "honest", "buyer"):
        fund(model, pid, who)
    # Amounts are the orders' net inputs; each maker deposits the least amount that nets to them.
    blocker = model.create(pid, "blocker", False, deposit_for(blocker_in), blocker_out, 100_001)
    sell_ids = [model.create(pid, "honest", False, deposit_for(trade_asset), trade_quote, 100_000)
                for _ in range(count)]
    buy_ids = [model.create(pid, "buyer", True, deposit_for(trade_quote), trade_asset, 100_000)
               for _ in range(count)]
    pool = model.pools[pid]
    sell, buy, bad = pool.orders[sell_ids[0]], pool.orders[buy_ids[0]], pool.orders[blocker]
    assert sell.price == buy.price == bad.price
    assert bad.exact_price > buy.exact_price >= sell.exact_price
    assert match_amounts(sell, buy, False)
    results = [model.match_book(pid, 8) for _ in range(retries)]
    assert results == [0] * retries
    before = len(model.pools[pid].orders)
    blocked_quote = count * trade_quote
    result = {
        "case": name, "orders_each_side": count, "retries": retries,
        "price_key": str(sell.price), "asset_decimals": 18, "usdc_decimals": 6,
        "honest_price_USDC": display(usdc_price(sell)),
        "blocker_price_USDC": display(usdc_price(bad)),
        "blocker_to_bid_price_ratio": display(bad.exact_price / buy.exact_price),
        "ordinary_bucket_width_USDC": display(bucket_width()),
        "blocked_quote_USDC": display(Fraction(blocked_quote, 10**6)),
        "blocker_input_raw": str(blocker_in), "blocker_output_minimum_raw": str(blocker_out),
        "blocker_input_spot_value_USDC": display(Fraction(blocker_in, 10**18) * price),
        "blocker_bid_USDC": "0.100001", "matches_before_cancel": sum(results),
        "live_orders_before_cancel": before,
    }
    model.cancel(pid, blocker, "blocker")
    calls, matched = 0, 0
    while model.pools[pid].orders:
        n = model.match_book(pid, 8)
        assert n > 0
        matched += n
        calls += 1
    result.update(matches_after_cancel=matched, drain_calls=calls,
                  quote_paid_USDC=display(Fraction(sum(e[5] for e in model.events if e[0] == "Matched"), 10**6)))
    model.assert_invariants()
    return result


def run(count=20, retries=100):
    return {
        "normal": collision_case("normal_bucket", Fraction(1000), 2 * 10**15 - 1, 2_000_000,
                                 10**18, 10**9, count, retries),
        "floor": collision_case("lower_clamp", Fraction(1, 10**12), 2 * 10**30, 3_800_000 * 10**6,
                                10**36, 10**12, count, retries),
        "ceiling": collision_case("upper_clamp_hypothetical", Fraction(10**42), 1, 10**36,
                                  1, 10**30, count, retries),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=20)
    parser.add_argument("--retries", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.orders, args.retries)
    body = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body + "\n")
    print(body)

if __name__ == "__main__":
    main()
