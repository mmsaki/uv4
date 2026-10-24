"""Compare measured receipts, assert identical events, and write paper evidence/figure.
Usage: uv run --with matplotlib python examples/report_matching_receipts.py BEFORE AFTER PAPER
"""
import hashlib
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

before_path, after_path, paper_path = map(Path, sys.argv[1:])
before, after = [json.loads(p.read_text()) for p in (before_path, after_path)]
assert before['compiler'] == after['compiler'], 'Compiler settings differ'
assert [r['matches'] for r in before['rows']] == [1, 2, 4, 8]
assert [r['matches'] for r in after['rows']] == [1, 2, 4, 8]
rows = []
for old, new in zip(before['rows'], after['rows']):
    assert old['events'] == new['events'], 'Transaction behavior changed'
    rows.append(dict(matches=new['matches'], before_gas=old['receipt_gas'], after_gas=new['receipt_gas'],
                     saving_percent=round(100 * (1 - new['receipt_gas'] / old['receipt_gas']), 2),
                     identical_events=True,
                     events_sha256=hashlib.sha256(json.dumps(new['events'], sort_keys=True).encode()).hexdigest()))
report = dict(method=after['method'], client=after['client'], rows=rows,
              compiler=after['compiler'],
              baseline_source='Pre-optimization local exact-eligibility implementation from evidence/validation.json of the preceding revision; not a deployed version.',
              changes=['Stop ancestor repair at an unchanged summary, except the first refresh branch.',
                       'Retain unreachable node/summary slots; fully overwrite recycled nodes and repair summaries.',
                       'Keep the highest-priority bid when it crosses the minimum ask, skipping a redundant traversal.'])
for target in (Path('docs/priority_protocol/matching_receipts.json'), paper_path/'evidence/matching-receipts.json'):
    target.write_text(json.dumps(report, indent=2) + '\n')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, ax = plt.subplots(figsize=(7.2, 3.5), layout='constrained')
x = list(range(len(rows)))
ax.bar([v-.18 for v in x], [r['before_gas']/1e6 for r in rows], width=.36, label='Before')
ax.bar([v+.18 for v in x], [r['after_gas']/1e6 for r in rows], width=.36, label='After')
ax.set(xticks=x, xticklabels=[str(r['matches']) for r in rows], xlabel='Matches per Router transaction',
       ylabel='Receipt gas (millions)', title='Transaction cost with 128 noncrossing blockers')
ax.legend(frameon=False)
ax.grid(axis='y', alpha=.15)
fig.savefig(paper_path/'figures/matching-receipts.pdf')
fig.savefig(paper_path/'figures/matching-receipts.png', dpi=180)
text = r'''\begin{figure}[htbp]
\centering
\includegraphics[width=0.85\textwidth]{figures/matching-receipts.pdf}
\caption{Actual Router transaction receipts, including intrinsic gas and applied storage refunds.}
\end{figure}
\begin{center}
\begin{tabular}{r r r r}
\hline
Matches & Before & After & Reduction \\
\hline
'''
for r in rows:
    text += f"{r['matches']} & {r['before_gas']:,} & {r['after_gas']:,} & {r['saving_percent']:.1f}\\%" + r' \\' + '\n'
text += r'''\hline
\end{tabular}
\end{center}
These are separate \texttt{Router.matchBook} transactions on a local Anvil, each starting from
an imported Foundry fixture with 128 blockers and 32 crossing pairs, standard ERC-20 tokens,
and no LP positions. All emitted events agree before and after optimization. Receipt gas
includes intrinsic gas and applied refunds; it must not be compared directly with the gross
unlock measurements above. One match is cheaper in total than eight, while eight amortizes
entry costs across more matches. Different owners, token implementations, LP state, partial
fills, and tree shapes can change these costs. The measurements do not establish a global
minimum or a worst-case gas limit.
'''
text += f"\nBoth versions use Solidity {after['compiler']['solc'].split('+')[0]} with {after['compiler']['optimizer']['runs']:,} optimizer runs.\n"
(paper_path/'sections/receipt-results.tex').write_text(text)
print(json.dumps(rows, indent=2))
