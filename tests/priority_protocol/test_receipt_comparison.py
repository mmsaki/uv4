import json
from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[2] / 'examples/compare_matching_receipts.py'


def run_comparison(tmp_path, current_huff_event='new', allow=False):
    paths = []
    for name, gas, event, huff in [('sol', 200, 'new', False), ('before', 180, 'old', True),
                                  ('after', 100, current_huff_event, True)]:
        compiler = {'fixture_compiler': {'optimizer': {'runs': 43690}}} if huff else {'optimizer': {'runs': 43690}}
        data = dict(client='anvil', compiler=compiler, fixture_sha256=name, method='test',
                    rows=[dict(matches=n, receipt_gas=gas, events=[{'data': event}]) for n in [1, 2, 4, 8]])
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(data))
        paths.append(str(path))
    command = [sys.executable, str(SCRIPT), *paths, str(tmp_path / 'out.json')]
    if allow:
        command.append('--allow-prior-event-changes')
    return subprocess.run(command, capture_output=True, text=True)


def test_default_rejects_prior_event_change(tmp_path):
    assert run_comparison(tmp_path).returncode != 0


def test_approved_prior_change_still_checks_current_events(tmp_path):
    assert run_comparison(tmp_path, allow=True).returncode == 0
    assert run_comparison(tmp_path, current_huff_event='different', allow=True).returncode != 0
