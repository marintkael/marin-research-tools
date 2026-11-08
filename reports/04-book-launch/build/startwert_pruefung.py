#!/usr/bin/env python3
"""Bericht 04: Prüfung des Startwerts (08.11.2026; zusätzliche Prüfung, nicht vorregistriert, ändert keine Zahl der Hauptanalyse).

Rechnet das 95-%-Bootstrap-Intervall der Kopfzahl der Hauptanalyse (Grundlinie 08.09.-07.10. gegen Wirkungsfenster
08.10.-07.11.) mit dem vorregistrierten Startwert 20261007 und mit den Startwerten 20261008 bis 20261007 + N neu.
build/analyze.py bleibt unverändert: dessen Teil bis vor 'Vorher-Nachher' (Laden, Bewerten, Tageswerte, Grundlinie) wird
ausgeführt, danach delta('total', 'baseline', 'effect') je Startwert mit frischem Zufallsgenerator; Grenzen ungerundet gezählt. In der Hauptanalyse ist
dieser Aufruf der erste Zug des Generators; der vorregistrierte Startwert reproduziert daher data/results.json exakt (geprüft).

Aufruf: build/startwert_pruefung.py [--n 200]  ->  data/results_startwerte.json
"""
import argparse, datetime as dt, json, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parent.parent; A = R / 'build' / 'analyze.py'
ap = argparse.ArgumentParser(); ap.add_argument('--n', type=int, default=200); args = ap.parse_args()
src = A.read_text(encoding='utf-8')
MARK = '# ------------------------------------------------------------------ Vorher-Nachher'
if src.count(MARK) != 1: raise SystemExit('Marke in analyze.py nicht eindeutig')
ns = {'__file__': str(A), '__name__': 'analyze_teil'}
_argv = sys.argv; sys.argv = [str(A), '--ohne-varianten']
exec(compile(src.split(MARK)[0], str(A), 'exec'), ns)
sys.argv = _argv
SEED, rnd, N_BOOT = ns['SEED'], ns['rnd'], ns['N_BOOT']

ref = json.loads((R / 'data' / 'results.json').read_text(encoding='utf-8'))['effects']['primary']['total']
seeds = [SEED] + [SEED + k for k in range(1, args.n + 1)]
# delta() rundet seine Ausgaben mit rnd() auf zwei Stellen. Für die Zählung über/unter null werden die Grenzen
# ungerundet gebraucht: rnd wird während des Laufs durch die Identität ersetzt (gleiche Ziehungen, gleiche Perzentile),
# gerundet wird danach mit der Original-Funktion. Prüfung: gerundet == results.json beim vorregistrierten Startwert.
# Punktschätzungen und Referenz: ein Aufruf mit der Original-Rundung (vorregistrierter Startwert) muss results.json
# vollständig reproduzieren. Die Punktschätzungen hängen nicht vom Startwert ab.
ns['rng'] = np.random.default_rng(SEED)
x0 = ns['delta']('total', 'baseline', 'effect')
if any(x0[k] != ref[k] for k in ('detrended', 'ci95_detrended', 'raw', 'ci95_raw')):
    raise SystemExit(f'vorregistrierter Startwert reproduziert results.json nicht: {x0} / {ref}')
_rnd = rnd
ns['rnd'] = lambda x, n=2: None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)
rows = []
for s in seeds:
    ns['rng'] = np.random.default_rng(s)
    x = ns['delta']('total', 'baseline', 'effect')
    u = {k: x[k] for k in ('ci95_detrended', 'ci95_raw')}
    g = {'detrended': x0['detrended'], 'raw': x0['raw'],
         'ci95_detrended': [_rnd(v) for v in u['ci95_detrended']], 'ci95_raw': [_rnd(v) for v in u['ci95_raw']]}
    rows.append({'seed': s, **g, 'ungerundet': {k: [round(w, 6) for w in v] for k, v in u.items()}})
    if s == SEED and (g['ci95_detrended'] != ref['ci95_detrended'] or g['ci95_raw'] != ref['ci95_raw']):
        raise SystemExit(f'ungerundeter Lauf weicht beim vorregistrierten Startwert ab: {g} / {ref}')
ns['rnd'] = _rnd

alt = rows[1:]
def stats(v):
    return {'min': rnd(min(v)), 'max': rnd(max(v)), 'mittel': rnd(float(np.mean(v))), 'sd': round(float(np.std(v, ddof=1)), 3)}
# Kennzahlen und Zählungen auf den ungerundeten Grenzen
rl = [r['ungerundet']['ci95_raw'][0] for r in alt]; rh = [r['ungerundet']['ci95_raw'][1] for r in alt]
dl = [r['ungerundet']['ci95_detrended'][0] for r in alt]; dh = [r['ungerundet']['ci95_detrended'][1] for r in alt]
out = {
    'beschreibung': ('Prüfung des Startwerts (zusätzlich, nicht vorregistriert): 95-%-Bootstrap-Intervall der Kopfzahl der '
                     'Hauptanalyse mit weiteren Startwerten des Zufallsgenerators; Punktschätzungen hängen nicht vom Startwert ab. '
                     'Ändert keine Zahl der Hauptanalyse.'),
    'status': 'pruefung_nicht_vorregistriert',
    'generated_at_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'kennzahl': 'total', 'vergleich': 'primary', 'n_boot': N_BOOT,
    'startwert_vorregistriert': SEED, 'startwerte_weitere': [SEED + 1, SEED + args.n], 'n_weitere': args.n,
    'reproduziert_results_json': True, 'vorregistriert': {k: rows[0][k] for k in ('seed', 'detrended', 'ci95_detrended', 'raw', 'ci95_raw')},
    'zaehlung': 'ungerundete Grenzen (Bootstrap-Perzentile vor dem Runden); min/max/mittel danach auf zwei Stellen gerundet',
    'unbereinigt_untergrenze': {**stats(rl), 'n_ueber_null': sum(1 for v in rl if v > 0), 'n_unter_null': sum(1 for v in rl if v < 0),
                                'n_ueber_null_gerundet': sum(1 for r in alt if r['ci95_raw'][0] > 0)},
    'unbereinigt_obergrenze': stats(rh),
    'bereinigt_untergrenze': {**stats(dl), 'n_ueber_null': sum(1 for v in dl if v > 0)},
    'bereinigt_obergrenze': {**stats(dh), 'n_unter_null': sum(1 for v in dh if v < 0)},
    'laeufe': rows,
}
(R / 'data' / 'results_startwerte.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('Startwerte:', args.n, '+ vorregistriert', SEED, '(reproduziert)')
for k in ('unbereinigt_untergrenze', 'unbereinigt_obergrenze', 'bereinigt_untergrenze', 'bereinigt_obergrenze'):
    print(' ', k, out[k])
