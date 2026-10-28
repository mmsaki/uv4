from fractions import Fraction
import random
import pytest
from uv4.priority_protocol.arithmetic import Order, crosses, match_amounts, deposit_for as D
from uv4.priority_protocol.model import Protocol
from uv4.priority_protocol.scenarios import setup, fund

@pytest.mark.parametrize('price,a,q,ba,bq',[
    (Fraction(1000),10**18,10**9,2*10**15-1,2_000_000),
    (Fraction(1,10**12),10**36,10**12,2*10**30,3_800_000*10**6),
    (Fraction(10**42),1,10**30,1,10**36),
])
def test_blocker_stays_while_twenty_orders_clear(price,a,q,ba,bq):
    m,p=setup(price)
    for who in ('bad','sell','buy'):fund(m,p,who)
    # Net amounts: each maker deposits the least amount whose net input is the scenario's.
    bad=m.create(p,'bad',False,D(ba),bq,100001)
    for _ in range(20):m.create(p,'sell',False,D(a),q,100000)
    for _ in range(20):m.create(p,'buy',True,D(q),a,100000)
    assert list(m.pools[p].orders)==[bad]
    assert len([e for e in m.events if e[0]=='Matched'])==20
    assert m.pools[p].orders[bad].amount_in==ba
    m.assert_invariants()


def test_exact_crossing_implies_positive_safe_integer_match():
    # Exhaustive small amounts, then 10,000 varied-width pairs. Check inequalities directly,
    # independently of the rounding formulas used by the matcher.
    r=random.Random(20261023)
    vectors=[(a,q,b,A) for a in range(1,13) for q in range(1,13)
             for b in range(1,13) for A in range(1,13)]
    vectors += [tuple(r.randrange(1,2**r.randrange(2,127)) for _ in range(4)) for _ in range(10000)]
    for a,q,b,A in vectors:
        if b*a<q*A:continue
        s=Order('s','s',False,True,a,q,0,1)
        t=Order('b','b',True,False,b,A,0,2)
        for rb in (False,True):
            z=match_amounts(s,t,rb)
            assert 0<z.asset<=a and 0<z.quote<=b
            assert z.quote*a>=z.asset*q
            assert z.asset*b>=z.quote*A


def test_boundary_selection_is_lexicographically_maximal_feasible_pair():
    r=random.Random(20261023)
    for _ in range(200):
        m,p=setup(minimum=0)
        pool=m.pools[p]
        # Selection oracle only, no escrow mutation. All ratios fall below the v4 range: the lowest tick.
        for i in range(30):
            buy=bool(i%2)
            n,d=r.randrange(1,100),10**45
            o=Order(str(i),str(i),buy,not buy,n if buy else d,d if buy else n,r.randrange(4),i+1)
            pool.orders[o.id]=o
        buys=pool.level(True,1);sells=pool.level(False,1)
        feasible=[(b,s) for b in buys for s in sells if b.exact_price>=s.exact_price]
        best=pool.eligible(True,1,min(s.exact_price for s in sells))
        assert (best is None)==(not feasible)
        if feasible:
            ask=pool.eligible(False,1,best.exact_price)
            expected=max(feasible,key=lambda pair:(pair[0].priority_key,pair[1].priority_key))
            assert (best.id,ask.id)==(expected[0].id,expected[1].id)


def test_same_tick_price_precedes_fee_and_age():
    for buy in (False, True):
        m, p = setup()
        for who in ("worse", "better", "taker"):
            fund(m, p, who)
        if buy:
            worse = m.create(p, "worse", True, D(10**9), 10**18, 110000)
            better = m.create(p, "better", True, D(10**9+1), 10**18, 100000)
            assert m.pools[p].orders[worse].price == m.pools[p].orders[better].price
            m.create(p, "taker", False, D(10**18), 10**9, 100000)
        else:
            worse = m.create(p, "worse", False, D(10**18), 10**9+1, 110000)
            better = m.create(p, "better", False, D(10**18), 10**9, 100000)
            assert m.pools[p].orders[worse].price == m.pools[p].orders[better].price
            m.create(p, "taker", True, D(10**9+1), 10**18, 100000)
        assert worse in m.pools[p].orders
        assert better not in m.pools[p].orders
        m.assert_invariants()
