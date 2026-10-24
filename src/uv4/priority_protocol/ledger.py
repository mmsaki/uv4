"""PoolManager accounting: assets, ERC-6909 claims, unlock deltas and pool reserves."""
from collections import defaultdict
from dataclasses import dataclass, field
from .arithmetic import require, uint

PM = "pool-manager"
HOOK = "hook"
VAULT = "fee-vault"
ROUTER = "router"
NATIVE = "NATIVE"

@dataclass
class Ledger:
    balances: dict = field(default_factory=lambda: defaultdict(int))
    claims: dict = field(default_factory=lambda: defaultdict(int))
    deltas: dict = field(default_factory=lambda: defaultdict(int))
    reserves: dict = field(default_factory=lambda: defaultdict(int))
    supply: dict = field(default_factory=lambda: defaultdict(int))
    allowances: dict = field(default_factory=lambda: defaultdict(int))
    claim_allowances: dict = field(default_factory=lambda: defaultdict(int))
    blocked: set = field(default_factory=set)

    def mint_test_tokens(self, who, currency, amount):
        uint(amount)
        self.balances[who, currency] += amount
        self.supply[currency] += amount

    def transfer(self, sender, recipient, currency, amount):
        uint(amount)
        require((recipient, currency) not in self.blocked, "recipient rejected transfer")
        require(self.balances[sender, currency] >= amount, "insufficient balance")
        self.balances[sender, currency] -= amount
        self.balances[recipient, currency] += amount

    def approve(self, owner, spender, currency, amount):
        self.allowances[owner, spender, currency] = uint(amount)

    def settle(self, payer, credited, currency, amount, spender=None):
        if spender is not None and payer != spender and currency != NATIVE:
            key = payer, spender, currency
            require(self.allowances[key] >= amount, "insufficient allowance")
            if self.allowances[key] != 2**256 - 1:
                self.allowances[key] -= amount
        self.transfer(payer, PM, currency, amount)
        self.deltas[credited, currency] += amount

    def mint_claim(self, actor, recipient, currency, amount):
        uint(amount)
        self.deltas[actor, currency] -= amount
        self.claims[recipient, currency] += amount

    def burn_claim(self, actor, owner, currency, amount):
        uint(amount)
        if actor != owner:
            key = owner, actor, currency
            require(self.claim_allowances[key] >= amount, "insufficient claim allowance")
            if self.claim_allowances[key] != 2**256 - 1:
                self.claim_allowances[key] -= amount
        require(self.claims[owner, currency] >= amount, "insufficient claims")
        self.claims[owner, currency] -= amount
        self.deltas[actor, currency] += amount

    def transfer_claim(self, sender, recipient, currency, amount):
        uint(amount)
        require(self.claims[sender, currency] >= amount, "insufficient claims")
        self.claims[sender, currency] -= amount
        self.claims[recipient, currency] = uint(self.claims[recipient, currency] + amount)

    def take(self, actor, recipient, currency, amount):
        self.deltas[actor, currency] -= amount
        self.transfer(PM, recipient, currency, amount)

    def payout(self, actor, recipient, currency, amount):
        if currency == NATIVE:
            self.mint_claim(actor, recipient, currency, amount)
        else:
            self.take(actor, recipient, currency, amount)

    def into_pool(self, actor, pool, currency, amount):
        self.deltas[actor, currency] -= amount
        self.reserves[pool, currency] += amount

    def out_of_pool(self, actor, pool, currency, amount):
        require(self.reserves[pool, currency] >= amount, "insufficient pool inventory")
        self.reserves[pool, currency] -= amount
        self.deltas[actor, currency] += amount

    def assert_invariants(self):
        assert all(v >= 0 for v in self.balances.values())
        assert all(v >= 0 for v in self.claims.values())
        assert all(v >= 0 for v in self.reserves.values())
        assert all(v == 0 for v in self.deltas.values()), "unsettled unlock delta"
        for c, supply in self.supply.items():
            assert sum(v for (_, token), v in self.balances.items() if token == c) == supply
            claims = sum(v for (_, token), v in self.claims.items() if token == c)
            pools = sum(v for (_, token), v in self.reserves.items() if token == c)
            assert self.balances[PM, c] == claims + pools, (c, self.balances[PM, c], claims, pools)
