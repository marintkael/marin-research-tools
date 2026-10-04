#!/usr/bin/env python3
"""Validation Report Q3/2026 (phase 1, instrument validation): freeze the raw rows from the measurement database.
Window T+0 (2026-05-11) to end of Q3 (2026-09-30), date = UTC day of the measurement timestamp.
Output data/*.json + data/freeze.json (time, row counts). analyze.py reads ONLY these files.

Published version: credentials and database identifiers come from the environment, nothing is hard-coded.
  MEASUREMENT_DB_API_TOKEN   API token with read access to the measurement database
  MEASUREMENT_DB_ACCOUNT_ID  account identifier of the database host
  MEASUREMENT_DB_ID          database identifier
The database itself is not public; the frozen extract used in the report is released with the
replication archive (see README)."""
import json, os, datetime, urllib.request
from pathlib import Path
TOKEN = os.environ['MEASUREMENT_DB_API_TOKEN']; ACC = os.environ['MEASUREMENT_DB_ACCOUNT_ID']; DB = os.environ['MEASUREMENT_DB_ID']
R = Path(__file__).resolve().parent.parent; D = R/'data'
START, END = '2026-05-11', '2026-09-30'
def d1(sql):
    req = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{ACC}/d1/database/{DB}/query',
        data=json.dumps({'sql': sql}).encode(), headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}, method='POST')
    return json.load(urllib.request.urlopen(req, timeout=90))['result'][0]['results']
def pull(base, order):
    rows, off = [], 0
    while True:
        b = d1(f"{base} ORDER BY {order} LIMIT 2000 OFFSET {off}"); rows += b
        if len(b) < 2000: return rows
        off += 2000
W = f"BETWEEN '{START}' AND '{END}'"
out = {
  'web_rows': pull(f"SELECT run_id, date(asked_at) d, asked_at, llm, question_id, category, score, status FROM ai_citation_results WHERE date(asked_at) {W}", 'asked_at, llm, question_id'),
  'claude_web_rows': pull(f"SELECT s.id snapshot_id, date(s.run_ts) d, s.run_ts, r.model, r.question_id, r.category, r.score, r.status FROM claude_web_results r JOIN claude_web_snapshots s ON s.id=r.snapshot_id WHERE date(s.run_ts) {W}", 's.run_ts, r.model, r.question_id'),
  'runs': pull(f"SELECT id, run_at, triggered_by, stages_ok, stages_failed FROM pipeline_runs WHERE date(run_at) {W}", 'run_at'),
  'data_gaps': pull("SELECT id, channel, gap_start, gap_end, recorded_at FROM data_gaps", 'id'),
}
for k, v in out.items(): json.dump(v, open(D/f'{k}.json', 'w'), ensure_ascii=False)
json.dump({'frozen_at_utc': datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z', 'window': [START, END],
           'rows': {k: len(v) for k, v in out.items()}}, open(D/'freeze.json', 'w'), indent=1)
print(json.load(open(D/'freeze.json')))
