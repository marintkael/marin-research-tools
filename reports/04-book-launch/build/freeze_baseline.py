#!/usr/bin/env python3
"""Bericht 04: Grundlinie einfrieren (Stichtag 2026-10-07 23:59:59 UTC) nach data/baseline_freeze/.

Idempotent und nicht überschreibend:
  1. Gibt es data/baseline_freeze/freeze.json noch nicht, wird der Abzug einmal vollständig erstellt.
  2. Gibt es ihn schon, werden die Tabellen mit demselben Stichtag erneut gelesen. Zeilen, die erst nach dem
     ersten Abzug geschrieben wurden, aber einen Zeitstempel vor dem Stichtag tragen (z. B. die Claude-Grundlinie
     vom 07.10., deren Ergebnis verspätet eintrifft), landen in <tabelle>.supplement.json; die Originaldateien
     bleiben unverändert. Jeder Nachtrag wird in supplements.json protokolliert.
  3. Zeilen, die im ersten Abzug standen und sich in der Datenbank verändert haben (z. B. registrierte Nachbewertung vor
     dem Ereignis, Lückenregister Eintrag 37), werden bis zur Korrekturfrist 08.10.2026 12:00 UTC (vor dem ersten
     Wirkungs-Ankertag) als <tabelle>.corrections.json übernommen; die Originaldateien bleiben unverändert, analyze.py
     legt die Korrekturen darüber. Nach der Frist werden Änderungen nur gemeldet (integrity in supplements.json).
Aufruf: python3 build/freeze_baseline.py
"""
import datetime as dt, json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import fetch

R = Path(__file__).resolve().parent.parent
OUT = R / 'data' / 'baseline_freeze'
CUTOFF = dt.datetime(2026, 10, 7, 23, 59, 59, tzinfo=dt.timezone.utc)
CORRECTION_DEADLINE = dt.datetime(2026, 10, 8, 12, 0, 0, tzinfo=dt.timezone.utc)
KEYS = {'web_rows': ('rid',), 'runs': ('id',), 'claude_web_rows': ('rid',), 'questions': ('question_id',), 'data_gaps': ('id',)}


def key(row, t):
    return tuple(row[k] for k in KEYS[t])


def main():
    if not (OUT / 'freeze.json').exists():
        f = fetch.fetch(CUTOFF, OUT)
        print('Grundlinie eingefroren:', json.dumps(f['rows']))
        report_claude_baseline()
        return
    tmp = Path(tempfile.mkdtemp())
    try:
        fresh = fetch.fetch(CUTOFF, tmp)
        log_p = OUT / 'supplements.json'
        log = json.loads(log_p.read_text(encoding='utf-8')) if log_p.exists() else []
        entry = {'checked_at_utc': fresh['frozen_at_utc'], 'added': {}, 'integrity': {}}
        for t in KEYS:
            orig = json.loads((OUT / f'{t}.json').read_text(encoding='utf-8'))
            sup_p = OUT / f'{t}.supplement.json'
            sup = json.loads(sup_p.read_text(encoding='utf-8')) if sup_p.exists() else []
            cor_p = OUT / f'{t}.corrections.json'
            cor = {key(r, t): r for r in (json.loads(cor_p.read_text(encoding='utf-8')) if cor_p.exists() else [])}
            known = {key(r, t): r for r in orig + sup}
            known.update(cor)
            new = json.loads((tmp / f'{t}.json').read_text(encoding='utf-8'))
            newk = {key(r, t): r for r in new}
            add = [r for k, r in newk.items() if k not in known]
            changed = {k: r for k, r in newk.items() if k in known and known[k] != r}
            missing = sum(1 for k in known if k not in newk)
            if add:
                sup_p.write_text(json.dumps(sup + add, ensure_ascii=False), encoding='utf-8')
                entry['added'][t] = len(add)
            if changed and dt.datetime.now(dt.timezone.utc) < CORRECTION_DEADLINE:
                cor.update(changed)
                cor_p.write_text(json.dumps(list(cor.values()), ensure_ascii=False), encoding='utf-8')
                entry.setdefault('corrected', {})[t] = len(changed)
            elif changed or missing:
                entry['integrity'][t] = {'changed_since_freeze': len(changed), 'missing_since_freeze': missing}
        if entry['added'] or entry['integrity'] or entry.get('corrected'):
            log.append(entry)
            log_p.write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding='utf-8')
        print('Nachtrag:', json.dumps(entry, ensure_ascii=False))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    report_claude_baseline()


def report_claude_baseline():
    rows = json.loads((OUT / 'claude_web_rows.json').read_text(encoding='utf-8'))
    sp = OUT / 'claude_web_rows.supplement.json'
    if sp.exists():
        rows += json.loads(sp.read_text(encoding='utf-8'))
    d = [r for r in rows if r['d'] == '2026-10-07' and r['status'] != 'error']
    print('Claude-Grundlinie 07.10.:', f'{len(d)} Zeilen mit Messwert' if d else 'noch nicht vorhanden – Lauf am 08.10. vormittags wiederholen')


if __name__ == '__main__':
    main()
