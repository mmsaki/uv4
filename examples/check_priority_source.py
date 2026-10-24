"""Detect drift between this protocol model's reviewed source snapshot and Solidity."""
import hashlib
import json
import sys
from pathlib import Path
manifest = json.loads((Path(__file__).resolve().parents[1] / 'docs/priority_protocol/source_manifest.json').read_text())
root = Path(sys.argv[1])
changed = [name for name, expected in manifest['sha256'].items()
           if not (root / name).exists() or hashlib.sha256((root / name).read_bytes()).hexdigest() != expected]
if changed:
    print('Solidity source drift; review the model before relying on it:', *changed, sep='\n')
    raise SystemExit(1)
print(f"Source snapshot matches ({len(manifest['sha256'])} Solidity files).")
