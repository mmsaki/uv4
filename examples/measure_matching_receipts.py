"""Measure real Router.matchBook transaction receipts on an isolated local Anvil.

Export with EXPORT_GAS_FIXTURE=true forge test --match-contract EligibleGasTest -vv.
Usage: python examples/measure_matching_receipts.py STATE_JSON FORGE_LOG RPC_URL OUTPUT_JSON
WARNING: resets the local Anvil instance at RPC_URL; never use a shared node.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

state_path, log_path, url, output_path = sys.argv[1:]
assert urlparse(url).hostname in ('127.0.0.1', 'localhost'), 'Use a dedicated local Anvil'


def request(payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.load(response)


def rpc(method, params=None):
    result = request(dict(jsonrpc='2.0', id=1, method=method, params=params or []))
    assert 'error' not in result, result
    return result['result']


rpc('anvil_reset')
state = json.loads(Path(state_path).read_text())
ops = []
for address, account in state.items():
    for method, value in [('anvil_setCode', account['code']), ('anvil_setBalance', account['balance']),
                          ('anvil_setNonce', account['nonce'])]:
        ops.append(dict(jsonrpc='2.0', id=len(ops), method=method, params=[address, value]))
    for slot, value in account['storage'].items():
        ops.append(dict(jsonrpc='2.0', id=len(ops), method='anvil_setStorageAt', params=[address, slot, value]))
for start in range(0, len(ops), 500):
    results = request(ops[start:start + 500])
    assert all('error' not in r for r in results), results
log = Path(log_path).read_text()
router = re.search(r'benchmark_router: (0x[0-9a-fA-F]+)', log)[1]
data = re.search(r'benchmark_calldata: (0x[0-9a-fA-F]+)', log)[1]
sender = rpc('eth_accounts')[0]
rpc('anvil_setBalance', [sender, hex(10**20)])
match_topic = rpc('web3_sha3', ['0x' + b'AsyncOrdersMatched(bytes32,bytes32,bytes32,uint256,uint256)'.hex()])
rows = []
for count in (1, 2, 4, 8):
    snapshot = rpc('evm_snapshot')
    tx = dict(to=router, data=data[:-64] + f'{count:064x}', gas=hex(15_000_000))
    tx['from'] = sender
    tx_hash = rpc('eth_sendTransaction', [tx])
    receipt = None
    for _ in range(100):
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt is not None:
            break
        time.sleep(.05)
    assert receipt and int(receipt['status'], 16) == 1, receipt
    matches = [e for e in receipt['logs'] if e['topics'][0] == match_topic]
    assert len(matches) == count, (count, matches)
    # Preserve all emitted events for before/after semantic equality checks.
    events = [dict(address=e['address'], topics=e['topics'], data=e['data']) for e in receipt['logs']]
    rows.append(dict(matches=count, receipt_gas=int(receipt['gasUsed'], 16), events=events))
    assert rpc('evm_revert', [snapshot])
artifact_path = Path(state_path).resolve().parents[1] / 'out/AsyncMatching.sol/AsyncMatching.json'
metadata = json.loads(artifact_path.read_text())['metadata']
if isinstance(metadata, str):
    metadata = json.loads(metadata)
compiler = dict(solc=metadata['compiler']['version'], optimizer=metadata['settings']['optimizer'])
report = dict(compiler=compiler, fixture_sha256=__import__('hashlib').sha256(Path(state_path).read_bytes()).hexdigest(), method='Actual Router.matchBook transactions on isolated Anvil, imported Foundry fixture; '
                    '128 blockers, 32 pairs, standard ERC20s, no LPs; gasUsed includes intrinsic gas and '
                    'applied refunds. Each transaction starts from the same state. Not a worst-case bound.',
              client=rpc('web3_clientVersion'), rows=rows)
Path(output_path).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps([{k: v for k, v in r.items() if k != 'events'} for r in rows], indent=2))
