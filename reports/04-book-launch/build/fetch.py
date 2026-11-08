#!/usr/bin/env python3
"""Bericht 04 (Buch-Erscheinen und KI-Zitationsverhalten): Rohzeilen aus der Messdatenbank einfrieren.

Zieht per SELECT alle Zeilen, die die Vorregistrierung Q7 (Fassung 1.4 vom 15.10.2026) braucht:
  - ai_citation_results  OpenAI-Websuche + Gemini, ab 2026-08-19 (Basis der CUSUM-Driftprüfung; Grundlinie ab 2026-09-08)
  - pipeline_runs        Laufzeitpunkte (Dedupe-Regel vom 04.09.2026)
  - claude_web_*         Claude auf claude.ai mit Websuche (sekundär, beschreibend)
  - data_gaps            Lückenregister (nur Kennung, Kanal, Datum; Begründungstexte stehen öffentlich im Register)
bis zum Stichtag --cutoff (UTC, inklusive). Ausgabe: <out>/*.json + <out>/freeze.json (Zeitpunkt, Fenster, Zeilenzahlen, Prüfsummen).

Zugriff (keine Kennungen im Code):
  MARIN_D1_CMD   Befehl, der eine SQL-Anweisung als letztes Argument annimmt und die Ergebniszeilen als JSON-Liste ausgibt
oder
  CF_ACCOUNT_ID, D1_DATABASE_ID, CF_API_TOKEN   direkter Aufruf der D1-Schnittstelle.
Es werden ausschließlich SELECT-Anweisungen gesendet.

Aufruf:  python3 build/fetch.py --cutoff 2026-10-07T23:59:59Z --out data/current
"""
import argparse, datetime as dt, hashlib, json, os, shlex, subprocess, urllib.request
from pathlib import Path

R = Path(__file__).resolve().parent.parent
CUSUM_BASE_START = '2026-08-19'      # erster Ankertag des Drei-Tage-Rasters
BASELINE = ('2026-09-08', '2026-10-07')
PANEL = ('openai_search', 'gemini')  # primäres Panel laut Änderung vom 07.10.2026
PAGE = 2000


def d1(sql):
    if not sql.lstrip().upper().startswith('SELECT'):
        raise SystemExit('nur SELECT erlaubt')
    cmd = os.environ.get('MARIN_D1_CMD')
    if cmd:
        out = subprocess.run(shlex.split(os.path.expanduser(cmd)) + [sql], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit('D1-Abfrage fehlgeschlagen: ' + (out.stderr or out.stdout)[-400:])
        return json.loads(out.stdout)
    acc, db, tok = (os.environ.get(k) for k in ('CF_ACCOUNT_ID', 'D1_DATABASE_ID', 'CF_API_TOKEN'))
    if not (acc and db and tok):
        raise SystemExit('Zugang fehlt: MARIN_D1_CMD oder CF_ACCOUNT_ID + D1_DATABASE_ID + CF_API_TOKEN setzen')
    req = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database/{db}/query',
                                 data=json.dumps({'sql': sql}).encode(),
                                 headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}, method='POST')
    return json.load(urllib.request.urlopen(req, timeout=90))['result'][0]['results']


def pull(base, order):
    rows, off = [], 0
    while True:
        b = d1(f'{base} ORDER BY {order} LIMIT {PAGE} OFFSET {off}')
        rows += b
        if len(b) < PAGE:
            return rows
        off += PAGE


def iso_sql(ts):
    """ISO-Zeitstempel -> Vergleichsform der Tabellen ('YYYY-MM-DD HH:MM:SS' bzw. ISO mit T)."""
    return ts.strftime('%Y-%m-%d %H:%M:%S'), ts.strftime('%Y-%m-%dT%H:%M:%S')


def fetch(cutoff, out):
    out.mkdir(parents=True, exist_ok=True)
    sp, st = iso_sql(cutoff)
    panel = ','.join(f"'{x}'" for x in PANEL)
    # asked_at/run_at: 'YYYY-MM-DD HH:MM:SS' oder ISO; datetime() normalisiert beide Formen
    tables = {
        'web_rows': pull(
            "SELECT rowid AS rid, run_id, date(asked_at) AS d, asked_at, llm, question_id, category, score, status "
            f"FROM ai_citation_results WHERE llm IN ({panel}) AND date(asked_at) >= '{CUSUM_BASE_START}' "
            f"AND datetime(asked_at) <= datetime('{sp}')", 'rowid'),
        'runs': pull(
            "SELECT id, run_at, triggered_by FROM pipeline_runs "
            f"WHERE date(run_at) >= '2026-08-18' AND datetime(run_at) <= datetime('{sp}')", 'run_at'),
        'claude_web_rows': pull(
            "SELECT r.id AS rid, s.id AS snapshot_id, date(s.run_ts) AS d, s.run_ts, r.model, r.question_id, r.category, r.score, r.status "
            "FROM claude_web_results r JOIN claude_web_snapshots s ON s.id = r.snapshot_id "
            f"WHERE date(s.run_ts) >= '{CUSUM_BASE_START}' AND datetime(s.run_ts) <= datetime('{sp}')", 'r.id'),
        'questions': pull(
            "SELECT question_id, category, MIN(question) AS question FROM ai_citation_results "
            f"WHERE llm = 'gemini' AND date(asked_at) >= '{BASELINE[0]}' GROUP BY question_id, category", 'question_id'),
        'data_gaps': pull(
            "SELECT id, channel, gap_start, gap_end, recorded_at FROM data_gaps "
            f"WHERE datetime(recorded_at) <= datetime('{sp}')", 'id'),
    }
    sums = {}
    for k, v in tables.items():
        p = out / f'{k}.json'
        p.write_text(json.dumps(v, ensure_ascii=False), encoding='utf-8')
        sums[k] = hashlib.sha256(p.read_bytes()).hexdigest()
    freeze = {
        'frozen_at_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'cutoff_utc': cutoff.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'window': [CUSUM_BASE_START, cutoff.date().isoformat()],
        'baseline_window': list(BASELINE),
        'panel': list(PANEL),
        'rows': {k: len(v) for k, v in tables.items()},
        'sha256': sums,
        'preregistration': 'Q7_book_release v1.4 (2026-10-15)',   # bis 08.11.2026 stand hier fest v1.1
    }
    (out / 'freeze.json').write_text(json.dumps(freeze, indent=1, ensure_ascii=False), encoding='utf-8')
    return freeze


def parse_cutoff(s):
    if s in (None, 'now'):
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    t = dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    return (t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cutoff', default='now', help="UTC-Stichtag inklusive, z. B. 2026-11-07T23:59:59Z (Standard: jetzt)")
    ap.add_argument('--out', default='data/current', help='Zielordner relativ zum Berichtsordner')
    a = ap.parse_args()
    f = fetch(parse_cutoff(a.cutoff), R / a.out)
    print(json.dumps({k: f[k] for k in ('frozen_at_utc', 'cutoff_utc', 'rows')}, ensure_ascii=False))
