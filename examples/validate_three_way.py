"""Regenerate a shared Python oracle and run it against Solidity and native Huff.

Run from uv4 with `uv run python examples/validate_three_way.py --solidity PATH --huff PATH`.
This validates matching traces, not arbitrary bytecode equivalence or all entry points.
"""
import argparse
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--solidity', type=Path, required=True)
parser.add_argument('--huff', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]

def run(command, cwd):
    subprocess.run(command, cwd=cwd, check=True)

run([sys.executable, '-m', 'pytest', 'tests/priority_protocol', '-q'], root)
for repo, huff in ((args.solidity.resolve(), False), (args.huff.resolve(), True)):
    command = [sys.executable, 'examples/export_eligible_vectors.py', str(repo)]
    if huff:
        command.append('--huff')
    run(command, root)
    command = [sys.executable, 'examples/export_priority_vectors.py', str(repo)]
    if huff:
        command.append('--huff')
    run(command, root)
    path = 'test/current/{EligiblePythonVectors,PriorityPythonVectors,PriorityPythonHashes}.t.sol' if huff else 'test/security/{EligiblePythonVectors,PriorityPythonVectors,PriorityPythonHashes}.t.sol' 
    run(['forge', 'test', '--match-path', path, '--fuzz-seed', '0x20261024', '-vv'], repo)
run([sys.executable, 'examples/export_huff_tick.py', str(args.huff.resolve())], root)
run(['forge', 'test', '--match-contract', 'TickParityTest', '-vv'], args.huff.resolve())
print('Shared Python traces passed on both Solidity and native Huff; tick-key vectors passed on Huff.')
