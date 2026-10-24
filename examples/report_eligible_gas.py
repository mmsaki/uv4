"""Parse the real Foundry benchmark log and emit reproducible paper evidence/plots.
Usage: uv run --with matplotlib python examples/report_eligible_gas.py LOG WHITEPAPER
"""
import json
import re
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
log=Path(sys.argv[1]).read_text()
rows=[dict(blockers=int(a),matches=int(b),gross_gas=int(c)) for a,b,c in
      re.findall(r'blockers: (\d+)\s+matches: (\d+)\s+gross_gas: (\d+)',log)]
assert len(rows)==24 and len({(r['blockers'],r['matches']) for r in rows})==24
paper=Path(sys.argv[2]); report={'method':'Real hook/PoolManager unlock; dry-run accessed storage cooled; gross gasleft delta; no refund/intrinsic adjustment; >8 matches compose calls in one test-harness unlock. Standard ERC20 fixtures; no LP positions. These are measurements, not a worst-case gas certificate.','rows':rows}
Path('docs/priority_protocol/eligible_gas.json').write_text(json.dumps(report,indent=2)+'\n')
(paper/'evidence/eligible-gas.json').write_text(json.dumps(report,indent=2)+'\n')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for n in (0,1,16,128):
 rr=sorted((r for r in rows if r['blockers']==n),key=lambda r:r['matches'])
 xs=[r['matches'] for r in rr];ys=[r['gross_gas'] for r in rr]
 axs[0].plot(xs,[g/1e6 for g in ys],marker='o',label=f'{n} blocker' + ('' if n==1 else 's'))
 axs[1].plot(xs,[g/x/1e3 for x,g in zip(xs,ys)],marker='o',label=f'{n} blocker' + ('' if n==1 else 's'))
axs[0].set(xlabel='Matches in composed unlock',ylabel='Gross execution gas (millions)',title='Measured batch cost')
axs[1].set(xlabel='Matches in composed unlock',ylabel='Gas per match (thousands)',title='Measured amortized cost')
axs[0].legend(frameon=False)
for ax in axs:ax.set_xticks([1,8,16,32]);ax.grid(axis='y',alpha=.15)
fig.savefig(paper/'figures/eligible-gas.pdf');fig.savefig(paper/'figures/eligible-gas.png',dpi=180)
text=r'''\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{figures/eligible-gas.pdf}
\caption{Measured gross execution gas; 32 resting sells and buys, zero to 128 ineligible high-fee asks.}
\end{figure}
\begin{center}
\begin{tabular}{r r r r r}
\hline
Matches & 0 blockers & 1 blocker & 16 blockers & 128 blockers \\
\hline
'''
for m in (1,2,4,8,16,32):
 vals=[next(r['gross_gas'] for r in rows if r['matches']==m and r['blockers']==n) for n in (0,1,16,128)]
 text+=str(m)+' & '+' & '.join(f'{v:,}' for v in vals)+r' \\'+'\n'
text+=r'''\hline
\end{tabular}
\end{center}
The benchmark measures a real hook/PoolManager unlock after cooling storage accessed by a
dry run. Values are gross execution gas around the test-harness unlock, without storage
refund subtraction or transaction intrinsic gas. Standard ERC-20 fixtures and no active LP
positions are used. Rows above eight matches compose multiple matching calls inside that
unlock; they do not describe a new Router batch endpoint. The largest tested batch is 32,
not a demonstrated global optimum. The 128-blocker example is not the worst possible
128-branch trie shape. At eight matches its measured cost is GAS_EIGHT gas; at 32 it is
GAS_THIRTY_TWO gas, or about GAS_PER_MATCH gas per match. A gas budget and a certified external-call
envelope are still needed before increasing a production per-call cap.
'''
g8=next(r['gross_gas'] for r in rows if r['matches']==8 and r['blockers']==128)
g32=next(r['gross_gas'] for r in rows if r['matches']==32 and r['blockers']==128)
text=text.replace('GAS_EIGHT',f'{g8:,}').replace('GAS_THIRTY_TWO',f'{g32:,}').replace('GAS_PER_MATCH',f'{round(g32/32):,}')
(paper/'sections/gas-results.tex').write_text(text)
print(json.dumps(report,indent=2))
