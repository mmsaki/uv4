"""Compare Solidity, previous Huff, and optimized Huff receipt reports from one benchmark fixture.

Usage: python examples/compare_matching_receipts.py SOLIDITY_JSON HUFF_BEFORE_JSON HUFF_AFTER_JSON OUTPUT_JSON
Checks every emitted event before reporting gas savings. This is not a universal gas bound.
"""
import json
import sys
from pathlib import Path

sol_path, before_path, after_path, output_path = map(Path, sys.argv[1:])
sol, before, after = [json.loads(p.read_text()) for p in (sol_path, before_path, after_path)]
assert sol['client'] == before['client'] == after['client'], 'Use the same execution client'
assert sol['compiler']['optimizer'] == after['compiler']['fixture_compiler']['optimizer'], 'Use the same fixture optimizer'
assert [r['matches'] for r in sol['rows']] == [1, 2, 4, 8]
assert [r['matches'] for r in before['rows']] == [1, 2, 4, 8]
assert [r['matches'] for r in after['rows']] == [1, 2, 4, 8]
rows = []
for s, b, a in zip(sol['rows'], before['rows'], after['rows']):
    assert s['events'] == b['events'] == a['events'], f"Observable events differ at {s['matches']} matches"
    assert a['receipt_gas'] < s['receipt_gas'] and a['receipt_gas'] < b['receipt_gas']
    rows.append(dict(matches=s['matches'], solidity=s['receipt_gas'], huff_before=b['receipt_gas'],
                     huff_after=a['receipt_gas'], all_events_identical=True,
                     savings_vs_solidity_percent=100 * (1 - a['receipt_gas'] / s['receipt_gas']),
                     savings_vs_previous_huff_percent=100 * (1 - a['receipt_gas'] / b['receipt_gas'])))
report = dict(method=after['method'], client=after['client'], rows=rows,
              compilers=dict(solidity=sol['compiler'], huff=after['compiler']),
              fixture_hashes=dict(solidity=sol['fixture_sha256'], huff_before=before['fixture_sha256'],
                                  huff_after=after['fixture_sha256']))
output_path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(rows, indent=2))
