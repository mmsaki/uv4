from uv4.priority_protocol.ledger import Ledger, HOOK, VAULT
from uv4.priority_protocol.model import Protocol


def test_direct_claim_transfer_leaves_unlock_delta_unchanged():
    ledger = Ledger()
    ledger.claims[HOOK, 'USDC'] = 100
    ledger.deltas[HOOK, 'USDC'] = 7
    ledger.transfer_claim(HOOK, VAULT, 'USDC', 30)
    assert ledger.claims[HOOK, 'USDC'] == 70
    assert ledger.claims[VAULT, 'USDC'] == 30
    assert ledger.deltas[HOOK, 'USDC'] == 7


def test_self_credit_does_not_accumulate_past_uint256():
    protocol = Protocol()
    protocol.ledger.claims[HOOK, 'USDC'] = 2**256 - 1
    protocol._claim_batch = {}
    protocol._credit_claim(HOOK, 'USDC', 2**256 - 1)
    protocol._credit_claim(HOOK, 'USDC', 2**256 - 1)
    assert protocol._claim_batch == {}
    assert protocol.ledger.claims[HOOK, 'USDC'] == 2**256 - 1


def test_batch_aggregates_by_recipient_and_currency():
    protocol = Protocol()
    protocol._claim_batch = {}
    protocol._credit_claim('alice', 'USDC', 1)
    protocol._credit_claim('alice', 'ETH', 2)
    protocol._credit_claim('alice', 'USDC', 3)
    assert list(protocol._claim_batch.items()) == [(('alice', 'USDC'), 4), (('alice', 'ETH'), 2)]
