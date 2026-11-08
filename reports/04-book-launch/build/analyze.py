#!/usr/bin/env python3
"""Bericht 04: Auswertung nach Vorregistrierung Q7 (Fassung 1.4 vom 15.10.2026: Änderungen 1–3 vom 07.10.2026 vor dem
Ereignis, Änderung 4 vom 15.10.2026 im laufenden Wirkungsfenster; datierte Vermerke vom 08.11.2026).

Läufe (08.11.2026, Register 66, 71, 83):
  analyze.py                        Hauptanalyse (vorregistriert) -> data/results.json. Rechnet anschließend jede Variante
                                    unten als eigenen Lauf (gleicher Startwert) und trägt kompakte Blöcke in results.json ein
                                    (sensitivitaeten, extension_0811); --ohne-varianten überspringt das.
  --regeln nachtrag                 Sensitivität Bewertungsregeln vom 02.11. (Register 71) -> data/results_regeln_nachtrag.json
  --leer luecke|fehler              Sensitivität leere Antworten (Register 66): als Lücke (Frage fehlt an diesem Tag) bzw. als
                                    Fehlmessung (Anbieter-Tag unvollständig) -> data/results_leere_antworten.json (je Modus ein Teil)
  --ohne-aenderung4                 Sensitivität ohne Änderung 4 (Register 50) -> data/results_ohne_aenderung4.json
  --erweiterung 0811                NICHT vorregistrierte Erweiterung des Wirkungsfensters bis Ankertag 08.11.2026 (Register 83),
                                    Abzug data/extension_freeze_0811 -> data/results_erweiterung_0811.json

Liest NUR eingefrorene Dateien:
  data/baseline_freeze/   Grundlinie, Stichtag 2026-10-07 23:59:59 UTC (inkl. *.supplement.json), wird nie überschrieben
  data/effect_freeze/     Abzug zum Ende des Wirkungsfensters (Stichtag 07.11.2026), sonst data/current/
  data/observation_freeze/ Abzug zum Ende der Beobachtung (Stichtag 06.01.2027), sonst data/current/
  data/current/           laufender Abzug (fetch.py --out data/current)
Zeilen bis zum Stichtag kommen ausschließlich aus der Grundlinie, Zeilen danach aus dem Abzug des jeweiligen Fensters.
Ausgabe: data/results.json = einzige Zahlenquelle für Figuren und Text.

Festlegungen (im Code fixiert am 07.10.2026, vor dem Ereignis):
  Panel (primär)     OpenAI-Websuche + Gemini (Google-Websuche). Claude nur beschreibend.
  Ankertage          Drei-Tage-Raster ab 2026-08-19 (UTC). Messungen an anderen Tagen bleiben unberücksichtigt.
  Dedupe             je Tag, Anbieter, Frage eine Zeile: Fehlerzeile verliert immer, sonst Zeile am nächsten zum
                     planmäßigen Laufzeitpunkt (frühester cron-Lauf des Tages), Gleichstand -> frühere Zeile.
  Tageswert          Punktsumme / (n x 3) x 100 über die Fragen eines Kanals; nur vollständige Anbieter-Tage (16 von 16).
  Kanäle             Direkt = D1-D3 · Saga-Wissen = L1, L2 · Empfehlung = G1, G2, C1, C2, GR1-GR6 (wie Messdienst:
                     direct_pure / longtail / discovery_pure). Forschung (R1) nur in der Kopfzahl. GR1-GR6 allein sekundär.
  Kopfzahl je Tag    einfacher Mittelwert OpenAI + Gemini (nur Tage mit beiden; Tage mit einem Anbieter = Basiswechsel).
  Vorher-Nachher     je Anbieter: mittleres Residuum im Wirkungsfenster minus mittleres Residuum der Grundlinie, beide gegen
                     dieselbe lineare Drift (OLS über alle Ankertage ab 19.08. bis Grundlinienende = CUSUM-Basis, in das
                     Fenster fortgeschrieben); Kopfzahl/Kanal = Mittel der
                     Anbieter-Differenzen. 95-%-Intervall: Bootstrap über Ankertage (je Anbieter und Fenster getrennt,
                     10.000 Ziehungen, Startwert 20261007). Unbereinigte Differenz zusätzlich.
  Driftprüfung       CUSUM (k = 0,5 SD, h = 5 SD) über die Grundlinien-Ankertage gegen die Referenz 19.08.-06.09.
  Erste Abweichung   je Kanal: einseitiger CUSUM (k = 0,5, h = 5) der driftbereinigten, auf die Grundlinien-SD
                     standardisierten Residuen ab dem ersten Ankertag des Wirkungsfensters; sekundär: erster Ankertag
                     über der 95-%-Prognosegrenze der Grundlinien-Drift.
"""
import argparse, collections as C, datetime as dt, json, math, subprocess, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parent.parent; D = R / 'data'
CUTOFF = dt.datetime(2026, 10, 7, 23, 59, 59)
ANCHOR0 = dt.date(2026, 8, 19)
EVENT = dt.date(2026, 10, 8); PREORDER = dt.date(2026, 9, 30); CLAUDE_NEW = dt.date(2026, 10, 7)
WIN = {'cusum_ref': ('2026-08-19', '2026-09-07'), 'baseline': ('2026-09-08', '2026-10-07'),
       'sensitivity': ('2026-09-08', '2026-09-29'), 'effect': ('2026-10-08', '2026-11-07'),
       'delayed': ('2026-11-08', '2027-01-06')}
PROV = {'openai_search': 'OpenAI', 'gemini': 'Gemini'}
CH = {'direct': ['D1', 'D2', 'D3'], 'longtail': ['L1', 'L2'],
      'discovery': ['G1', 'G2', 'C1', 'C2', 'GR1', 'GR2', 'GR3', 'GR4', 'GR5', 'GR6'],
      'recommend_gr': ['GR1', 'GR2', 'GR3', 'GR4', 'GR5', 'GR6'], 'research': ['R1']}
ALLQ = CH['direct'] + CH['longtail'] + CH['discovery'] + CH['research']
SCORE_METRICS = ['total', 'direct', 'longtail', 'discovery', 'recommend_gr']
# Robustheits-Kennzahl (Änderung 2 vom 07.10.2026): Trefferquote = Anteil Antworten mit Bewertung > 0, je Kanal
HIT_METRICS = ['hit_' + m for m in SCORE_METRICS]
METRICS = SCORE_METRICS + HIT_METRICS
N_BOOT, SEED, K_SD, H_SD = 10000, 20261007, 0.5, 5.0


def ts(x):
    t = dt.datetime.fromisoformat(str(x).replace('Z', '+00:00').replace(' ', 'T'))
    return t.astimezone(dt.timezone.utc).replace(tzinfo=None) if t.tzinfo else t


def day(s): return dt.date.fromisoformat(s)


def rnd(x, n=2): return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


# ------------------------------------------------------------------ Laden
KEYF = {'web_rows': 'rid', 'claude_web_rows': 'rid', 'runs': 'id', 'data_gaps': 'id', 'questions': 'question_id'}
corrections_applied = {}


def load_dir(p, t):
    """Abzug + Nachtrag (*.supplement.json) + Korrekturen vor der Frist (*.corrections.json, ersetzen Zeilen gleicher Kennung)."""
    if not (p / f'{t}.json').exists(): return []
    rows = json.loads((p / f'{t}.json').read_text(encoding='utf-8'))
    s = p / f'{t}.supplement.json'
    rows = rows + (json.loads(s.read_text(encoding='utf-8')) if s.exists() else [])
    c = p / f'{t}.corrections.json'
    if c.exists():
        cor = {r[KEYF[t]]: r for r in json.loads(c.read_text(encoding='utf-8'))}
        rows = [cor.get(r[KEYF[t]], r) for r in rows]
        corrections_applied[f'{p.name}/{t}'] = len(cor)
    return rows


ap = argparse.ArgumentParser()
ap.add_argument('--source', default='auto', choices=['auto', 'none'], help='none = nur Grundlinie auswerten')
# 02.11.2026 Methoden-Nachtrag Bewertungsregeln: vorregistriert = Hauptanalyse (alte Regeln beidseitig), nachtrag = Sensitivität
ap.add_argument('--regeln', default='vorregistriert', choices=['vorregistriert', 'nachtrag'])
# 08.11.2026 (Register 66): leere Antworten. vorregistriert = wie gemessen (0 Punkte); luecke = die Frage fehlt
# an diesem Tag (Tageswert über die übrigen Fragen); fehler = Fehlmessung (der Anbieter-Tag ist nicht vollständig)
ap.add_argument('--leer', default='vorregistriert', choices=['vorregistriert', 'luecke', 'fehler'])
# 08.11.2026: Sensitivität ohne Änderung 4 (Register 50) – die beiden am 15.10. rückwirkend geänderten Antworten auf 0
ap.add_argument('--ohne-aenderung4', action='store_true')
# 08.11.2026 (Register 83): NICHT vorregistrierte Erweiterung des Wirkungsfensters bis einschließlich Ankertag 08.11.2026
ap.add_argument('--erweiterung', default=None, choices=['0811'])
ap.add_argument('--ohne-varianten', action='store_true', help='Hauptlauf: Varianten nicht neu rechnen (Blöcke bleiben leer)')
args = ap.parse_args()
VARIANTS = [v for v in (args.regeln == 'nachtrag' and 'regeln_nachtrag', args.leer != 'vorregistriert' and f'leere_antworten_{args.leer}',
                        args.ohne_aenderung4 and 'ohne_aenderung4', args.erweiterung and f'erweiterung_{args.erweiterung}') if v]
if len(VARIANTS) > 1: raise SystemExit('je Lauf höchstens eine Variante: ' + ', '.join(VARIANTS))
VARIANT = VARIANTS[0] if VARIANTS else 'haupt'
BF = D / 'baseline_freeze'
if not (BF / 'freeze.json').exists(): raise SystemExit('Grundlinie fehlt: build/freeze_baseline.py zuerst')
EFFECT_END = dt.datetime(2026, 11, 7, 23, 59, 59)
EXT_DIR = 'extension_freeze_0811'
if args.erweiterung == '0811':   # Wirkungsfenster bis einschließlich Ankertag 08.11.; Beobachtung ab 09.11.
    WIN['effect'] = ('2026-10-08', '2026-11-08'); WIN['delayed'] = ('2026-11-09', '2027-01-06')
    EFFECT_END = dt.datetime(2026, 11, 8, 23, 59, 59)


def has(n): return (D / n / 'freeze.json').exists()


# Quellen je Zeitabschnitt: (bis Stichtag] Grundlinie · (Stichtag, 07.11.] effect_freeze, sonst current · danach observation_freeze, sonst current
# Erweiterung 0811: (Stichtag, 08.11. 23:59:59] ausschließlich aus dem eigenen Abzug data/extension_freeze_0811
SEG = []
if args.erweiterung:
    if not has(EXT_DIR): raise SystemExit(f'Abzug fehlt: build/fetch.py --cutoff 2026-11-08T23:59:59Z --out data/{EXT_DIR}')
    SEG.append((CUTOFF, EFFECT_END, D / EXT_DIR))
elif args.source != 'none':
    e_src = 'effect_freeze' if has('effect_freeze') else ('current' if has('current') else None)
    o_src = 'observation_freeze' if has('observation_freeze') else ('current' if has('current') else None)
    if e_src: SEG.append((CUTOFF, EFFECT_END, D / e_src))
    if o_src: SEG.append((EFFECT_END, dt.datetime(2100, 1, 1), D / o_src))
post_dirs = sorted({x[2] for x in SEG}, key=str)
latest = max(post_dirs, key=lambda p_: json.loads((p_ / 'freeze.json').read_text(encoding='utf-8'))['cutoff_utc']) if post_dirs else None
TS = {'web_rows': 'asked_at', 'claude_web_rows': 'run_ts', 'runs': 'run_at'}
data, integrity = {}, {}
for t in ('web_rows', 'claude_web_rows', 'runs', 'data_gaps', 'questions'):
    base = load_dir(BF, t)
    if t in TS:
        base = [r for r in base if ts(r[TS[t]]) <= CUTOFF]
        post = [r for lo, hi, pd_ in SEG for r in load_dir(pd_, t) if lo < ts(r[TS[t]]) <= hi]
        if latest:   # Abgleich: hat sich der Grundlinienbestand in der Datenbank seit dem Einfrieren verändert?
            kf = 'rid' if t != 'runs' else 'id'
            later = {r[kf]: r for r in load_dir(latest, t) if ts(r[TS[t]]) <= CUTOFF}
            bk = {r[kf]: r for r in base}
            integrity[t] = {'checked_against': latest.name, 'baseline_rows': len(bk), 'missing_in_later_pull': sum(1 for k in bk if k not in later),
                            'changed_in_later_pull': sum(1 for k in bk if k in later and later[k] != bk[k]),
                            'new_in_later_pull': sum(1 for k in later if k not in bk)}
        data[t] = base + post
    else:   # Register und Fragen: jüngster Stand
        data[t] = load_dir(latest, t) if latest and load_dir(latest, t) else base
# 02.11.2026: Bewertungsregeln beidseitig gleich halten. Die Grundlinie ist mit den vorregistrierten Regeln eingefroren,
# die Datenbank trägt im Wirkungsfenster seit 02.11. die neuen Regeln (10 Zeilen). Hauptanalyse: Fensterzeilen auf den
# vorregistrierten Wert zurück; Sensitivität: Grundlinienzeilen auf den neuen Wert. Quelle data/scorer_nachtrag_2026-11-02.json.
scorer_rules = {'regeln': args.regeln, 'overrides': 0}
db_orig = {}   # (Tabelle, rid) -> Wert der Messdatenbank vor der Rückstellung
_sn = D / 'scorer_nachtrag_2026-11-02.json'
if _sn.exists():
    _n = json.loads(_sn.read_text(encoding='utf-8'))
    # 08.11.2026: Umfang des Nachtrags für den Text (window: am Volltext; baseline: am Auszug von 500 Zeichen)
    scorer_rules['nachtrag_eintraege'] = {'window': len(_n['window']), 'baseline_auszug_500_zeichen': len(_n['baseline']),
                                          'window_je_fenster': dict(C.Counter(r.get('fenster', 'wirkung') for r in _n['window']))}
    _ov = {}
    if args.regeln == 'vorregistriert':
        for r in _n['window']: _ov[(r['table'], r['rid'])] = (r['score_vorregistriert'], r['status_vorregistriert'])
    else:
        for r in _n['baseline']: _ov[(r['table'], r['rid'])] = (r['score_nachtrag'], r['status_nachtrag'])
    for t in ('web_rows', 'claude_web_rows'):
        for r in data[t]:
            o = _ov.get((t, r['rid']))
            if o and (r['score'], r['status']) != o:
                db_orig[(t, r['rid'])] = (r['score'], r['status'])
                r['score'], r['status'] = o; scorer_rules['overrides'] += 1
    # 08.11.2026 abends: Eintrag 43 (Pauline Kael, 07.10.2026) sagt, echte Angaben über den Autor in derselben Antwort werden
    # wie üblich bewertet. Der Bewerter in der vorregistrierten Fassung (vor dem 02.11.2026) setzt das enger um: Eine Antwort,
    # die den Autor zutreffend beschreibt und sich am Ende gegen Pauline Kael abgrenzt, gilt als Kollision mit 0 Punkten
    # (Fehler 1 in Eintrag 71). Die Hauptanalyse folgt dem Bewerter; hier werden die betroffenen Antworten ausgewiesen.
    _by_rid = {(t, r['rid']): r for t in ('web_rows', 'claude_web_rows') for r in data[t]}
    _e43 = []
    for r in _n['window']:
        if r['status_vorregistriert'] == 'collision' and r['status_nachtrag'] != 'collision':
            x = _by_rid.get((r['table'], r['rid']))
            _e43.append({'table': r['table'], 'rid': r['rid'], 'd': r.get('d') or (x and x['d']),
                         'modell': r.get('anbieter') or (x and (x.get('model') or x.get('llm'))),
                         'question_id': r.get('question_id') or (x and x['question_id']), 'fenster': r.get('fenster', 'wirkung'),
                         'score_bewerter_vorregistriert': r['score_vorregistriert'], 'status_bewerter_vorregistriert': r['status_vorregistriert'],
                         'score_wortlaut_eintrag43': r['score_nachtrag'], 'status_wortlaut_eintrag43': r['status_nachtrag'],
                         'im_datenstand': x is not None})
    if any(not e['d'] or not e['modell'] for e in _e43 if e['im_datenstand']):
        raise SystemExit('Eintrag 43: betroffene Zeile ohne Tag oder Modell')
    scorer_rules['eintrag43_enger_umgesetzt'] = {
        'hinweis': ('Eintrag 43 (07.10.2026): echte Angaben über den Autor in derselben Antwort werden wie üblich bewertet. Der Bewerter in '
                    'der vorregistrierten Fassung (vor dem 02.11.2026) wertet Antworten, die den Autor zutreffend beschreiben und sich '
                    'gegen Pauline Kael abgrenzen, als Kollision mit 0 Punkten (Fehler 1 in Eintrag 71). Die Hauptanalyse folgt dem '
                    'Bewerter. Wert nach dem Wortlaut = Wert nach den Regeln vom 02.11.2026 (Fehler 1 behoben).'),
        'zeilen': _e43, 'je_fenster': dict(C.Counter(e['fenster'] for e in _e43)),
        'je_tabelle': dict(C.Counter(e['table'] for e in _e43))}

# 08.11.2026: Datenänderungen der Varianten (nach den Bewertungsregeln, vor dem Dedupe). Hauptanalyse: keine.
variant_rows = []
if args.leer != 'vorregistriert':
    # Leere Antworten (Antworttext leer, Bewerterstatus not_found): Kennungen aus data/leere_antworten.json (Abfrage der
    # Messdatenbank, Kriterium dort). Abgleich: jede gelistete Zeile trägt not_found, keine andere Panel-Zeile trägt not_found.
    _la = json.loads((D / 'leere_antworten.json').read_text(encoding='utf-8'))
    _ids = {x['rid'] for x in _la['rows']}
    _hit = [r for r in data['web_rows'] if r['rid'] in _ids]
    _bad = [r['rid'] for r in _hit if r['status'] != 'not_found'] + [r['rid'] for r in data['web_rows'] if r['status'] == 'not_found' and r['rid'] not in _ids]
    if _bad: raise SystemExit(f'leere Antworten: Abgleich mit dem Bewerterstatus fehlgeschlagen ({_bad[:5]})')
    for r in _hit:
        variant_rows.append({'table': 'web_rows', 'rid': r['rid'], 'd': r['d'], 'llm': r['llm'], 'question_id': r['question_id'], 'score': r['score']})
        if args.leer == 'fehler': r['status'] = 'error'
        else: r['leer'] = True
if args.ohne_aenderung4:
    # Änderung 4 (15.10.2026, Register 50) änderte rückwirkend genau zwei Antworten, beide am 12.10., Frage L1, je 0 -> 2 Punkte
    A4 = {('web_rows', 27384): 'gemini', ('claude_web_rows', 4542): 'claude-opus-5-5'}
    for (t, rid), who in A4.items():
        r = next((x for x in data[t] if x['rid'] == rid), None)
        if r is None or r['d'] != '2026-10-12' or r['question_id'] != 'L1' or r['score'] != 2:
            raise SystemExit(f'Änderung 4: Zeile {t} {rid} nicht wie erwartet')
        variant_rows.append({'table': t, 'rid': rid, 'd': r['d'], 'who': who, 'question_id': 'L1', 'score_mit_aenderung4': 2, 'score_ohne': 0})
        r['score'], r['status'] = 0, 'ohne_aenderung4'
freeze_b =json.loads((BF / 'freeze.json').read_text(encoding='utf-8'))
freeze_post = {p_.name: json.loads((p_ / 'freeze.json').read_text(encoding='utf-8')) for p_ in post_dirs}
data_until = max([CUTOFF] + [ts(f['cutoff_utc']) for f in freeze_post.values()])
if SEG and SEG[0][2].name == 'effect_freeze': data_until = max(data_until, EFFECT_END)

anchors = []; a = ANCHOR0
while a <= day(WIN['delayed'][1]): anchors.append(a); a += dt.timedelta(days=3)
ANCH = {x.isoformat() for x in anchors}


def in_win(d, w):
    d = d if isinstance(d, str) else d.isoformat(); return WIN[w][0] <= d <= WIN[w][1]


# ------------------------------------------------------------------ Dedupe OpenAI/Gemini
RUN = {r['id']: r for r in data['runs']}
# 07.10.2026 (Entscheidung des Autors, vor dem Ereignis, data_gaps method_openai_nachholung): OpenAI-Nachmessung nach Kontingent-Ausfall
# schreibt in den Lauf des Ankertags zurueck, die Antworten tragen aber den echten Zeitpunkt (Folgetag). Solche Zeilen
# zaehlen fuer den Ankertag ihres Laufs, wenn sie hoechstens 36 h nach dem Laufstart liegen (gleiche Frist wie Claude).
n_nachholung = 0
for r in data['web_rows']:
    run = RUN.get(r['run_id'])
    if not run or r['d'] in ANCH: continue
    rd = str(run['run_at'])[:10]
    if rd in ANCH and r['llm'] == 'openai_search' and 0 <= (ts(r['asked_at']) - ts(run['run_at'])).total_seconds() <= 36 * 3600:
        r['d'] = rd; r['nachholung'] = True; n_nachholung += 1
day_runs = C.defaultdict(set); first_row = {}
for r in data['web_rows']:
    day_runs[(r['d'], r['llm'])].add(r['run_id'])
    t = ts(r['asked_at'])
    if r['run_id'] not in first_row or t < first_row[r['run_id']]: first_row[r['run_id']] = t
plan_src = C.Counter()


def planned(d, llm):
    rs = day_runs[(d, llm)]; known = [RUN[x] for x in rs if x in RUN]
    cron = [ts(x['run_at']) for x in known if x.get('triggered_by') == 'cron']
    if cron: plan_src['cron'] += 1; return min(cron)
    if known: plan_src['run'] += 1; return min(ts(x['run_at']) for x in known)
    plan_src['first_row'] += 1; return min(first_row[x] for x in rs)


cells, dropped, pc = {}, 0, {}
for r in data['web_rows']:
    if r['d'] not in ANCH: continue
    k0 = (r['d'], r['llm'])
    if k0 not in pc: pc[k0] = planned(*k0)
    t = ts(r['asked_at']); err = r['status'] == 'error'
    cand = (err, abs((t - pc[k0]).total_seconds()), t, r['rid'])
    key = (r['d'], r['llm'], r['question_id'])
    if key in cells: dropped += 1
    if key not in cells or cand < cells[key][0]: cells[key] = (cand, r)

prov_day = C.defaultdict(dict)   # prov -> d -> info
for (d, llm, q), (cand, r) in cells.items():
    x = prov_day[PROV[llm]].setdefault(d, {'valid': {}, 'error': 0, 'leer': set()})
    if r['status'] == 'error': x['error'] += 1
    elif r.get('leer'): x['leer'].add(q)    # nur --leer luecke: Frage fehlt an diesem Tag
    else: x['valid'][q] = r['score']
SEL = {r['rid'] for _, r in cells.values()}   # nach dem Dedupe gewertete Panel-Zeilen (Ankertage)

if _sn.exists():
    # 08.11.2026 abends: Aufteilung der 41 am Auszug nachbewerteten Grundlinienzeilen (Sensitivität Eintrag 71) danach, ob sie
    # in eine Kennzahl eingehen: OpenAI/Gemini nur auf Ankertagen (gewertete Zeile nach dem Dedupe); Claude nur beschreibend.
    _bl = _n['baseline']; _w = [e for e in _bl if e['table'] == 'web_rows']; _c = [e for e in _bl if e['table'] == 'claude_web_rows']
    _wa = [e for e in _w if e['d'] in ANCH and e['rid'] in SEL]
    scorer_rules['nachtrag_eintraege']['baseline_auszug_aufteilung'] = {
        'openai_gemini': len(_w), 'openai_gemini_ankertage_gewertet': len(_wa),
        'openai_gemini_ankertage_je_anbieter': dict(C.Counter(PROV[e['model']] for e in _wa)),
        'openai_gemini_nicht_gewertet': len(_w) - len(_wa),
        'openai_gemini_nicht_gewertet_zwischentage': sum(1 for e in _w if e['d'] not in ANCH),
        'claude_aeltere_reihe': sum(1 for e in _c if e['d'] < CLAUDE_NEW.isoformat()),
        'claude_grundlinie_0710': sum(1 for e in _c if e['d'] == CLAUDE_NEW.isoformat()),
        'hinweis': ('Zwischentage gehen nicht ein (Eintrag 26); die ältere Claude-Reihe ist nur Kontext, die Claude-Grundlinienmessung '
                    'vom 07.10.2026 geht nur in die beschreibenden Claude-Werte ein.')}
    if len(_c) != scorer_rules['nachtrag_eintraege']['baseline_auszug_aufteilung']['claude_aeltere_reihe'] + scorer_rules['nachtrag_eintraege']['baseline_auszug_aufteilung']['claude_grundlinie_0710']:
        raise SystemExit('Aufteilung der Grundlinienzeilen unvollständig')


def pct(scores): return 100.0 * sum(scores) / (len(scores) * 3) if scores else None


def hit(scores): return 100.0 * sum(1 for x in scores if x > 0) / len(scores) if scores else None


def day_values(x):
    v = x['valid']; lz = x['leer']
    complete = all(q in v or q in lz for q in ALLQ)   # ohne --leer luecke ist lz leer: alle 16 Fragen gültig
    out = {'n_valid': len(v), 'n_error': x['error'], 'complete': complete}
    if lz: out['n_leer_als_luecke'] = len(lz)
    if complete:   # Kanal ohne gültige Frage (nur bei --leer luecke möglich): None
        out['total'] = pct([v[q] for q in ALLQ if q in v])
        for m, qs in CH.items(): out[m] = pct([v[q] for q in qs if q in v])
        out['hit_total'] = hit([v[q] for q in ALLQ if q in v])
        for m, qs in CH.items(): out['hit_' + m] = hit([v[q] for q in qs if q in v])
    return out


PD = {p: {d: day_values(x) for d, x in sorted(prov_day[p].items())} for p in ('OpenAI', 'Gemini')}


def series(p, m, w=None):
    return {d: v[m] for d, v in PD[p].items() if v['complete'] and v.get(m) is not None and (w is None or in_win(d, w))}


# ------------------------------------------------------------------ Ankertag-Tabelle
def state(p, d):
    v = PD[p].get(d)
    if v is None: return 'kein_lauf' if day(d) <= data_until.date() else 'ausstehend'
    return 'vollstaendig' if v['complete'] else ('nur_fehler' if v['n_valid'] == 0 else 'teilweise')


anchor_table = []
for a in anchors:
    d = a.isoformat()
    if d > WIN['effect'][1] and day(d) > data_until.date(): continue
    row = {'d': d, 'window': next((w for w in ('baseline', 'effect', 'delayed') if in_win(d, w)), 'cusum_ref' if in_win(d, 'cusum_ref') else None)}
    for p in ('OpenAI', 'Gemini'):
        v = PD[p].get(d, {}); row[p] = {'state': state(p, d), **{m: rnd(v.get(m)) for m in METRICS + ['research']}}
    both = all(row[p]['state'] == 'vollstaendig' for p in ('OpenAI', 'Gemini'))
    some = [p for p in ('OpenAI', 'Gemini') if row[p]['state'] == 'vollstaendig']
    row['basis'] = 'beide' if both else ('nur_' + some[0].lower() if some else None)
    row['headline'] = {m: (rnd(np.mean([row[p][m] for p in some])) if both and all(row[p][m] is not None for p in some) else None) for m in METRICS}
    row['single_provider_value'] = {m: (row[some[0]][m] if len(some) == 1 else None) for m in METRICS}
    anchor_table.append(row)


# ------------------------------------------------------------------ Statistik-Bausteine
def tnum(d): return (day(d) - EVENT).days     # Zeitachse: Tage relativ zum Erscheinen


def _betacf(a, b, x):
    """Kettenbruch der regularisierten unvollständigen Betafunktion (modifizierter Lentz)."""
    tiny = 1e-300; c = 1.0; d = 1.0 - (a + b) * x / (a + 1.0); d = 1.0 / (d if abs(d) > tiny else tiny); h = d
    for m in range(1, 400):
        for num in (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)), -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))):
            d = 1.0 + num * d; d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + num / c; c = c if abs(c) > tiny else tiny; h *= d * c
        if abs(d * c - 1.0) < 1e-16: break
    return h


def _t_cdf(t, df):
    x = df / (df + t * t); a, b = df / 2.0, 0.5
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    ib = math.exp(lb) * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1.0 - math.exp(lb) * _betacf(b, a, 1 - x) / b
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def t975(df):
    """97,5-%-Quantil der t-Verteilung. Mit scipy wie bisher; ohne scipy (z. B. venv-obs) Bisektion über die t-Verteilung,
    geprüft am 08.11.2026: alle Ergebnisdateien gleich."""
    try:
        from scipy import stats
        return float(stats.t.ppf(0.975, df))
    except ImportError:
        lo, hi = 0.0, 1000.0
        for _ in range(200):
            mid = (lo + hi) / 2; lo, hi = (mid, hi) if _t_cdf(mid, df) < 0.975 else (lo, mid)
        return (lo + hi) / 2


def ols(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float); n = len(xs)
    if n < 3 or np.ptp(xs) == 0: return None
    b, a = np.polyfit(xs, ys, 1); res = ys - (a + b * xs); s = math.sqrt((res ** 2).sum() / (n - 2))
    sxx = ((xs - xs.mean()) ** 2).sum(); se_b = s / math.sqrt(sxx)
    tc = t975(n - 2)
    return {'intercept_at_event': a, 'slope_pp_per_day': b, 'slope_se': se_b, 'slope_ci95': [b - tc * se_b, b + tc * se_b],
            'resid_sd': s, 'n': n, 'xbar': xs.mean(), 'sxx': sxx, 't975': tc}


def describe(ser):
    v = list(ser.values())
    return {'n_anchor_days': len(v), 'days': list(ser), 'mean': rnd(np.mean(v)) if v else None,
            'sd': rnd(np.std(v, ddof=1)) if len(v) > 1 else None, 'min': rnd(min(v)) if v else None, 'max': rnd(max(v)) if v else None}


def drift_of(ser):
    f = ols([tnum(d) for d in ser], list(ser.values()))
    if not f: return None
    return {'slope_pp_per_day': rnd(f['slope_pp_per_day'], 3), 'slope_ci95': [rnd(x, 3) for x in f['slope_ci95']],
            'level_at_event_pp': rnd(f['intercept_at_event']), 'resid_sd': rnd(f['resid_sd']), 'n': f['n']}


def cusum(xs, mu, sd, k=K_SD, h=H_SD):
    sp = sn = 0.0; path = []; alarms = []
    for d, x in xs:
        z = (x - mu) / sd; sp = max(0.0, sp + z - k); sn = max(0.0, sn - z - k)
        path.append({'d': d, 'x': rnd(x), 's_up': rnd(sp), 's_down': rnd(sn)})
        if sp > h or sn > h: alarms.append({'d': d, 'direction': 'up' if sp > h else 'down'}); sp = sn = 0.0
    return path, alarms


def sd_floor(m):
    """Untergrenze der SD: halber Punkt (Bewertung) bzw. halbe Antwort (Trefferquote) einer Anbieter-Messung."""
    base = m[4:] if m.startswith('hit_') else m
    nq = len(ALLQ if base == 'total' else CH[base])
    return (100.0 / nq if m.startswith('hit_') else 100.0 / (3 * nq)) / 2


rng = np.random.default_rng(SEED)


DRIFT_WIN = {'baseline': ('2026-08-19', '2026-10-07'), 'sensitivity': ('2026-08-19', '2026-09-29')}   # Driftschätzung: CUSUM-Basis ab 19.08.


def ser_range(p, m, lo, hi):
    return {d: v for d, v in series(p, m).items() if lo <= d <= hi}


def fit_parts(p, m, base_w):
    """Drift-Fenster (ab 19.08.) und Grundlinienfenster eines Anbieters; Referenz liegt nur im Drift-Fenster vor der Grundlinie."""
    lo, hi = DRIFT_WIN[base_w]
    allpre = ser_range(p, m, lo, hi); base = series(p, m, base_w)
    ref = {d: v for d, v in allpre.items() if d not in base}
    return ref, base


def detrended_delta(ref, base, eff):
    """Residuen gegen die lineare Drift (OLS über ref+base), Niveau = mittleres Residuum der Grundlinie.
    ref/base/eff: Listen von (Tag, Wert). Rückgabe (driftbereinigt, unbereinigt)."""
    pre = ref + base
    xp = np.array([tnum(d) for d, _ in pre]); yp = np.array([y for _, y in pre])
    yb = np.array([y for _, y in base]); ye = np.array([y for _, y in eff])
    raw = float(ye.mean() - yb.mean())
    if len(pre) < 3 or np.ptp(xp) == 0: return raw, raw
    b, a = np.polyfit(xp, yp, 1)
    rb = yb - (a + b * np.array([tnum(d) for d, _ in base])); re_ = ye - (a + b * np.array([tnum(d) for d, _ in eff]))
    return float(re_.mean() - rb.mean()), raw


def delta(metric, base_w, eff_w, eff_days=None):
    """Kopfzahl- bzw. Kanal-Differenz: Mittel der Anbieter-Differenzen, Bootstrap über Ankertage (je Fensterteil geschichtet).
    eff_days (nur Zusatzangabe): Wirkungstage auf diese Tage beschränken."""
    per, boots = {}, {}
    for p in ('OpenAI', 'Gemini'):
        ref, b = fit_parts(p, metric, base_w); e = series(p, metric, eff_w)
        if eff_days is not None: e = {d: v for d, v in e.items() if d in eff_days}
        per[p] = {'n_drift_ref': len(ref), 'n_base': len(b), 'n_effect': len(e), 'raw': None, 'detrended': None, 'ci95_detrended': None, 'ci95_raw': None}
        if len(b) < 3 or len(e) < 1: continue
        R_, B_, E_ = list(ref.items()), list(b.items()), list(e.items())
        per[p]['detrended'], per[p]['raw'] = detrended_delta(R_, B_, E_)
        if len(e) >= 2:
            bt = np.empty(N_BOOT); br = np.empty(N_BOOT)
            for i in range(N_BOOT):   # Ziehen mit Zurücklegen, getrennt nach Referenz-, Grundlinien- und Wirkungstagen
                ri = [R_[j] for j in rng.integers(0, len(R_), len(R_))] if R_ else []
                bi = [B_[j] for j in rng.integers(0, len(B_), len(B_))]; ei = [E_[j] for j in rng.integers(0, len(E_), len(E_))]
                bt[i], br[i] = detrended_delta(ri, bi, ei)
            boots[p] = (bt, br)
            per[p]['ci95_detrended'] = [rnd(np.percentile(bt, 2.5)), rnd(np.percentile(bt, 97.5))]
            per[p]['ci95_raw'] = [rnd(np.percentile(br, 2.5)), rnd(np.percentile(br, 97.5))]
            per[p]['boot_sd_detrended'] = rnd(np.std(bt, ddof=1), 3)
        per[p]['raw'] = rnd(per[p]['raw']); per[p]['detrended'] = rnd(per[p]['detrended'])
    ok = [p for p in per if per[p]['detrended'] is not None]
    out = {'providers': per, 'providers_used': ok, 'basis_note': None if len(ok) == 2 else ('nur ' + ok[0] if ok else 'ausstehend')}
    if not ok:
        out.update({'detrended': None, 'raw': None, 'ci95_detrended': None, 'ci95_raw': None, 'ci_excludes_zero': None, 'status': 'ausstehend'}); return out
    out['detrended'] = rnd(np.mean([per[p]['detrended'] for p in ok])); out['raw'] = rnd(np.mean([per[p]['raw'] for p in ok]))
    if all(p in boots for p in ok):
        bt = np.mean([boots[p][0] for p in ok], axis=0); br = np.mean([boots[p][1] for p in ok], axis=0)
        out['ci95_detrended'] = [rnd(np.percentile(bt, 2.5)), rnd(np.percentile(bt, 97.5))]
        out['ci95_raw'] = [rnd(np.percentile(br, 2.5)), rnd(np.percentile(br, 97.5))]
        out['boot_sd_detrended'] = rnd(np.std(bt, ddof=1), 3)
        lo, hi = out['ci95_detrended']; out['ci_excludes_zero'] = bool(lo > 0 or hi < 0)
    else:
        out['ci95_detrended'] = out['ci95_raw'] = None; out['ci_excludes_zero'] = None
    out['status'] = 'vorlaeufig' if data_until.date() < day(WIN[eff_w][1]) else 'abgeschlossen'
    return out


def drift_line(p, m, base_w='baseline'):
    """Driftgerade eines Anbieters (für Text und Abbildung): Steigung aus ref+base, Niveau so verschoben, dass das
    mittlere Residuum der Grundlinie null ist."""
    ref, b = fit_parts(p, m, base_w); pre = {**ref, **b}
    f = ols([tnum(d) for d in pre], list(pre.values()))
    if not f or not b: return None
    a, s = f['intercept_at_event'], f['slope_pp_per_day']
    shift = float(np.mean([v - (a + s * tnum(d)) for d, v in b.items()]))
    return {'slope_pp_per_day': s, 'level_at_event': a + shift, 'resid_sd': f['resid_sd'], 'n': f['n'], 'xbar': f['xbar'], 'sxx': f['sxx'], 't975': f['t975'],
            'slope_ci95': f['slope_ci95'], 'n_ref': len(ref), 'n_base': len(b)}


def combined_resid(metric, base_w, eff_w):
    """Je Ankertag: Mittel der verfügbaren Anbieter-Residuen gegen die jeweilige Driftgerade."""
    fits = {p: f for p in ('OpenAI', 'Gemini') if (f := drift_line(p, metric, base_w))}
    def res(w):
        out = {}
        for a in anchors:
            d = a.isoformat()
            if not in_win(d, w): continue
            have = [p for p in fits if d in series(p, metric)]
            rs = [series(p, metric)[d] - (fits[p]['level_at_event'] + fits[p]['slope_pp_per_day'] * tnum(d)) for p in have]
            pi = [fits[p]['t975'] * fits[p]['resid_sd'] * math.sqrt(1 + 1 / fits[p]['n'] + (tnum(d) - fits[p]['xbar']) ** 2 / fits[p]['sxx']) for p in have]
            if rs: out[d] = (float(np.mean(rs)), float(np.mean(pi)), len(rs))
        return out
    return fits, res(base_w), res(eff_w)


def first_deviation(metric, base_w='baseline', eff_w='effect'):
    fits, rb, re_ = combined_resid(metric, base_w, eff_w)
    if not fits: return {'status': 'ausstehend'}
    sd_raw = float(np.std([v[0] for v in rb.values()], ddof=1)) if len(rb) > 1 else 0.0
    sd = max(sd_raw, sd_floor(metric))
    path, alarms = cusum([(d, v[0]) for d, v in re_.items()], 0.0, sd)
    up = [a for a in alarms if a['direction'] == 'up']; down = [a for a in alarms if a['direction'] == 'down']
    pi_up = next((d for d, v in re_.items() if v[0] > v[1]), None)
    return {'baseline_resid_sd': rnd(sd_raw), 'sd_used': rnd(sd), 'sd_floor_applied': sd_raw < sd_floor(metric),
            'max_s_up': rnd(max((x['s_up'] for x in path), default=None)) if path else None, 'h': H_SD,
            'n_effect_days': len(re_), 'residuals': {d: {'resid': rnd(v[0]), 'pi95_half': rnd(v[1]), 'n_providers': v[2]} for d, v in re_.items()},
            'baseline_residuals': {d: rnd(v[0]) for d, v in rb.items()},
            'cusum_path': path, 'first_up_alarm': up[0]['d'] if up else None, 'first_down_alarm': down[0]['d'] if down else None,
            'first_above_pi95': pi_up, 'status': ('ausstehend' if not re_ else ('vorlaeufig' if data_until.date() < day(WIN[eff_w][1]) else 'abgeschlossen'))}


# ------------------------------------------------------------------ Grundlinie
def headline_series(m, w):
    return {r['d']: r['headline'][m] for r in anchor_table if r['basis'] == 'beide' and in_win(r['d'], w)}


baseline = {}
for w in ('baseline', 'sensitivity'):
    baseline[w] = {}
    for m in METRICS + ['research']:
        e = {'providers': {p: {**describe(series(p, m, w)), 'drift_within_window': drift_of(series(p, m, w)),
                               'drift_used': (lambda f: f and {'slope_pp_per_day': rnd(f['slope_pp_per_day'], 3), 'slope_ci95': [rnd(x, 3) for x in f['slope_ci95']],
                                                                'level_at_event_pp': rnd(f['level_at_event']), 'resid_sd': rnd(f['resid_sd']),
                                                                'n_days': f['n'], 'n_ref_days': f['n_ref'], 'n_base_days': f['n_base'],
                                                                'fit_window': list(DRIFT_WIN[w])})(drift_line(p, m, w) if m != 'research' else None)}
                           for p in ('OpenAI', 'Gemini')}}
        pm = [e['providers'][p]['mean'] for p in ('OpenAI', 'Gemini') if e['providers'][p]['mean'] is not None]
        e['provider_balanced_mean'] = rnd(np.mean(pm)) if len(pm) == 2 else None
        e['headline_days_both'] = describe(headline_series(m, w)) if m != 'research' else None
        baseline[w][m] = e

# Mindestens erkennbare Verschiebung (vor dem Ereignis festgelegt): 80 % Power, zweiseitig 5 %, Annahme 10 vollständige
# Wirkungs-Ankertage je Anbieter; Streuung = Residuen-SD der Driftgeraden. Grobe Planungsgröße, kein Test.
mde = {}
for m in METRICS:
    v = []
    for p in ('OpenAI', 'Gemini'):
        f = drift_line(p, m, 'baseline')
        if f: v.append(f['resid_sd'] ** 2 * (1 / f['n_base'] + 1 / 10))
    mde[m] = rnd(2.8 * math.sqrt(sum(v)) / len(v)) if len(v) == 2 else None
baseline['mde_pp_assuming_10_effect_days'] = mde

# Durch die Drift allein erwarteter Unterschied Wirkungsfenster - Grundlinie.
# 08.11.2026: je Anbieter über dessen eigene gemessene Wirkungstage (vorher: alle Wirkungs-Ankertage, auch
# Tage ohne Messung). Je Anbieter ist das genau der Abstand unbereinigt - driftbereinigt in effects.primary (gleiche Gerade).
# Der Wert über alle Wirkungs-Ankertage bleibt als gekennzeichneter Planungswert erhalten.
eff_t = [tnum(a.isoformat()) for a in anchors if in_win(a, 'effect')]
drift_implied, drift_implied_plan = {}, {}
for m in METRICS:
    per, per_plan, n_eff = {}, {}, {}
    for p in ('OpenAI', 'Gemini'):
        f = drift_line(p, m, 'baseline'); b = series(p, m, 'baseline'); e = series(p, m, 'effect')
        if f and b:
            per_plan[p] = f['slope_pp_per_day'] * (np.mean(eff_t) - np.mean([tnum(d) for d in b]))
            if e: per[p] = f['slope_pp_per_day'] * (np.mean([tnum(d) for d in e]) - np.mean([tnum(d) for d in b])); n_eff[p] = len(e)
    drift_implied[m] = {'providers': {p: rnd(v) for p, v in per.items()}, 'mean': rnd(np.mean(list(per.values()))) if len(per) == 2 else None,
                        'n_effect_days': n_eff, 'basis': 'gemessene Wirkungstage je Anbieter'}
    drift_implied_plan[m] = {'providers': {p: rnd(v) for p, v in per_plan.items()}, 'mean': rnd(np.mean(list(per_plan.values()))) if len(per_plan) == 2 else None,
                             'n_effect_anchor_days': len(eff_t),
                             'kennzeichnung': 'Planungswert: alle Wirkungs-Ankertage je Anbieter angenommen, auch Tage ohne Messung; nicht der Abstand der Schätzungen'}
baseline['drift_implied_diff_pp'] = drift_implied
baseline['drift_implied_diff_pp_planungswert'] = drift_implied_plan

# Driftprüfung: CUSUM der Grundlinien-Ankertage gegen die Referenz 19.08.-06.09. (je Anbieter, Kopfzahl-Fragen)
drift_check = {}
for p in ('OpenAI', 'Gemini'):
    drift_check[p] = {}
    for m in METRICS:
        ref = series(p, m, 'cusum_ref'); bl = series(p, m, 'baseline')
        if len(ref) < 3 or not bl: drift_check[p][m] = None; continue
        mu = float(np.mean(list(ref.values()))); sd = max(float(np.std(list(ref.values()), ddof=1)), sd_floor(m))
        path, alarms = cusum(list(bl.items()), mu, sd)
        long = {**ref, **bl}
        drift_check[p][m] = {'ref_days': list(ref), 'ref_mean': rnd(mu), 'ref_sd_used': rnd(sd), 'alarms': alarms, 'path': path,
                             'slope_long_19aug_07oct': drift_of(long)}

# ------------------------------------------------------------------ Vorher-Nachher
effects = {}
for label, bw, ew in (('primary', 'baseline', 'effect'), ('sensitivity', 'sensitivity', 'effect'), ('delayed', 'baseline', 'delayed')):
    effects[label] = {m: delta(m, bw, ew) for m in METRICS}
timing = {m: first_deviation(m) for m in ('direct', 'longtail', 'discovery', 'recommend_gr', 'total', 'hit_direct', 'hit_discovery', 'hit_total')}
# 08.11.2026: Trefferquote auch für Saga-Wissen und GR1-GR6 (ohne Zufallszahlen, ändert nichts anderes)
timing.update({m: first_deviation(m) for m in ('hit_longtail', 'hit_recommend_gr')})


def direct_rule(lab):
    """Änderung 3 (Lückenregister 39, ersetzt die Direkt-Regel aus Änderung 2): Im Direkt-Kanal ist die Trefferquote nur
    Vorzeichenprüfung. Ein Direkt-Effekt in Punkten wird berichtet, wenn sein 95-%-Intervall die Null ausschließt und der
    Schätzwert der Trefferquote dasselbe Vorzeichen hat (Schätzwert 0 zählt nicht als gleiches Vorzeichen);
    bei widersprechendem Vorzeichen: nicht belastbar. Andere Kanäle: Trefferquote volle Robustheits-Kennzahl (Intervall-Regel)."""
    a, b = effects[lab]['direct'], effects[lab]['hit_direct']
    if a['ci_excludes_zero'] is None or b['detrended'] is None: return {'status': 'ausstehend', 'verdict': None, 'reportable': None}
    if not a['ci_excludes_zero']:
        return {'status': a['status'], 'points_ci_excludes_zero': False, 'hit_estimate': b['detrended'], 'verdict': 'kein_effekt', 'reportable': False}
    same = (a['detrended'] > 0 and b['detrended'] > 0) or (a['detrended'] < 0 and b['detrended'] < 0)
    return {'status': a['status'], 'points_ci_excludes_zero': True, 'points_estimate': a['detrended'], 'hit_estimate': b['detrended'],
            'same_sign': same, 'verdict': 'berichtet' if same else 'nicht_belastbar', 'reportable': same}


def robust_rule(lab, m):
    """Andere Kanäle (Änderung 2): Effekt gilt als robust, wenn Punkte- und Trefferquoten-Intervall die Null ausschließen, gleiches Vorzeichen."""
    a, b = effects[lab][m], effects[lab]['hit_' + m]
    if a['ci_excludes_zero'] is None or b['ci_excludes_zero'] is None: return {'status': 'ausstehend', 'robust': None}
    same = (a['detrended'] > 0) == (b['detrended'] > 0)
    return {'status': a['status'], 'points_ci_excludes_zero': a['ci_excludes_zero'], 'hit_ci_excludes_zero': b['ci_excludes_zero'],
            'robust': bool(a['ci_excludes_zero'] and b['ci_excludes_zero'] and same)}


direct_effect_rule = {lab: direct_rule(lab) for lab in effects}
robustness_rule = {lab: {m: robust_rule(lab, m) for m in ('total', 'longtail', 'discovery', 'recommend_gr')} for lab in effects}


def order_verdict(rec='discovery'):
    """Reihenfolge-Urteil: Direkt gegen Empfehlungs-Kanal. Hauptfassung (im Code festgelegt am 07.10.2026): Empfehlung =
    G1, G2, C1, C2, GR1-GR6. Vorregistrierte Fassung (Q7 hypothesis): GR1-GR6 (rec='recommend_gr')."""
    dd, dr = timing['direct'], timing[rec]
    if dd.get('status') == 'ausstehend': return {'status': 'ausstehend', 'verdict': None}
    a, b = dd['first_up_alarm'], dr['first_up_alarm']
    if a is None and b is None: v = 'keine_abweichung'
    elif a and (b is None or a < b): v = 'direkt_frueher'
    elif a and b and a == b: v = 'gleichzeitig'
    else: v = 'empfehlung_frueher'
    if rec != 'discovery':
        return {'status': dd['status'], 'verdict': v, 'first_up_direct': a, 'first_up_recommend_gr': b, 'recommendation_channel': CH[rec],
                'kennzeichnung': 'vorregistrierte Fassung des Empfehlungs-Kanals (GR1-GR6); Hauptfassung (10 Fragen) siehe hypothesis_order'}
    return {'status': dd['status'], 'verdict': v, 'first_up_direct': a, 'first_up_discovery': b}


# ------------------------------------------------------------------ Claude (sekundär, beschreibend)
cw = [r for r in data['claude_web_rows'] if r['d'] >= WIN['baseline'][0]]  # 07.10. abends: alte Reihe als Kontext mitrechnen
snaps = C.defaultdict(list)
for r in cw: snaps[r['d']].append(r)
def claude_day(d, rows):
    # 07.10.2026 abends (Entscheidung des Autors): Claude = alle drei Modellfamilien, je das neueste Modell. Je Tag und Modell zaehlt der
    # erste Lauf mit Messwerten fuer dieses Modell (am 07.10.: Opus 11:50 UTC, Sonnet und Haiku 15:00 UTC).
    by_snap = C.defaultdict(list)
    for r in rows: by_snap[(r['run_ts'], r['snapshot_id'])].append(r)
    cellsc, src = {}, {}
    for k in sorted(by_snap):
        for m in sorted({x['model'] for x in by_snap[k]}):
            if m in src or not any(x['status'] != 'error' and x['model'] == m for x in by_snap[k]):
                continue
            src[m] = k
            for x in sorted((x for x in by_snap[k] if x['model'] == m), key=lambda x: (x['status'] == 'error', x['rid'])):
                cellsc.setdefault((m, x['question_id']), x)
    if not src:
        return {'n_valid': 0, 'n_error': len(rows), 'models': sorted({x['model'] for x in rows})}
    models = sorted(src)
    v = {}
    for m in models:
        vv = {q: x['score'] for (mm, q), x in cellsc.items() if mm == m and x['status'] != 'error'}
        v[m] = {'n_valid': len(vv), 'total': rnd(pct(list(vv.values()))) if vv else None,
                **{c: rnd(pct([vv[q] for q in qs if q in vv])) if any(q in vv for q in qs) else None for c, qs in CH.items()}}
    prov = {c: (rnd(sum(x[c] for x in v.values() if x.get(c) is not None) / sum(1 for x in v.values() if x.get(c) is not None))
                if any(x.get(c) is not None for x in v.values()) else None) for c in ('total', 'direct', 'longtail', 'discovery', 'recommend_gr')}
    return {'snapshots': {m: {'snapshot_id': src[m][1], 'run_ts': src[m][0]} for m in models}, 'models': models, 'by_model': v,
            'provider_mean': prov, 'n_valid': sum(x['n_valid'] for x in v.values()), 'anchor_day': d in ANCH,
            'kind': 'grundlinie' if d == CLAUDE_NEW.isoformat() else ('ankertag' if d in ANCH else 'nachholung_oder_ausserplan'),
            '_used_rids': sorted(x['rid'] for x in cellsc.values())}


claude_days = {d: claude_day(d, rows) for d, rows in sorted(snaps.items())}
# 08.11.2026 abends: beschreibende Claude-Werte, wenn die nach Eintrag 43 enger bewerteten Antworten (scorer_rules.
# eintrag43_enger_umgesetzt) nach dem Wortlaut von Eintrag 43 eingehen. Nur Kennzeichnung; maßgeblich bleibt claude.days.
_e43c = {e['rid']: e for e in scorer_rules.get('eintrag43_enger_umgesetzt', {}).get('zeilen', [])
         if e['table'] == 'claude_web_rows' and e['im_datenstand'] and args.regeln == 'vorregistriert'}
claude_e43 = {}
for d in sorted({e['d'] for e in _e43c.values()}):
    if d not in snaps or d < CLAUDE_NEW.isoformat(): continue
    alt = claude_day(d, [dict(r, score=_e43c[r['rid']]['score_wortlaut_eintrag43'], status=_e43c[r['rid']]['status_wortlaut_eintrag43'])
                         if r['rid'] in _e43c else r for r in snaps[d]])
    base_ = claude_days[d]
    used = [rid for rid in _e43c if rid in base_['_used_rids'] and _e43c[rid]['d'] == d]
    if len(used) != sum(1 for e in _e43c.values() if e['d'] == d): raise SystemExit(f'Eintrag 43: Zeile am {d} nicht gewertet')
    claude_e43[d] = {'antworten': [{'rid': rid, 'modell': _e43c[rid]['modell'], 'question_id': _e43c[rid]['question_id']} for rid in used],
                     'provider_mean': {c: {'bewerter_vorregistriert': base_['provider_mean'][c], 'wortlaut_eintrag43': alt['provider_mean'][c]} for c in ('total', 'direct')},
                     'by_model': {_e43c[rid]['modell']: {c: {'bewerter_vorregistriert': base_['by_model'][_e43c[rid]['modell']][c],
                                                             'wortlaut_eintrag43': alt['by_model'][_e43c[rid]['modell']][c]} for c in ('total', 'direct')} for rid in used}}
for x in claude_days.values(): x.pop('_used_rids', None)
old_days = {d: x for d, x in claude_days.items() if d < CLAUDE_NEW.isoformat() and d in ANCH}
claude_days = {d: x for d, x in claude_days.items() if d >= CLAUDE_NEW.isoformat()}
cb = claude_days.get(CLAUDE_NEW.isoformat())
claude = {'config': 'je das neueste Opus-, Sonnet- und Haiku-Modell auf claude.ai, Websuche, Inkognito-Chat; Anbieter Claude = Mittel der Modelle; Grundlinie 07.10.2026, Messreihe ab 09.10.2026',
          'baseline_0710': cb, 'baseline_status': 'vorhanden' if cb and cb.get('n_valid') else 'ausstehend',
          'days': claude_days, 'model_labels_seen': sorted({m for x in claude_days.values() for m in x.get('models', [])}),
          'note': 'keine Signifikanzaussage (Vorregistrierung Q7, Änderung 2)',
          'old_series': {'days': old_days, 'models': sorted({m for x in old_days.values() for m in x.get('models', [])}),
                         'comparable': False, 'note': 'feste ältere Modellstufen bis 06.10.2026, nur Ankertage; Kontext, nicht vergleichbar'}}
claude['eintrag43_wortlaut'] = {'hinweis': ('Nur Kennzeichnung (beschreibend): Tageswerte, wenn die Antworten aus freeze.scorer_rules.eintrag43_enger_umgesetzt '
                                            'nach dem Wortlaut von Eintrag 43 bewertet werden; claude.days folgt dem Bewerter in der vorregistrierten Fassung.'),
                                'days': claude_e43}
if cb and cb.get('n_valid'):
    def _fam(m): return next((f for f in ('opus', 'sonnet', 'haiku') if f in m), m)
    base_fam = {_fam(m): cb['by_model'][m] for m in cb['models']}
    claude['descriptive_diff_to_baseline'] = {}
    for d, x in claude_days.items():
        if d <= CLAUDE_NEW.isoformat() or not x.get('by_model'):
            continue
        dd = {}
        for m, vals in x['by_model'].items():
            b0 = base_fam.get(_fam(m))
            if b0:
                dd[_fam(m)] = {c: (rnd(vals[c] - b0[c]) if vals.get(c) is not None and b0.get(c) is not None else None) for c in ('total', 'direct', 'longtail', 'discovery')}
        pm, bm = x.get('provider_mean') or {}, cb.get('provider_mean') or {}
        dd['claude_mittel'] = {c: (rnd(pm[c] - bm[c]) if pm.get(c) is not None and bm.get(c) is not None else None) for c in ('total', 'direct', 'longtail', 'discovery')}
        claude['descriptive_diff_to_baseline'][d] = dd
old = [r for r in data['claude_web_rows'] if WIN['baseline'][0] <= r['d'] < CLAUDE_NEW.isoformat()]
claude['old_series_baseline_window'] = {'rows': len(old), 'valid_rows': sum(r['status'] != 'error' for r in old),
                                        'models': sorted({r['model'] for r in old}), 'comparable': False}

# ------------------------------------------------------------------ Abdeckung, Register
def cover(w):
    days = [a.isoformat() for a in anchors if in_win(a, w)]
    return {'anchor_days': len(days), 'first': days[0] if days else None, 'last': days[-1] if days else None,
            **{p: {'complete': sum(1 for d in days if state(p, d) == 'vollstaendig'),
                   'not_complete': [d for d in days if state(p, d) not in ('vollstaendig', 'ausstehend')],
                   'pending': [d for d in days if state(p, d) == 'ausstehend']} for p in ('OpenAI', 'Gemini')},
            'both_complete': sum(1 for d in days if all(state(p, d) == 'vollstaendig' for p in ('OpenAI', 'Gemini')))}


coverage = {w: cover(w) for w in ('cusum_ref', 'baseline', 'sensitivity', 'effect', 'delayed')}
gaps = sorted([g for g in data['data_gaps'] if g['gap_end'][:10] >= WIN['cusum_ref'][0]], key=lambda g: g['id'])
off_anchor = {p: sorted({r['d'] for r in data['web_rows'] if PROV[r['llm']] == p and r['d'] not in ANCH and r['d'] >= ANCHOR0.isoformat()})
              for p in ('OpenAI', 'Gemini')}
questions = {q['question_id']: {'category': q['category'], 'question': q['question']} for q in data['questions']}



# ------------------------------------------------------------------ 08.11.2026: Wirkungsfenster beschreibend
def window_block(w):
    """Anbietermittel eines Fensters aus ungerundeten Tageswerten, jeder Anbieter über seine eigenen gemessenen Ankertage.
    Für das Wirkungsfenster ist diff_provider_balanced genau die unbereinigte Differenz (effects.primary.*.raw)."""
    out = {}
    for m in METRICS + ['research']:
        prov = {p: describe(series(p, m, w)) for p in ('OpenAI', 'Gemini')}
        um = [float(np.mean(list(series(p, m, w).values()))) for p in ('OpenAI', 'Gemini') if series(p, m, w)]
        out[m] = {'providers': prov, 'provider_balanced_mean': rnd(np.mean(um)) if len(um) == 2 else None,
                  'headline_days_both': describe(headline_series(m, w)) if m != 'research' else None}
    return out


effect_window = {'hinweis': ('Anbietermittel = Mittel der beiden Anbietermittel aus ungerundeten Tageswerten, jeder Anbieter über seine '
                             'eigenen gemessenen Wirkungstage (OpenAI und Gemini können verschieden viele Tage haben); gleiche Basis '
                             'wie baseline.baseline.*.provider_balanced_mean. Der Abstand beider ist die unbereinigte Differenz '
                             'effects.primary.*.raw (dort je Anbieter gerundet gemittelt). headline_days_both = nur Tage mit beiden Anbietern.'),
                 'by_metric': window_block('effect')}


# ------------------------------------------------------------------ 08.11.2026: Zusatzangaben (nicht vorregistriert)
def halves(p, m):
    """Mittleres Residuum eines Anbieters gegen seine eigene Driftgerade (Grundlinienresiduen im Mittel null) je Hälfte
    der Wirkungs-Ankertage. Das Mittel beider Hälften ist bei voller Abdeckung der driftbereinigte Anbieterwert."""
    f = drift_line(p, m, 'baseline')
    if not f: return None
    days = [a.isoformat() for a in anchors if in_win(a, 'effect')]; h = len(days) // 2
    s = series(p, m, 'effect'); out = {}
    for k, ds in (('erste_haelfte', days[:h]), ('zweite_haelfte', days[h:])):
        rs = [s[d] - (f['level_at_event'] + f['slope_pp_per_day'] * tnum(d)) for d in ds if d in s]
        out[k] = {'anchor_days': [ds[0], ds[-1]] if ds else None, 'days_measured': [d for d in ds if d in s], 'n': len(rs),
                  'mean_resid': rnd(np.mean(rs)) if rs else None}
    return out


def cusum_critical(m):
    """Erster Aufwärtsalarm und die größte Streuung, bei der er noch auftritt (Bisektion; gleiche Residuen wie timing)."""
    t = timing[m]
    if t.get('status') == 'ausstehend': return None
    fits, rb, re_ = combined_resid(m, 'baseline', 'effect')
    xs = [(d, v[0]) for d, v in re_.items()]
    sd0 = max(float(np.std([v[0] for v in rb.values()], ddof=1)), sd_floor(m))

    def first_up(sd):
        al = cusum(xs, 0.0, sd)[1]; u = [a['d'] for a in al if a['direction'] == 'up']; return u[0] if u else None
    out = {'first_up_alarm': t['first_up_alarm'], 'sd_used': rnd(sd0, 3), 'max_s_up': t['max_s_up'], 'h': H_SD, 'k': K_SD}
    if first_up(sd0) is None: out['alarm_solange_sd_unter'] = None; return out
    lo, hi = sd0, sd0 * 20
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if first_up(mid) else (lo, mid)
    if not all(first_up(x) for x in np.linspace(sd0, lo, 40)): raise SystemExit(f'CUSUM-Schwelle {m}: Alarm nicht monoton in der Streuung')
    out['alarm_solange_sd_unter'] = rnd(lo, 3)
    return out


def mde_drift(m):
    """Mindestens erkennbare Verschiebung des tatsächlich gerechneten Tests (80 % Power, zweiseitig 5 %): 2,8-mal die
    Bootstrap-Standardabweichung der driftbereinigten Schätzung. Zum Vergleich die analytische Näherung mit den gemessenen
    Wirkungstagen je Anbieter und der Unsicherheit der Driftgeraden (Varianz je Anbieter
    s^2 (1/n_Grundlinie + 1/n_Wirkung + (t_Wirkung - t_Grundlinie)^2 / Sxx)) und der Planungswert (10 Tage, Drift bekannt)."""
    v, det = [], {}
    for p in ('OpenAI', 'Gemini'):
        f = drift_line(p, m, 'baseline'); b = series(p, m, 'baseline'); e = series(p, m, 'effect')
        if not (f and b and e): continue
        tb, te = np.mean([tnum(d) for d in b]), np.mean([tnum(d) for d in e])
        v.append(f['resid_sd'] ** 2 * (1 / len(b) + 1 / len(e) + (te - tb) ** 2 / f['sxx']))
        det[p] = {'n_base': len(b), 'n_effect': len(e), 'resid_sd': rnd(f['resid_sd'], 3), 'tbar_base': rnd(tb), 'tbar_effect': rnd(te), 'sxx': rnd(f['sxx'], 1)}
    E = effects['primary'][m]
    return {'wert': rnd(2.8 * E['boot_sd_detrended']) if E.get('boot_sd_detrended') is not None else None,
            'methode': ('2,8-mal die Bootstrap-Standardabweichung der driftbereinigten Schätzung effects.primary (enthält die '
                        'Unsicherheit von Driftgerade, Grundlinie und Wirkungstagen bei der tatsächlichen Tageszahl je Anbieter)'),
            'naeherung_analytisch': rnd(2.8 * math.sqrt(sum(v)) / len(v)) if len(v) == 2 else None,
            'planungswert_10_tage_drift_bekannt': mde.get(m), 'providers': det}


def pooled_hit_direct(w):
    """Trefferquote Direkt über alle Antworten des Fensters gezählt (nicht als Mittel der beiden Anbieter)."""
    hits = ans = 0
    for p in ('OpenAI', 'Gemini'):
        for d, v in series(p, 'hit_direct', w).items(): hits += round(v * len(CH['direct']) / 100); ans += len(CH['direct'])
    return {'hits': hits, 'answers': ans, 'pct': rnd(100.0 * hits / ans) if ans else None,
            'mittel_der_anbieter': baseline['baseline']['hit_direct']['provider_balanced_mean'] if w == 'baseline' else None}


zusatz = {'status': 'zusatzangaben_nicht_vorregistriert',
          'hinweis': ('Ergänzende, nicht vorregistrierte Angaben (Prüfung vom 08.11.2026). '
                      'Die Entscheidung folgt allein effects.primary und hypothesis_order.'),
          'haelften_gegen_driftgerade': {p: {m: halves(p, m) for m in SCORE_METRICS} for p in ('OpenAI', 'Gemini')},
          'cusum_streuung_kritisch': {m: cusum_critical(m) for m in ('total', 'hit_total')},
          'mde_mit_drift_unsicherheit': {m: mde_drift(m) for m in SCORE_METRICS},
          'obergrenze_anteil_grundlinie_pct': {m: (rnd(100.0 * effects['primary'][m]['ci95_detrended'][1] / baseline['baseline'][m]['provider_balanced_mean'], 1)
                                                   if effects['primary'][m].get('ci95_detrended') and baseline['baseline'][m]['provider_balanced_mean'] else None)
                                               for m in SCORE_METRICS},
          'hit_direct_grundlinie_gepoolt': pooled_hit_direct('baseline')}
if VARIANT == 'haupt':
    # Kopfzahl und Kanäle nur auf den Wirkungstagen mit beiden Anbietern (eigener Lauf des Zufallsgenerators, gleicher Startwert;
    # die Hauptanalyse ist zu diesem Zeitpunkt fertig gerechnet und bleibt unberührt)
    both_days = [r['d'] for r in anchor_table if r['basis'] == 'beide' and in_win(r['d'], 'effect')]
    rng = np.random.default_rng(SEED)
    zusatz['tage_beide_anbieter'] = {'days': both_days, 'n_days': len(both_days),
                                     'hinweis': 'Wirkungsfenster auf die Tage mit beiden Anbietern beschränkt (OpenAI an denselben Tagen wie Gemini); Grundlinie unverändert',
                                     'effects': {m: delta(m, 'baseline', 'effect', eff_days=set(both_days)) for m in METRICS}}

# ------------------------------------------------------------------ Ausgabe
GAP_AT = {g['id']: str(g['recorded_at'])[:10] for g in data['data_gaps']}
VARIANT_INFO = {
    'regeln_nachtrag': {'status': 'sensitivitaet', 'register_entry': 71,
                        'beschreibung': 'Bewertungsregeln vom 02.11.2026 in Grundlinie und Wirkungsfenster (Grundlinie am Auszug von 500 Zeichen neu bewertet)'},
    'leere_antworten_luecke': {'status': 'sensitivitaet', 'register_entry': 66,
                               'beschreibung': 'Leere Antworten als Lücke: die Frage fehlt an diesem Tag, der Tageswert wird über die übrigen Fragen gebildet'},
    'leere_antworten_fehler': {'status': 'sensitivitaet', 'register_entry': 66,
                               'beschreibung': 'Leere Antworten als Fehlmessung: der Anbieter-Tag ist nicht vollständig und entfällt'},
    'ohne_aenderung4': {'status': 'sensitivitaet', 'register_entry': 50,
                        'beschreibung': ('Ohne Änderung 4 (Buchtitel als Bewertungsanker, festgelegt am 15.10.2026 im laufenden Wirkungsfenster): '
                                         'die beiden damals rückwirkend geänderten Antworten (12.10., L1, Gemini und Claude Opus) auf 0 Punkte. '
                                         'Volltextprüfung 08.11.2026 der OpenAI- und Gemini-Antworten mit Punkten über null an den Ankertagen '
                                         '18.10. bis 08.11.: nach den vorregistrierten Regeln 57 Antworten (nach den Werten der Messdatenbank 56; '
                                         'Zählung in extension_0811.titelanker_pruefung). 54 nennen den Autor namentlich, 2 Direkt-Antworten zu D3 '
                                         'nennen ihn über die Domain (für D2 und D3 gilt der Titel-Anker nicht), und eine Antwort zu R1 (08.11., OpenAI) '
                                         'erhält nach den vorregistrierten Regeln 0,5 Punkte, weil sie das Wort Marin aus der Frage wiederholt. Keine '
                                         'weitere Antwort hängt allein am Titel-Anker. Claude nicht geprüft.')},
    'erweiterung_0811': {'status': 'nicht_vorregistriert', 'register_entry': 83,
                         'beschreibung': ('Erweiterung des Wirkungsfensters bis einschließlich Ankertag 08.11.2026. Entscheidung des Autors nach Ende '
                                          'des Wirkungsfensters, um die Gemini-Messung des 08.11. aufzunehmen; nicht vorregistriert. Hypothesen, '
                                          'Kennzahlen, Driftbereinigung, Bewertungsregeln (vorregistriert, inkl. Neubewertung am Volltext) und '
                                          'Entscheidungsregel unverändert; entschieden wird allein mit der Hauptanalyse (Wirkungsfenster bis 07.11., '
                                          'letzter Ankertag 05.11.).')},
}
OUTF = {'haupt': 'results.json', 'regeln_nachtrag': 'results_regeln_nachtrag.json', 'leere_antworten_luecke': 'results_leere_antworten.json',
        'leere_antworten_fehler': 'results_leere_antworten.json', 'ohne_aenderung4': 'results_ohne_aenderung4.json',
        'erweiterung_0811': 'results_erweiterung_0811.json'}
now = dt.datetime.now(dt.timezone.utc)
res = {
    'generated_at_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    # 08.11.2026: Fassung 1.4 mit vier Änderungen; Änderung 4 im laufenden Wirkungsfenster
    'preregistration': {'id': 'prereg-q7-book-release-effect', 'version': 'v1.4 · 2026-10-15', 'event': EVENT.isoformat(),
                        'preorder': PREORDER.isoformat(), 'windows': WIN, 'register_entries': [12, 18, 36, 38, 39, 50],
                        'amendments': [
                            {'nr': 1, 'version': 'v1.1', 'fixed': '2026-10-07', 'register_entry': 36, 'before_event': True},
                            {'nr': 2, 'version': 'v1.2', 'fixed': '2026-10-07', 'register_entry': 38, 'before_event': True},
                            {'nr': 3, 'version': 'v1.3', 'fixed': '2026-10-07', 'register_entry': 39, 'before_event': True},
                            {'nr': 4, 'version': 'v1.4', 'fixed': '2026-10-15', 'register_entry': 50, 'before_event': False,
                             'hinweis': ('im laufenden Wirkungsfenster nach den Ankertagen 09.10., 12.10. und 15.10. festgelegt; ändert eine '
                                         'Gemini-Antwort im Wirkungsfenster (12.10., L1, 0 -> 2 Punkte) und eine Claude-Antwort (beschreibend); '
                                         'Sensitivität ohne Änderung 4: sensitivitaeten.ohne_aenderung4')}],
                        'vermerke_2026_11_08': {'correction': 'Registerzeiten der Einträge 12 und 18 (Fassung im Repositorium seit 07.10.2026)',
                                                'extension': 'nicht vorregistrierte Erweiterung bis Ankertag 08.11.2026 (Eintrag 83)'},
                        'register_recorded_at': {str(i): GAP_AT.get(i) for i in (12, 18, 36, 38, 39, 50)},
                        'method_addenda_register_entries': {'66': 'leere Antworten (Sensitivität)', '71': 'Bewertungsregeln vom 02.11.2026 (Hauptanalyse vorregistriert, Sensitivität)',
                                                            '83': 'Erweiterung bis Ankertag 08.11.2026 (nicht vorregistriert)'}},
    'freeze': {'baseline': freeze_b, 'post_sources': {f'{lo:%Y-%m-%d}..{hi:%Y-%m-%d}': pd_.name for lo, hi, pd_ in SEG}, 'post': freeze_post,
               # 08.11.2026 abends: Die eingefrorenen freeze.json bleiben unverändert; ihr Feld preregistration ist der Text, den
               # build/fetch.py beim Abzug fest eintrug (bis 08.11.2026 'Q7_book_release v1.1 (2026-10-07)').
               'preregistration_hinweis': {
                   'text': ('Das Feld preregistration in freeze.baseline und freeze.post.* ist der Text, den build/fetch.py beim Abzug fest '
                            'eintrug (bis zum 08.11.2026 stand dort Q7_book_release v1.1 (2026-10-07)); die eingefrorenen Abzüge bleiben '
                            'unverändert. Maßgeblich ist preregistration.version (Fassung 1.4 vom 15.10.2026 mit datierten Vermerken vom 08.11.2026).'),
                   'massgeblich': 'v1.4 · 2026-10-15',
                   'feld_in_abzuegen': {'baseline_freeze': freeze_b.get('preregistration'), **{k: v.get('preregistration') for k, v in freeze_post.items()}}},
               'data_until_utc': data_until.strftime('%Y-%m-%dT%H:%M:%SZ'), 'integrity': integrity,
               'baseline_corrections_applied': corrections_applied, 'scorer_rules': scorer_rules,
               'baseline_supplements_log': json.loads((BF / 'supplements.json').read_text(encoding='utf-8')) if (BF / 'supplements.json').exists() else []},
    'phase': ('grundlinie' if data_until.date() < EVENT else ('wirkungsfenster_laufend' if data_until.date() < day(WIN['effect'][1]) else
              ('beobachtung_laufend' if data_until.date() < day(WIN['delayed'][1]) else 'abgeschlossen'))),
    'definitions': {'channels': CH, 'headline_questions': ALLQ, 'n_boot': N_BOOT, 'seed': SEED, 'cusum_k_sd': K_SD, 'cusum_h_sd': H_SD,
                    'sd_floor_pp': {m: rnd(sd_floor(m), 3) for m in METRICS}, 'time_axis': 'Tage relativ zum 08.10.2026'},
    'dedupe': {'dropped_rows': dropped, 'planned_time_source': dict(plan_src)},
    'anchors': [a.isoformat() for a in anchors], 'anchor_table': anchor_table,
    'coverage': coverage, 'off_anchor_days': off_anchor,
    'baseline': baseline, 'drift_check': drift_check,
    'effects': effects, 'direct_effect_rule': direct_effect_rule, 'robustness_rule': robustness_rule, 'timing': timing, 'hypothesis_order': order_verdict(),
    'hypothesis_order_gr1_gr6': order_verdict('recommend_gr'),
    'effect_window': effect_window, 'zusatzangaben': zusatz,
    'claude': claude, 'data_gaps': gaps, 'questions': questions,
}
if VARIANT != 'haupt':
    info = {'name': VARIANT, **VARIANT_INFO[VARIANT], 'register_recorded_at': GAP_AT.get(VARIANT_INFO[VARIANT]['register_entry'])}
    if args.leer != 'vorregistriert':
        info['leere_antworten'] = {'gesamt': len(variant_rows), 'auf_ankertagen': sum(1 for x in variant_rows if x['d'] in ANCH),
                                   'je_fenster_ankertage': {w: sum(1 for x in variant_rows if x['d'] in ANCH and in_win(x['d'], w)) for w in ('cusum_ref', 'baseline', 'effect', 'delayed')},
                                   'je_anbieter_ankertage': dict(C.Counter(PROV[x['llm']] for x in variant_rows if x['d'] in ANCH)),
                                   'zeilen_ankertage': [x for x in variant_rows if x['d'] in ANCH]}
    else:
        info['geaenderte_zeilen'] = variant_rows
    if args.erweiterung:
        info['abzug'] = {'ordner': 'data/' + EXT_DIR, **{k: freeze_post[EXT_DIR].get(k) for k in ('frozen_at_utc', 'cutoff_utc', 'rows')}}
        # Zählbasis der Volltextprüfung zu Änderung 4 (Titel als Anker): gewertete Antworten von OpenAI und Gemini mit Punkten
        # über null an den Ankertagen 18.10. bis 08.11., nach den vorregistrierten Regeln und nach den Werten der Messdatenbank
        _pos = [(d, llm, q, r) for (d, llm, q), (_, r) in cells.items() if '2026-10-18' <= d <= WIN['effect'][1] and r['status'] != 'error']
        _db = lambda r: db_orig.get(('web_rows', r['rid']), (r['score'], r['status']))
        info['titelanker_pruefung'] = {
            'zeitraum': ['2026-10-18', WIN['effect'][1]],
            'ueber_null_vorregistriert': sum(1 for *_, r in _pos if r['score'] > 0),
            'ueber_null_messdatenbank': sum(1 for *_, r in _pos if _db(r)[0] > 0),
            'nur_vorregistriert_ueber_null': [{'rid': r['rid'], 'd': d, 'anbieter': llm, 'question_id': q, 'score': r['score'], 'status': r['status']}
                                              for d, llm, q, r in _pos if r['score'] > 0 and _db(r)[0] <= 0],
            'je_anbieter_vorregistriert': dict(C.Counter(PROV[llm] for d, llm, q, r in _pos if r['score'] > 0))}
    res = {'variante': info, **res}


def kompakt(r):
    """Kompakte Kennzahlen eines Laufs für results.json (volle Werte in der jeweiligen Datei)."""
    E = r['effects']['primary']; T = r['timing']
    ef = {}
    for m in METRICS:
        x = E[m]; ef[m] = {k: x.get(k) for k in ('detrended', 'ci95_detrended', 'raw', 'ci95_raw', 'ci_excludes_zero', 'status', 'basis_note')}
        ef[m]['providers'] = {p: {k: x['providers'][p].get(k) for k in ('n_base', 'n_effect', 'detrended', 'ci95_detrended', 'raw', 'ci95_raw')} for p in ('OpenAI', 'Gemini')}
    es = {}
    for m in METRICS:
        x = r['effects']['sensitivity'][m]; es[m] = {k: x.get(k) for k in ('detrended', 'ci95_detrended', 'raw', 'ci95_raw', 'ci_excludes_zero')}
        es[m]['providers'] = {p: {k: x['providers'][p].get(k) for k in ('n_base', 'n_effect', 'detrended', 'ci95_detrended', 'raw', 'ci95_raw')} for p in ('OpenAI', 'Gemini')}
    return {'effects_primary': ef,
            'effects_sensitivity_baseline': es,
            'timing': {m: {k: T[m].get(k) for k in ('first_up_alarm', 'first_down_alarm', 'first_above_pi95', 'sd_used', 'max_s_up', 'n_effect_days')} for m in T},
            'hypothesis_order': r['hypothesis_order'], 'hypothesis_order_gr1_gr6': r.get('hypothesis_order_gr1_gr6'),
            'direct_effect_rule': r['direct_effect_rule']['primary'], 'robustness_rule': r['robustness_rule']['primary'],
            'coverage': {w: r['coverage'][w] for w in ('cusum_ref', 'baseline', 'effect')},
            'baseline_balanced_mean': {m: r['baseline']['baseline'][m]['provider_balanced_mean'] for m in METRICS},
            'effect_window_balanced_mean': {m: r['effect_window']['by_metric'][m]['provider_balanced_mean'] for m in METRICS},
            'drift_implied_diff_pp': {m: r['baseline']['drift_implied_diff_pp'][m] for m in SCORE_METRICS},
            'scorer_overrides': r['freeze']['scorer_rules']['overrides']}


if VARIANT == 'haupt' and args.source != 'none' and not args.ohne_varianten:
    # Jede Variante als eigener Lauf dieses Skripts (frischer Zufallsgenerator mit demselben Startwert, Hauptanalyse unberührt)
    t0 = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    for flags in (['--regeln', 'nachtrag'], ['--leer', 'luecke'], ['--leer', 'fehler'], ['--ohne-aenderung4'], ['--erweiterung', '0811']):
        pr = subprocess.run([sys.executable, str(Path(__file__).resolve()), *flags], capture_output=True, text=True)
        if pr.returncode: raise SystemExit('Variante fehlgeschlagen (' + ' '.join(flags) + '):\n' + pr.stdout[-800:] + pr.stderr[-2000:])
        print('  Variante', ' '.join(flags), '->', [l for l in pr.stdout.splitlines() if 'Wirkung Kopfzahl' in l][-1].strip())

    def load(n, part=None):
        x = json.loads((D / n).read_text(encoding='utf-8')); x = x[part] if part else x
        if x['generated_at_utc'] < t0: raise SystemExit(f'{n} {part or ""}: nicht in diesem Lauf erzeugt')
        return x
    VN, VA, VX = load('results_regeln_nachtrag.json'), load('results_ohne_aenderung4.json'), load('results_erweiterung_0811.json')
    VL = {k: load('results_leere_antworten.json', k) for k in ('luecke', 'fehler')}
    res['sensitivitaeten'] = {
        'hinweis': 'Kompakte Kennzahlen; vollständige Ergebnisse in der genannten Datei. Die Entscheidung folgt allein der Hauptanalyse.',
        'regeln_nachtrag': {'status': 'sensitivitaet', 'register_entry': 71, 'datei': 'data/results_regeln_nachtrag.json', **kompakt(VN)},
        'leere_antworten': {'status': 'sensitivitaet', 'register_entry': 66, 'datei': 'data/results_leere_antworten.json',
                            'leere_antworten': {k: v for k, v in VL['luecke']['variante']['leere_antworten'].items() if k != 'zeilen_ankertage'},
                            'luecke': {'beschreibung': VARIANT_INFO['leere_antworten_luecke']['beschreibung'], **kompakt(VL['luecke'])},
                            'fehler': {'beschreibung': VARIANT_INFO['leere_antworten_fehler']['beschreibung'], **kompakt(VL['fehler'])}},
        'ohne_aenderung4': {'status': 'sensitivitaet', 'register_entry': 50, 'datei': 'data/results_ohne_aenderung4.json',
                            'beschreibung': VARIANT_INFO['ohne_aenderung4']['beschreibung'], 'geaenderte_zeilen': VA['variante']['geaenderte_zeilen'], **kompakt(VA)},
    }
    a0811 = next((r for r in VX['anchor_table'] if r['d'] == '2026-11-08'), None)
    cx = VX['claude']['days'].get('2026-11-08') or {}
    g83 = next((g for g in VX['data_gaps'] if g['id'] == 83), None)
    if not g83 or str(g83['recorded_at'])[:10] != VX['variante']['register_recorded_at']: raise SystemExit('Eintrag 83 fehlt im Abzug der Erweiterung')
    TA = VX['variante']['titelanker_pruefung']
    # Die Beschreibung der Sensitivität ohne Änderung 4 nennt diese Zählung (57 / 56, eine Antwort nur vorregistriert über null)
    if (TA['ueber_null_vorregistriert'], TA['ueber_null_messdatenbank'], len(TA['nur_vorregistriert_ueber_null'])) != (57, 56, 1) \
            or TA['nur_vorregistriert_ueber_null'][0]['question_id'] != 'R1' or TA['nur_vorregistriert_ueber_null'][0]['status'] != 'name_only_echo':
        raise SystemExit(f'Volltextprüfung Änderung 4: Zählung weicht von der Beschreibung ab ({TA})')
    res['sensitivitaeten']['ohne_aenderung4']['volltextpruefung_titelanker'] = {'datei': 'data/results_erweiterung_0811.json', **TA}
    _xf = VX['freeze']['post'][EXT_DIR]
    res['freeze']['preregistration_hinweis']['feld_in_abzuegen'][EXT_DIR] = _xf.get('preregistration')
    res['freeze']['preregistration_hinweis'][EXT_DIR + '_preregistration_fassung'] = _xf.get('preregistration_fassung')
    res['extension_0811'] = {
        'status': 'nicht_vorregistriert', 'register_entry': 83, 'register_recorded_at': VX['variante']['register_recorded_at'],
        'register_recorded_at_utc': str(g83['recorded_at']), 'titelanker_pruefung': TA,
        'beschreibung': VARIANT_INFO['erweiterung_0811']['beschreibung'], 'datei': 'data/results_erweiterung_0811.json',
        'window_effect': VX['preregistration']['windows']['effect'], 'abzug': VX['variante']['abzug'],
        'anchor_0811': a0811, **kompakt(VX),
        'vergleich_hauptanalyse': {m: {'haupt': effects['primary'][m]['detrended'], 'erweiterung': VX['effects']['primary'][m]['detrended'],
                                       'differenz': rnd(VX['effects']['primary'][m]['detrended'] - effects['primary'][m]['detrended'])
                                       if VX['effects']['primary'][m]['detrended'] is not None and effects['primary'][m]['detrended'] is not None else None}
                                   for m in METRICS},
        'claude_0811': {'provider_mean': cx.get('provider_mean'), 'by_model': cx.get('by_model'),
                        'descriptive_diff_to_baseline': VX['claude'].get('descriptive_diff_to_baseline', {}).get('2026-11-08')},
    }
elif VARIANT == 'haupt':
    res['sensitivitaeten'] = res['extension_0811'] = None

outp = D / OUTF[VARIANT]
if VARIANT.startswith('leere_antworten_'):   # ein gemeinsamer Container, je Modus ein Teil
    cont = json.loads(outp.read_text(encoding='utf-8')) if outp.exists() else {}
    cont.update({'beschreibung': 'Sensitivität leere Antworten (Register 66): Teil luecke und Teil fehler, je ein vollständiger Lauf von analyze.py',
                 'status': 'sensitivitaet', 'register_entry': 66, args.leer: res})
    outp.write_text(json.dumps(cont, ensure_ascii=False, indent=1), encoding='utf-8')
else:
    outp.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
b = baseline['baseline']
print('Lauf:', VARIANT, '->', outp.name)
print('Phase:', res['phase'], '· Daten bis', res['freeze']['data_until_utc'], '· Quellen danach:', res['freeze']['post_sources'])
for m in METRICS:
    x = b[m]; print(f"  Grundlinie {m:13s} OpenAI {x['providers']['OpenAI']['mean']} (n={x['providers']['OpenAI']['n_anchor_days']}) · "
                    f"Gemini {x['providers']['Gemini']['mean']} (n={x['providers']['Gemini']['n_anchor_days']}) · ausgeglichen {x['provider_balanced_mean']}")
print('  Wirkung Kopfzahl:', effects['primary']['total']['status'], effects['primary']['total']['detrended'], effects['primary']['total']['ci95_detrended'])
print('  Claude-Grundlinie 07.10.:', claude['baseline_status'])
late = {t: v['new_in_later_pull'] for t, v in integrity.items() if v['new_in_later_pull']}
if late: print('  HINWEIS: Zeilen vor dem Stichtag, die nach dem Einfrieren eingetroffen sind:', late, '-> build/freeze_baseline.py ausführen')
chg = {t: (v['changed_in_later_pull'], v['missing_in_later_pull']) for t, v in integrity.items() if v['changed_in_later_pull'] or v['missing_in_later_pull']}
if chg: print('  WARNUNG: Grundlinienzeilen in der Datenbank verändert/fehlend:', chg, '-> im Bericht ausweisen, Grundlinie bleibt eingefroren')
