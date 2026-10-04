#!/usr/bin/env python3
"""Freeze the pre-registrations Q0-Q6 (header fields + SHA-256 per file) -> data/preregs.json.
Reads the YAML files from this repository's pre_registrations/ folder."""
import json, hashlib, datetime, yaml
from pathlib import Path
SRC = Path(__file__).resolve().parents[3]/'pre_registrations'
D = Path(__file__).resolve().parent.parent/'data'
out = []
for f in sorted(SRC.glob('Q*.yaml')):
    raw = f.read_bytes(); y = yaml.safe_load(raw)
    s = y.get('sampling') or {}
    out.append({'file': f.name, 'sha256': hashlib.sha256(raw).hexdigest(), 'id': y.get('id'), 'field': y.get('field'),
                'start': str(s.get('start') or y.get('start_date') or '') or None, 'end': str(s.get('end') or y.get('end_date') or '') or None,
                'stopping_rule': (str(y.get('stopping_rule')) if y.get('stopping_rule') else None),
                'status': str(y.get('status')), 'version': str(y.get('version')) if y.get('version') else None})
json.dump({'frozen_at_utc': datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z', 'source': 'marin-research-tools/pre_registrations', 'items': out},
          open(D/'preregs.json', 'w'), ensure_ascii=False, indent=1)
print(len(out), [(x['id'], x['start'], x['end']) for x in out])
