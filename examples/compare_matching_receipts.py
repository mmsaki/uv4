"""Compare Solidity, previous Huff, and optimized Huff receipt reports from one benchmark fixture.

Usage: python examples/compare_matching_receipts.py SOLIDITY_JSON HUFF_BEFORE_JSON HUFF_AFTER_JSON OUTPUT_JSON
Checks every emitted event before reporting gas savings. This is not a universal gas bound.
"""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('solidity', type=Path)
parser.add_argument('before', type=Path)
parser.add_argument('after', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--allow-prior-event-changes', action='store_true',
                    help='Allow approved old/new event changes; current Solidity and Huff must still match exactly')
args = parser.parse_args()
sol_path, before_path, after_path, output_path = args.solidity, args.before, args.after, args.output
sol, before, after = [json.loads(p.read_text()) for p in (sol_path, before_path, after_path)]
assert sol['client'] == before['client'] == after['client'], 'Use the same execution client'
assert sol['compiler']['optimizer'] == after['compiler']['fixture_compiler']['optimizer'], 'Use the same fixture optimizer'
assert [r['matches'] for r in sol['rows']] == [1, 2, 4, 8]
assert [r['matches'] for r in before['rows']] == [1, 2, 4, 8]
assert [r['matches'] for r in after['rows']] == [1, 2, 4, 8]
rows = []
for s, b, a in zip(sol['rows'], before['rows'], after['rows']):
    assert s['events'] == a['events'], f"Current Solidity/Huff events differ at {s['matches']} matches"
    prior_events_identical = b['events'] == a['events']
    assert args.allow_prior_event_changes or prior_events_identical, f"Prior events differ at {s['matches']} matches"
    assert a['receipt_gas'] < s['receipt_gas'] and a['receipt_gas'] < b['receipt_gas']
    rows.append(dict(matches=s['matches'], solidity=s['receipt_gas'], huff_before=b['receipt_gas'],
                     huff_after=a['receipt_gas'], all_events_identical=prior_events_identical,
                     current_events_identical=True, prior_events_identical=prior_events_identical,
                     savings_vs_solidity_percent=100 * (1 - a['receipt_gas'] / s['receipt_gas']),
                     savings_vs_previous_huff_percent=100 * (1 - a['receipt_gas'] / b['receipt_gas'])))
report = dict(method=after['method'], client=after['client'], rows=rows,
              compilers=dict(solidity=sol['compiler'], huff=after['compiler']),
              fixture_hashes=dict(solidity=sol['fixture_sha256'], huff_before=before['fixture_sha256'],
                                  huff_after=after['fixture_sha256']))
output_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(rows, indent=2))
