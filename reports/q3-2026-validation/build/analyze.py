#!/usr/bin/env python3
"""Aktivitaets-Bericht Q3/2026 — Instrument-Validierung Phase 1. Liest NUR data/*.json (fetch.py).
Ausgabe data/results.json = einzige Zahlenquelle fuer Figuren und Text.
Etappe 1 (01.10.2026): Abdeckung je Anbieter + Wiederhol-Uebereinstimmung (Test-Retest) je Frage.
Etappe 2 (04.10.2026): Tageswert je Anbieter, CUSUM (h=5), Cronbachs Alpha, Eingriffs-Chronik Q0-Q6.
Etappe 3 (04.10.2026): Alarm-Abgleich mit dem Luecken-Register, CUSUM gegen rollierende 30-Tage-Basis, Hypothesen H-Q0-INST-01..06,
                     Abdeckungsbilanz Soll/Ist, Anker-Messflaechen (Wikidata, Knowledge Graph, Bing, Search Console)."""
import json, datetime as dt, collections as C
from pathlib import Path
R = Path(__file__).resolve().parent.parent; D = R/'data'
web = json.load(open(D/'web_rows.json')); cw = json.load(open(D/'claude_web_rows.json'))
gaps = json.load(open(D/'data_gaps.json')); freeze = json.load(open(D/'freeze.json'))
START, END = (dt.date.fromisoformat(x) for x in freeze['window'])
ANCHOR0 = dt.date(2026, 8, 19)          # Kadenz alle 3 Tage seit 19.08. (data_gaps id 4)
N_Q = 16
# Kopfzahl-Anbieter (Kanon 04.09.): OpenAI-Websuche, Gemini, Claude-Web. Claude-Web = Web-Tiers, ohne Fremdmodelle im Werkzeug.
WEB = {'openai_search': 'OpenAI', 'gemini': 'Gemini'}
CW_FOREIGN = {'gemini-2.5-flash-grounded', 'gpt-4o-mini-search-preview', 'gpt-4o-search-preview'}

def is_err(st): return st == 'error'
# ---- eine Zeile je (Tag, Anbieter-Einheit, Frage), Kanon-Regel (Forschungsentscheid 04.09.2026, Registereintrag 11):
#      Fehlerzeile verliert immer; sonst gewinnt die Zeile, deren Zeitstempel dem planmaessigen Laufzeitpunkt am naechsten liegt;
#      Gleichstand -> frueherer Zeitstempel, dann Reihenfolge im Abzug (entspricht kleinster rowid).
#      Planmaessiger Laufzeitpunkt eines Tages: OpenAI/Gemini = run_at des fruehesten cron-Laufs unter den Laeufen des Tages
#      (runs.json; ohne cron-Lauf der frueheste Lauf, ohne Laufeintrag der frueheste Messzeitpunkt des Laufs);
#      Claude-Web = run_ts des fruehesten Snapshots (Laufs) des Tages.
def ts_of(x):
    x = x.replace('Z', '+00:00').replace(' ', 'T')
    t = dt.datetime.fromisoformat(x)
    return t.replace(tzinfo=None) if t.tzinfo is None else t.astimezone(dt.timezone.utc).replace(tzinfo=None)
runs = json.load(open(D/'runs.json')); RUN = {r['id']: r for r in runs}
first_ts_of_run = {}
for r in web:
    t = ts_of(r['asked_at'])
    if r['run_id'] not in first_ts_of_run or t < first_ts_of_run[r['run_id']]: first_ts_of_run[r['run_id']] = t
day_runs = C.defaultdict(set)
for r in web:
    if r['llm'] in WEB: day_runs[(r['d'], r['llm'])].add(r['run_id'])
def planned_web(d, llm):
    rs = day_runs[(d, llm)]; known = [RUN[x] for x in rs if x in RUN]
    cron = [ts_of(x['run_at']) for x in known if x['triggered_by'] == 'cron']
    if cron: return min(cron), 'cron'
    if known: return min(ts_of(x['run_at']) for x in known), 'run'
    return min(first_ts_of_run[x] for x in rs), 'first_row'
cw_day_first = {}
for r in cw:
    t = ts_of(r['run_ts'])
    if r['d'] not in cw_day_first or t < cw_day_first[r['d']]: cw_day_first[r['d']] = t
cells = {}; dedupe_stats = C.Counter(); planned_src = C.Counter()
def put(key, ts, plan, idx, score, st):
    t = ts_of(ts); cand = (is_err(st), abs((t - plan).total_seconds()), t, idx)
    cur = cells.get(key)
    if cur is not None: dedupe_stats['dropped'] += 1
    if cur is None or cand < cur[4]: cells[key] = (is_err(st), ts, score, st, cand)
plan_cache = {}
for i, r in enumerate(web):
    if r['llm'] in WEB:
        k = (r['d'], r['llm'])
        if k not in plan_cache: plan_cache[k] = planned_web(*k); planned_src[plan_cache[k][1]] += 1
        put((r['d'], WEB[r['llm']], r['llm'], r['question_id']), r['asked_at'], plan_cache[k][0], i, r['score'], r['status'])
for i, r in enumerate(cw):
    if r['model'] not in CW_FOREIGN: put((r['d'], 'Claude-Web', r['model'], r['question_id']), r['run_ts'], cw_day_first[r['d']], i, r['score'], r['status'])
cells = {k: v[:4] for k, v in cells.items()}

# ---- 1. Abdeckung je Tag x Anbieter
day = C.defaultdict(lambda: {'valid': 0, 'error': 0, 'units': set()})
for (d, prov, unit, q), (err, ts, sc, st) in cells.items():
    x = day[(d, prov)]; x['units'].add(unit); x['error' if err else 'valid'] += 1
def soll(prov, n_units): return N_Q * max(n_units, 1)
cov = {}
for prov in ('OpenAI', 'Gemini', 'Claude-Web'):
    ds = sorted(d for (d, p) in day if p == prov)
    full = [d for d in ds if day[(d, prov)]['valid'] >= soll(prov, len(day[(d, prov)]['units']))]
    allerr = [d for d in ds if day[(d, prov)]['valid'] == 0]
    cov[prov] = {'measuring_days': len(ds), 'first': ds[0] if ds else None, 'last': ds[-1] if ds else None,
                 'complete_days': len(full), 'error_only_days': allerr,
                 'partial_days': [d for d in ds if d not in full and d not in allerr]}
anchors = []; a = ANCHOR0
while a <= END: anchors.append(a.isoformat()); a += dt.timedelta(days=3)
anchor_grid = {d: {p: (lambda x: None if x is None else {'valid': x['valid'], 'error': x['error'], 'units': len(x['units'])})(day.get((d, p)))
                   for p in ('OpenAI', 'Gemini', 'Claude-Web')} for d in anchors}
anchor_full = {p: sum(1 for d in anchors if anchor_grid[d][p] and anchor_grid[d][p]['valid'] >= soll(p, anchor_grid[d][p]['units'])) for p in ('OpenAI', 'Gemini', 'Claude-Web')}
off_anchor = {p: sorted(d for (d, pp) in day if pp == p and d >= ANCHOR0.isoformat() and d not in anchors and day[(d, pp)]['valid'] > 0) for p in ('OpenAI', 'Gemini', 'Claude-Web')}

# Ankertage ohne eigene Messung: naechster Messtag mit Messwert (+/-2 Tage) — Messung neben dem Raster, nicht Ersatz
cw_days = sorted(d for (d, p) in day if p == 'Claude-Web' and day[(d, p)]['valid'] > 0)
def nearest(d0):
    d0 = dt.date.fromisoformat(d0); c = [x for x in cw_days if abs((dt.date.fromisoformat(x) - d0).days) <= 2]
    return min(c, key=lambda x: abs((dt.date.fromisoformat(x) - d0).days)) if c else None
cw_off_grid = {d: nearest(d) for d in anchors if anchor_grid[d]['Claude-Web'] is None}

# ---- 2. Wiederhol-Uebereinstimmung: gleiche Frage, gleiche Einheit, aufeinanderfolgende Messtage mit Messwert
series = C.defaultdict(list)
for (d, prov, unit, q), (err, ts, sc, st) in cells.items():
    if not err: series[(prov, unit, q)].append((d, sc))
agree = C.defaultdict(lambda: [0, 0]); agree_q = C.defaultdict(lambda: [0, 0])
for (prov, unit, q), pts in series.items():
    pts.sort()
    for (d1, s1), (d2, s2) in zip(pts, pts[1:]):
        same = int(s1 == s2); agree[prov][0] += same; agree[prov][1] += 1
        agree_q[(prov, q)][0] += same; agree_q[(prov, q)][1] += 1
retest = {p: {'pairs': n, 'identical': k, 'share_pct': round(100 * k / n, 1) if n else None} for p, (k, n) in sorted(agree.items())}
retest_q = sorted(({'provider': p, 'question_id': q, 'pairs': n, 'share_pct': round(100 * k / n, 1)} for (p, q), (k, n) in agree_q.items() if n), key=lambda x: (x['provider'], x['question_id']))

# ---- 4. Tageswert je Anbieter (eigene Messung, kein Leihwert): Prozent = Score-Summe / (n*3), wie im Worker;
#         Claude-Web = Mittel der Stufen-Prozente. Nur vollstaendige Tage (alle 16 Fragen je Einheit mit Messwert).
unit_day = C.defaultdict(list)
for (d, prov, unit, q), (err, ts, sc, st) in cells.items():
    if not err: unit_day[(d, prov, unit)].append(sc)
level = C.defaultdict(dict); level_partial = C.Counter()
for (d, prov, unit), scs in unit_day.items():
    if len(scs) < N_Q: level_partial[prov] += 1; continue
    level[prov].setdefault(d, []).append(100 * sum(scs) / (len(scs) * 3))
level = {p: {d: round(sum(v) / len(v), 2) for d, v in sorted(dd.items())} for p, dd in level.items()}

# ---- 5. CUSUM (tabellarisch, Methoden-Notiz 01 Abschn. 5.5: h = 5) je Anbieter auf der eigenen Tagesreihe.
#         Referenz = Mittel/SD der ersten 10 vollstaendigen Messtage; k = 0,5 SD, h = 5 SD; nach Alarm Neustart bei 0.
B, K_SD, H_SD = 10, 0.5, 5.0
def cusum(ser):
    days = list(ser); xs = [ser[d] for d in days]
    if len(xs) <= B: return None
    ref = xs[:B]; mu = sum(ref) / B; sd = (sum((x - mu) ** 2 for x in ref) / (B - 1)) ** 0.5
    if sd == 0: return {'baseline_days': days[:B], 'mu': round(mu, 2), 'sd': 0.0, 'note': 'SD der Referenz = 0, Karte nicht definiert'}
    k, h = K_SD * sd, H_SD * sd; sp = sn = 0.0; path = []; alarms = []
    for d, x in zip(days[B:], xs[B:]):
        sp = max(0.0, sp + (x - mu) - k); sn = max(0.0, sn - (x - mu) - k)
        path.append({'d': d, 'x': x, 's_up': round(sp, 2), 's_down': round(sn, 2)})
        if sp > h or sn > h:
            alarms.append({'d': d, 'direction': 'up' if sp > h else 'down', 'x': x}); sp = sn = 0.0
    return {'baseline_days': [days[0], days[B - 1]], 'mu': round(mu, 2), 'sd': round(sd, 2), 'k': round(k, 2), 'h': round(h, 2),
            'n_monitored': len(path), 'alarms': alarms, 'path': path}
cusum_res = {p: cusum(level[p]) for p in ('OpenAI', 'Gemini', 'Claude-Web') if p in level}
# Variante "Neubezug": nach jedem Alarm bilden die naechsten 10 Messtage die neue Referenz. Trennt eine einmalige
# Niveauverschiebung (Sichtbarkeitsanstieg gegen die Mai-Referenz) von weiteren Verschiebungen danach.
def cusum_rebase(ser):
    days = list(ser); i = 0; segs = []
    while len(days) - i > B:
        sub = {d: ser[d] for d in days[i:]}; c = cusum(sub)
        if not c or not c.get('alarms'):
            segs.append({k: c[k] for k in c if k != 'path'} if c else None); break
        a = c['alarms'][0]; segs.append({'baseline_days': c['baseline_days'], 'mu': c['mu'], 'sd': c['sd'], 'first_alarm': a})
        i = days.index(a['d']) + 1
    return segs
cusum_rebase_res = {p: cusum_rebase(level[p]) for p in ('OpenAI', 'Gemini', 'Claude-Web') if p in level}

# ---- 6. intra-Set-Konsistenz (Cronbachs Alpha ueber die 16 Fragen; Fall = Messtag x Einheit mit allen 16 Messwerten),
#         Bootstrap-95-%-Intervall ueber Faelle (2000 Ziehungen, fester Seed).
import random
def alpha(rows):
    kq = len(rows[0]); n = len(rows)
    if n < 3: return None
    def var(v): m = sum(v) / len(v); return sum((x - m) ** 2 for x in v) / (len(v) - 1)
    iv = [var([r[i] for r in rows]) for i in range(kq)]; tv = var([sum(r) for r in rows])
    return None if tv == 0 else kq / (kq - 1) * (1 - sum(iv) / tv)
qids = sorted({q for (_, _, _, q) in cells})
consistency = {}
for prov in ('OpenAI', 'Gemini', 'Claude-Web'):
    byc = C.defaultdict(dict)
    for (d, p, unit, q), (err, ts, sc, st) in cells.items():
        if p == prov and not err: byc[(d, unit)][q] = sc
    rows = [[v[q] for q in qids] for v in byc.values() if len(v) == len(qids)]
    if len(rows) < 3: consistency[prov] = {'cases': len(rows), 'alpha': None}; continue
    a = alpha(rows); rnd = random.Random(20261004); bs = []
    for _ in range(2000):
        b = alpha([rows[rnd.randrange(len(rows))] for _ in rows])
        if b is not None: bs.append(b)
    bs.sort()
    zero_var = [q for i, q in enumerate(qids) if len({r[i] for r in rows}) == 1]
    consistency[prov] = {'cases': len(rows), 'items': len(qids), 'alpha': round(a, 3) if a is not None else None,
                         'ci95': [round(bs[int(.025 * len(bs))], 3), round(bs[int(.975 * len(bs)) - 1], 3)] if bs else None,
                         'zero_variance_items': zero_var}

cat_of = {}
for r in web: cat_of[r['question_id']] = r['category']
consistency_by_cat = {}
for prov in ('OpenAI', 'Gemini', 'Claude-Web'):
    byc = C.defaultdict(dict)
    for (d, p, unit, q), (err, ts, sc, st) in cells.items():
        if p == prov and not err: byc[(d, unit)][q] = sc
    full = [v for v in byc.values() if len(v) == len(qids)]
    for cat in sorted(set(cat_of.values())):
        qs = [q for q in qids if cat_of.get(q) == cat and len({v[q] for v in full}) > 1]
        if len(qs) < 2 or len(full) < 3: consistency_by_cat[f'{prov}|{cat}'] = {'items_with_variance': len(qs), 'alpha': None}; continue
        a = alpha([[v[q] for q in qs] for v in full])
        consistency_by_cat[f'{prov}|{cat}'] = {'items_with_variance': len(qs), 'cases': len(full), 'alpha': round(a, 3) if a is not None else None}

# ---- 7. Eingriffs-Chronik: Vorregistrierungen (data/preregs.json) + datierte Eingriffe/Methodenentscheide aus dem Register
pr = json.load(open(D/'preregs.json'))
chron_prereg = [{'id': x['id'], 'file': x['file'], 'start': x['start'], 'end': x['end'], 'status_as_registered': x['status'],
                 'sampling_end_passed_by_window_end': bool(x['end'] and x['end'] <= END.isoformat())} for x in pr['items']]
chron_events = [{'id': g['id'], 'channel': g['channel'], 'date': g['gap_start'], 'recorded_at': g['recorded_at']}
                for g in gaps if g['channel'].startswith(('intervention', 'method_'))]

# ---- 3. Luecken-Register im Fenster
g_in = [g for g in gaps if g['gap_start'] <= END.isoformat() and g['gap_end'] >= START.isoformat()]

# ======================================================================================================
# Etappe 3 (04.10.2026): Alarm-Abgleich mit dokumentierten Ereignissen, CUSUM gegen rollierende 30-Tage-Basis
# (wie in der Vorregistrierung Q0 festgelegt), Hypothesen H-Q0-INST-01..06, Abdeckungsbilanz Soll/Ist.
# Zusaetzliche Eingaben (data/freeze_extra.json): event_codes.json, wikidata_snapshots.json, kg_snapshots.json,
# bing_daily.json, gsc_daily.json.
# ======================================================================================================
fx = json.load(open(D/'freeze_extra.json'))
EV = json.load(open(D/'event_codes.json'))['events']
PROVS = ('OpenAI', 'Gemini', 'Claude-Web')
def dd(s): return dt.date.fromisoformat(s)

# ---- 8a. Modellwechsel aus den Zeilen selbst (Einheiten-Etiketten je Anbieter): erster Tag eines neuen Etiketts
units_by_day = C.defaultdict(set)
for (d, prov, unit, q), (err, ts, sc, st) in cells.items():
    if not err: units_by_day[(prov, d)].add(unit)
model_changes = []
for prov in PROVS:
    seen = {}; days = sorted(d for (p, d) in units_by_day if p == prov)
    for d in days:
        for u in units_by_day[(prov, d)]: seen.setdefault(u, [d, d]); seen[u][1] = d
    first_day = days[0] if days else None
    for u, (a, b) in sorted(seen.items(), key=lambda kv: kv[1][0]):
        if a != first_day: model_changes.append({'provider': prov, 'unit': u, 'first_day': a, 'last_day': b})
    for u, (a, b) in seen.items():
        if a == first_day and b != days[-1]: model_changes.append({'provider': prov, 'unit': u, 'retired_after': b})
# Etikettwechsel als Ereignis 'M1' (Pegel moeglich), datiert auf den ersten Messtag mit neuem Etikett
ev_all = list(EV)
for i, m in enumerate(x for x in model_changes if 'first_day' in x):
    if not any(e['id'] == 'M-' + m['provider'] + '-' + m['first_day'] for e in ev_all):
        prev_end = max((x['retired_after'] for x in model_changes if x.get('provider') == m['provider'] and 'retired_after' in x and x['retired_after'] < m['first_day']), default=None)
        if prev_end is None: continue      # paralleles Zusatz-Etikett ohne abgeloestes Etikett = kein Wechsel
        ev_all.append({'id': 'M-' + m['provider'] + '-' + m['first_day'], 'from': prev_end, 'to': m['first_day'],
                       'providers': [m['provider']], 'effect': 'level', 'questions': None, 'direction': 'unknown',
                       'de': f"Modell-Etikett wechselt (letzter Messtag altes Etikett {prev_end}, erster Messtag neues Etikett {m['first_day']})",
                       'en': f"model label changes (last day old label {prev_end}, first day new label {m['first_day']})"})

def events_in(prov, a, b):
    return [e for e in ev_all if prov in e['providers'] and e['from'] <= b and e['to'] >= a]

# ---- 8b. Zerlegung einer Pegelverschiebung nach Fragen: Mittel je Frage (ueber Einheiten) Referenz vs. Pruefintervall,
#          Beitrag in Prozentpunkten des Tageswerts = Delta-Mittel * 100 / (16 * 3)
def q_means(prov, days):
    acc = C.defaultdict(list); ds = set(days)
    for (d, p, unit, q), (err, ts, sc, st) in cells.items():
        if p == prov and not err and d in ds and len(unit_day[(d, p, unit)]) >= N_Q: acc[q].append(sc)
    return {q: sum(v) / len(v) for q, v in acc.items()}
def status_shift(prov, days_a, days_b, qs):
    out = {}
    for lab, ds in (('reference', set(days_a)), ('interval', set(days_b))):
        cnt = C.Counter()
        for (d, p, unit, q), (err, ts, sc, st) in cells.items():
            if p == prov and not err and d in ds and q in qs: cnt[st] += 1
        out[lab] = dict(cnt.most_common())
    return out
def decompose(prov, ref_days, int_days):
    a, b = q_means(prov, ref_days), q_means(prov, int_days)
    contrib = sorted(({'question_id': q, 'mean_ref': round(a[q], 2), 'mean_interval': round(b[q], 2),
                       'contribution_pp': round((b[q] - a[q]) * 100 / (N_Q * 3), 2)} for q in a if q in b), key=lambda x: x['contribution_pp'])
    return contrib

def judge(prov, a, b, top_qs, alarm_dir):
    """Ein Alarm gilt als durch ein Ereignis erklaert, wenn ein Ereignis mit moeglicher Pegelwirkung (effect = level) im
    Pruefintervall VOR dem Alarmtag beginnt, die Fragen betrifft, die den Rueckgang tragen (zwei groesste Beitraege), und keine
    entgegengesetzte erwartete Richtung hat. Alle anderen Ereignisse im Intervall werden mit Grund ausgewiesen."""
    out, match = [], []
    for e in events_in(prov, a, b):
        why = None
        if e['effect'] != 'level': why = 'effect_' + e['effect']
        elif e['from'] >= b: why = 'same_day_as_alarm'
        elif e.get('direction', 'unknown') not in ('unknown', alarm_dir): why = 'opposite_direction'
        elif e['questions'] is not None and not set(e['questions']) & set(top_qs): why = 'other_questions'
        if why is None: match.append(e['id'])
        out.append({'id': e['id'], 'effect': e['effect'], 'from': e['from'], 'to': e['to'], 'questions': e['questions'], 'not_matched_because': why, 'de': e['de'], 'en': e['en']})
    verdict = 'explained' if match else ('unexplained_with_events' if out else 'unexplained_no_event')
    return verdict, out, match

days_of = {p: list(level[p]) for p in PROVS}
alarm_check = []
for prov in PROVS:
    for seg in cusum_rebase_res.get(prov, []):
        if not seg or 'first_alarm' not in seg or seg['first_alarm']['direction'] != 'down': continue
        a0, a1 = seg['baseline_days']; al = seg['first_alarm']['d']
        ref_days = [d for d in days_of[prov] if a0 <= d <= a1]
        int_days = [d for d in days_of[prov] if a1 < d <= al]
        dec = decompose(prov, ref_days, int_days); top = [x['question_id'] for x in dec[:2]]
        verdict, evs, matched = judge(prov, (dd(a1) + dt.timedelta(days=1)).isoformat(), al, top, 'down')
        alarm_check.append({'provider': prov, 'alarm_day': al, 'x': seg['first_alarm']['x'], 'reference': [a0, a1], 'ref_mu': seg['mu'], 'ref_sd': seg['sd'],
                            'interval': [(dd(a1) + dt.timedelta(days=1)).isoformat(), al], 'interval_measuring_days': len(int_days),
                            'interval_mean': round(sum(level[prov][d] for d in int_days) / len(int_days), 2) if int_days else None,
                            'interval_minus_ref': round(sum(level[prov][d] for d in int_days) / len(int_days) - seg['mu'], 2) if int_days else None,
                            'top_questions': dec[:3], 'status_shift_top2': status_shift(prov, ref_days, int_days, set(top)),
                            'events_in_interval': evs, 'matched_level_events': matched, 'verdict': verdict})

# ---- 8c. CUSUM gegen rollierende Basis (Vorregistrierung Q0, H-Q0-INST-03): Referenz = Messtage der letzten 30 Kalendertage
#          vor dem Tag (mind. 10), standardisiert; k = 0,5, h = 5 (in SD der jeweiligen Referenz); Neustart nach Alarm.
def cusum_rolling(ser, win=30, min_n=10):
    days = list(ser); sp = sn = 0.0; alarms = []; path = []
    for d in days:
        ref = [ser[x] for x in days if 0 < (dd(d) - dd(x)).days <= win]
        if len(ref) < min_n: continue
        mu = sum(ref) / len(ref); sd = (sum((x - mu) ** 2 for x in ref) / (len(ref) - 1)) ** 0.5
        if sd == 0: path.append({'d': d, 'z': None}); continue
        z = (ser[d] - mu) / sd
        sp = max(0.0, sp + z - K_SD); sn = max(0.0, sn - z - K_SD); path.append({'d': d, 'x': ser[d], 'mu': round(mu, 2), 's_up': round(sp, 2), 's_down': round(sn, 2)})
        if sp > H_SD or sn > H_SD:
            alarms.append({'d': d, 'direction': 'up' if sp > H_SD else 'down', 'x': ser[d], 'ref_mu': round(mu, 2), 'ref_sd': round(sd, 2), 'ref_n': len(ref)}); sp = sn = 0.0
    return {'n_monitored': len([p for p in path if p.get('z', 0) is not None]), 'n_sd_zero_days': len([p for p in path if p.get('z', 1) is None]), 'alarms': alarms, 'path': path}
cusum_roll = {p: cusum_rolling(level[p]) for p in PROVS}
for prov in PROVS:
    for a in cusum_roll[prov]['alarms']:
        win_a = (dd(a['d']) - dt.timedelta(days=7)).isoformat()
        evs = events_in(prov, win_a, a['d']); lvl = [e['id'] for e in evs if e['effect'] == 'level']
        a['events_7d_before'] = [e['id'] for e in evs]; a['level_events_7d_before'] = lvl
        a['model_change_7d_before'] = [e['id'] for e in evs if str(e['id']).startswith('M-')]
model_change_detected = {e['id']: [ (p, a['d']) for p in PROVS for a in cusum_roll[p]['alarms'] if e['id'] in a['model_change_7d_before']]
                         for e in ev_all if str(e['id']).startswith('M-')}

# ---- 8d. Abdeckungsbilanz: Soll = taeglich ab erstem Messtag des Anbieters bis 18.08., danach Ankerraster (alle 3 Tage ab 19.08.).
#          Gueltig = alle 16 Fragen je Einheit mit Messwert (vollstaendig) bzw. mindestens ein Messwert (teilweise).
def soll_days(first):
    out = []; d = dd(first)
    while d < ANCHOR0: out.append(d.isoformat()); d += dt.timedelta(days=1)
    return out + anchors
cov_bal = {}
for prov in PROVS:
    S = soll_days(cov[prov]['first']); rows = []
    for d in S:
        x = day.get((d, prov)); full = bool(x and x['valid'] >= soll(prov, len(x['units'])))
        state = 'complete' if full else ('partial' if x and x['valid'] > 0 else ('error_only' if x else 'none'))
        if state != 'complete':
            ev = [e['id'] for e in EV if prov in e['providers'] and e['effect'] in ('missing', 'timing') and e['from'] <= d <= e['to']]
            rows.append({'d': d, 'state': state, 'register': ev})
    miss = [r for r in rows if r['state'] in ('none', 'error_only')]
    cov_bal[prov] = {'first_day': cov[prov]['first'], 'soll_days': len(S), 'complete': len(S) - len(rows), 'partial': sum(r['state'] == 'partial' for r in rows),
                     'error_only': sum(r['state'] == 'error_only' for r in rows), 'none': sum(r['state'] == 'none' for r in rows),
                     'missing_with_register': sum(1 for r in miss if r['register']), 'missing_without_register': [r['d'] for r in miss if not r['register']], 'missing_without_register_n': sum(1 for r in miss if not r['register']), 'missing_total': len(miss),
                     'complete_pct': round(100 * (len(S) - len(rows)) / len(S), 1), 'not_complete_days': rows,
                     'daily_phase': {'soll': len([d for d in S if d < ANCHOR0.isoformat()]), 'complete': len([d for d in S if d < ANCHOR0.isoformat()]) - len([r for r in rows if r['d'] < ANCHOR0.isoformat()])},
                     'anchor_phase': {'soll': len(anchors), 'complete': len(anchors) - len([r for r in rows if r['d'] >= ANCHOR0.isoformat()])}}

# ---- 8e. Anker-Messflaechen: Wikidata, Google Knowledge Graph, Bing, Search Console
wd = json.load(open(D/'wikidata_snapshots.json')); kg = json.load(open(D/'kg_snapshots.json'))
bing = json.load(open(D/'bing_daily.json')); gsc = json.load(open(D/'gsc_daily.json'))
REG_ANCHOR = {'Q139720807': 'author', 'Q139720798': 'book'}     # in Q0 / Zenodo 10.5281/zenodo.20126038 als Anker benannt
reg_anchor = {q: {'snapshots': sum(1 for r in wd if r['qid'] == q), 'deleted_detected': min((r['d'] for r in wd if r['qid'] == q and r['deleted']), default=None)} for q in REG_ANCHOR}
succ = {}
for q in sorted({r['qid'] for r in wd} - set(REG_ANCHOR)):
    rs = sorted((r for r in wd if r['qid'] == q and not r['deleted']), key=lambda r: r['snapshot_at']); byd = {}
    for r in rs: byd.setdefault(r['d'], r)                                  # erster Schnappschuss je Tag
    ref = set(json.loads(rs[0]['claim_properties'])); covs = []; cc = []
    for d, r in sorted(byd.items()):
        props = set(json.loads(r['claim_properties'])); covs.append(len(props & ref) / len(ref)); cc.append(r['claim_count'])
    mu = sum(covs) / len(covs); sd = (sum((x - mu) ** 2 for x in covs) / (len(covs) - 1)) ** 0.5
    cmu = sum(cc) / len(cc); csd = (sum((x - cmu) ** 2 for x in cc) / (len(cc) - 1)) ** 0.5
    succ[q] = {'entity_type': rs[0]['entity_type'], 'first_day': min(byd), 'last_day': max(byd), 'days': len(byd),
               'reference_properties': len(ref), 'coverage_mean': round(mu, 3), 'coverage_min': round(min(covs), 3), 'coverage_cv': round(sd / mu, 4) if mu else None,
               'coverage_range': round(max(covs) - min(covs), 3), 'claim_count_min': min(cc), 'claim_count_max': max(cc), 'claim_count_cv': round(csd / cmu, 4),
               'consecutive_identical_claim_count_pct': round(100 * sum(1 for x, y in zip(cc, cc[1:]) if x == y) / (len(cc) - 1), 1)}
KGQ = {'Marin T. Kael': 'author', 'Das vierte Feld Marin Kael': 'book', 'Prägungen des Reiches Marin Kael': 'series'}
kg_day = C.defaultdict(dict)
for r in sorted(kg, key=lambda r: r['snapshot_at']):
    kg_day[r['d']].setdefault(KGQ.get(r['query'], r['query']), r)      # erster Schnappschuss je Tag und Anfrage
kg_sum = {}
for k in ('author', 'book', 'series'):
    ds = sorted(d for d in kg_day if k in kg_day[d]); hits = [int(kg_day[d][k]['response_count'] > 0) for d in ds]
    kg_sum[k] = {'days': len(ds), 'hit_days': sum(hits), 'hit_rate': round(sum(hits) / len(hits), 3) if hits else None,
                 'first_hit': next((d for d, h in zip(ds, hits) if h), None),
                 'consecutive_same_hit_pct': round(100 * sum(1 for x, y in zip(hits, hits[1:]) if x == y) / (len(hits) - 1), 1) if len(hits) > 1 else None}
sc = [(d, kg_day[d]['author']['top_match_score']) for d in sorted(kg_day) if 'author' in kg_day[d] and kg_day[d]['author']['top_match_score'] is not None]
def pearson(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys)); sxx = sum((x - mx) ** 2 for x in xs); syy = sum((y - my) ** 2 for y in ys)
    return None if sxx == 0 or syy == 0 else sxy / (sxx * syy) ** 0.5
sc_pairs = [(a[1], b[1]) for a, b in zip(sc, sc[1:]) if (dd(b[0]) - dd(a[0])).days == 1]
kg_score_r = pearson([a for a, b in sc_pairs], [b for a, b in sc_pairs]) if len(sc_pairs) > 2 else None
# Kappa Wikidata <-> KG (binaere Trefferklassifikation, Autor + Buch, Tage mit beiden Messungen)
wd_hit = {}
for q, s in succ.items():
    for r in wd:
        if r['qid'] == q and not r['deleted']: wd_hit[(r['d'], s['entity_type'])] = 1
pairs_k = [(wd_hit.get((d, k), 0), int(kg_day[d][k]['response_count'] > 0)) for d in sorted(kg_day) for k in ('author', 'book')
           if k in kg_day[d] and any(dd(succ_q['first_day']) <= dd(d) for succ_q in succ.values() if succ_q['entity_type'] == k)]
def kappa(pairs):
    n = len(pairs); po = sum(1 for a, b in pairs if a == b) / n
    pa = sum(a for a, _ in pairs) / n; pb = sum(b for _, b in pairs) / n; pe = pa * pb + (1 - pa) * (1 - pb)
    return po, pe, (None if pe == 1 else (po - pe) / (1 - pe))
po, pe, kap = kappa(pairs_k)
bing_m = C.defaultdict(lambda: {'days': 0, 'days_with_status': 0})
for r in bing: m = bing_m[r['d'][:7]]; m['days'] += 1; m['days_with_status'] += int(r['with_status'] > 0)
anchor_surfaces = {'wikidata_registered_anchor': reg_anchor, 'wikidata_successor': succ, 'kg': kg_sum, 'kg_author_score_consecutive_r': round(kg_score_r, 3) if kg_score_r is not None else None,
                   'kg_author_score_pairs': len(sc_pairs), 'kg_author_score_distinct': len({v for _, v in sc}), 'kappa_wd_kg': {'pairs': len(pairs_k), 'p_observed': round(po, 3), 'p_expected': round(pe, 3), 'kappa': round(kap, 3) if kap is not None else None,
                   'wd_hit_share': round(sum(a for a, _ in pairs_k) / len(pairs_k), 3), 'kg_hit_share': round(sum(b for _, b in pairs_k) / len(pairs_k), 3)},
                   'bing_by_month': dict(sorted(bing_m.items())), 'gsc_days': len(gsc)}

# ---- 8f. Wiederhol-Korrelation der Sprachmodell-Proben (H-Q0-INST-02, Einzel-Schnappschuss): Pearson-r ueber Paare
#          (gleiche Frage, gleiche Einheit, Messtage genau 1 Kalendertag auseinander); Bootstrap ueber Tagespaare (Cluster), 2000 Ziehungen.
retest_r = {}
for prov in PROVS:
    byday = C.defaultdict(list)
    for (p, unit, q), pts in series.items():
        if p != prov: continue
        for (d1, s1), (d2, s2) in zip(pts, pts[1:]):
            if (dd(d2) - dd(d1)).days == 1: byday[d1].append((s1, s2))
    allp = [x for v in byday.values() for x in v]; r0 = pearson([a for a, _ in allp], [b for _, b in allp]) if len(allp) > 2 else None
    keys = sorted(byday); rnd = random.Random(20261004); bs = []
    for _ in range(2000):
        smp = [x for k in (keys[rnd.randrange(len(keys))] for _ in keys) for x in byday[k]]
        v = pearson([a for a, _ in smp], [b for _, b in smp])
        if v is not None: bs.append(v)
    bs.sort()
    # Kontrolle: nur Fragen mit Varianz (fragen-zentriert), damit konstante Fragen die Korrelation nicht tragen
    qm = C.defaultdict(list)
    for (p, unit, q), pts in series.items():
        if p == prov: qm[q] += [s for _, s in pts]
    qmean = {q: sum(v) / len(v) for q, v in qm.items()}
    cen = []
    for (p, unit, q), pts in series.items():
        if p != prov: continue
        for (d1, s1), (d2, s2) in zip(pts, pts[1:]):
            if (dd(d2) - dd(d1)).days == 1: cen.append((s1 - qmean[q], s2 - qmean[q]))
    rc = pearson([a for a, _ in cen], [b for _, b in cen]) if len(cen) > 2 else None
    retest_r[prov] = {'pairs': len(allp), 'day_pairs': len(keys), 'r': round(r0, 3) if r0 is not None else None,
                      'ci95': [round(bs[int(.025 * len(bs))], 3), round(bs[int(.975 * len(bs)) - 1], 3)] if bs else None,
                      'r_within_question': round(rc, 3) if rc is not None else None}

# ---- 8g. Hypothesen-Tabelle H-Q0-INST-01..06 (Wortlaut der Schwellen: Vorregistrierung Q0, DOI 10.5281/zenodo.20125967, v1.0)
cons = consistency
ai_band = {p: (cons[p]['alpha'] is not None and 0.5 <= cons[p]['alpha'] < 0.7) for p in PROVS}
hyp = [
 {'id': 'H-Q0-INST-01', 'registered': 'Test-Retest r >= 0,9 fuer API-Flaechen (Wikidata, Google KG, Bing, GSC) auf 24-h-Wiederholungsproben an 14 Tagen',
  'verdict': 'not_testable', 'reason': 'Die 24-h-Wiederholungsproben wurden nicht erhoben; Bing ab 08/2026 ohne Status, GSC-Indexfeld tot; Folgetag-Vergleiche sind kein Retest desselben Zustands',
  'evidence': {'kg_author_consecutive_same_hit_pct': kg_sum['author']['consecutive_same_hit_pct'], 'kg_author_score_consecutive_r': anchor_surfaces['kg_author_score_consecutive_r'],
               'wikidata_consecutive_identical_claim_count_pct': {q: s['consecutive_identical_claim_count_pct'] for q, s in succ.items()},
               'bing_by_month': anchor_surfaces['bing_by_month']}},
 {'id': 'H-Q0-INST-02', 'registered': 'Sprachmodell-Proben: r >= 0,7 mit n = 5 Schnappschuessen je Tag und Median-Aggregation, Vergleich gegen Einzel-Schnappschuss',
  'verdict': 'not_testable', 'reason': 'Mehrfach-Schnappschuesse (n = 5 je Tag) wurden nicht erhoben; nur die Einzel-Schnappschuss-Bedingung ist berechenbar',
  'evidence': {'single_snapshot_r': retest_r, 'identical_score_next_measuring_day': retest}},
 {'id': 'H-Q0-INST-03', 'registered': 'Mindestens ein Modell-Update bei mindestens einer der KI-Flaechen Bing-KI, Gemini, ChatGPT, Google AI Overviews wird mit CUSUM (h = 5, rollierende 30-Tage-Basis) detektiert',
  'verdict': 'not_testable',
  'reason': 'Fuer die registrierten Flaechen fehlen Modellversions-Protokolle (OpenAI, Gemini) bzw. Messungen (Bing-KI, AI Overviews); auf der nicht registrierten Flaeche Claude-Web faellt ein Alarm auf den ersten Messtag nach einem Modell-Etikettwechsel'
            if any(model_change_detected.values()) else 'Fuer die registrierten Flaechen fehlen Modellversions-Protokolle bzw. Messungen; auch auf Claude-Web kein Alarm nach Etikettwechsel',
  'evidence': {'model_changes': model_changes, 'detected_on_unregistered_surface': model_change_detected,
               'rolling_alarms': {p: [{k: a[k] for k in ('d', 'direction', 'level_events_7d_before')} for a in cusum_roll[p]['alarms']] for p in PROVS}}},
 {'id': 'H-Q0-INST-04', 'registered': 'Cronbachs alpha >= 0,7 fuer API-Flaechen; 0,5 <= alpha < 0,7 fuer KI-Flaechen',
  'verdict': 'not_confirmed' if not all(ai_band.values()) else 'confirmed',
  'reason': 'API-Teil nicht pruefbar (keine Fragen-Sets auf API-Flaechen); KI-Teil: Punktschaetzung im Band bei ' + ', '.join(p for p in PROVS if ai_band[p]) + '; ausserhalb: ' + ', '.join(p for p in PROVS if not ai_band[p]),
  'evidence': {p: {'alpha': cons[p]['alpha'], 'ci95': cons[p]['ci95'], 'cases': cons[p]['cases'], 'zero_variance_items': len(cons[p]['zero_variance_items']), 'in_band_point': ai_band[p]} for p in PROVS}},
 {'id': 'H-Q0-INST-05', 'registered': 'Wikidata-Abdeckung des Person+Werk-Clusters bleibt ueber das Fenster stabil > 0,85 (Volatilitaet <= 0,1)',
  'verdict': 'not_confirmed', 'reason': 'Beide registrierten Anker-Items wurden im Fenster geloescht; die Nachfolge-Items sind ab ' + min(s['first_day'] for s in succ.values()) + ' stabil, decken das Fenster aber nicht ab',
  'evidence': {'registered_anchor': reg_anchor, 'successor': succ}},
 {'id': 'H-Q0-INST-06', 'registered': 'Cohens kappa >= 0,8 zwischen Wikidata und Google KG (binaere Trefferklassifikation)',
  'verdict': 'not_confirmed' if (kap is not None and kap < 0.8) else ('not_testable' if kap is None else 'confirmed'),
  'reason': 'kappa unter 0,5 (H0-Bereich); Wikidata fuehrt Autor und Buch an jedem Tag, der Knowledge Graph nur den Autor',
  'evidence': anchor_surfaces['kappa_wd_kg']},
]
cells_valid = C.Counter(p for (d, p, u, q), v in cells.items() if not v[0]); cells_err = C.Counter(p for (d, p, u, q), v in cells.items() if v[0])
summary = {'cells_valid': dict(cells_valid), 'cells_error': dict(cells_err), 'cells_valid_total': sum(cells_valid.values()),
           'raw_rows_used': {'web_rows_headline_providers': sum(1 for r in web if r['llm'] in WEB), 'claude_web_rows_tiers': sum(1 for r in cw if r['model'] not in CW_FOREIGN)},
           'level_days': {p: len(level[p]) for p in PROVS},
           'zero_variance_items': {p: len(consistency[p]['zero_variance_items']) for p in PROVS},
           'cusum_fixed_alarms': {p: {'up': sum(a['direction'] == 'up' for a in cusum_res[p]['alarms']), 'down': sum(a['direction'] == 'down' for a in cusum_res[p]['alarms'])} for p in PROVS},
           'cusum_rolling_alarms': {p: {'up': sum(a['direction'] == 'up' for a in cusum_roll[p]['alarms']), 'down': sum(a['direction'] == 'down' for a in cusum_roll[p]['alarms'])} for p in PROVS},
           'rebase_down_alarms': len(alarm_check), 'rebase_down_explained': sum(a['verdict'] == 'explained' for a in alarm_check),
           'retest_by_question_range': {p: [min(x['share_pct'] for x in retest_q if x['provider'] == p), max(x['share_pct'] for x in retest_q if x['provider'] == p)] for p in PROVS},
           'retest_questions_100pct': {p: sum(1 for x in retest_q if x['provider'] == p and x['share_pct'] == 100.0) for p in PROVS},
           'retest_varying_questions': {p: (lambda xs: {'questions': len(xs), 'pairs': sum(n for n, k in xs), 'share_pct': round(100 * sum(k for n, k in xs) / sum(n for n, k in xs), 1)})(
               [(n, k) for (pp, q), (k, n) in agree_q.items() if pp == p and q not in consistency[p]['zero_variance_items']]) for p in PROVS},
           'prereg_end_passed': [x['id'] for x in chron_prereg if x['sampling_end_passed_by_window_end']],
           'gaps_in_window_n': len(g_in)}
day_state = {p: {d: ('complete' if x['valid'] >= soll(p, len(x['units'])) else ('partial' if x['valid'] > 0 else 'error_only'))
                 for (d, pp), x in sorted(day.items()) if pp == p} for p in PROVS}
stage3 = {'summary': summary, 'day_state': day_state, 'model_changes': model_changes, 'alarm_check_rebase_down': alarm_check, 'cusum_rolling30': {p: {k: v for k, v in c.items() if k != 'path'} for p, c in cusum_roll.items()},
          'cusum_rolling30_path': {p: c['path'] for p, c in cusum_roll.items()}, 'model_change_detected': model_change_detected,
          'coverage_balance': cov_bal, 'anchor_surfaces': anchor_surfaces, 'retest_r_single_snapshot': retest_r, 'hypotheses_q0': hyp,
          'multiple_testing': 'BH-FDR (q = 0,05) registriert; nicht angewandt, weil keine der sechs Pruefungen einen p-Wert liefert (Schwellen-Vergleiche, deskriptiv)',
          'freeze_extra': fx}

stage3['dedupe'] = {'rule': 'Fehlerzeile verliert; sonst naechster Zeitstempel zum planmaessigen Laufzeitpunkt (run_at des fruehesten cron-Laufs des Tages bzw. run_ts des fruehesten Claude-Web-Laufs); Gleichstand: frueher, dann Abzugsreihenfolge',
                     'rows_dropped': dedupe_stats['dropped'], 'planned_time_source_day_provider': dict(planned_src)}
res = {'stand': 'Etappe 3 (04.10.2026): Abdeckung, Wiederhol-Uebereinstimmung, Tageswert, CUSUM, intra-Set-Konsistenz, Eingriffs-Chronik, Alarm-Abgleich, Hypothesen Q0, Abdeckungsbilanz',
       'stage3': stage3,
       'freeze': freeze, 'rules': {'one_row_per': '(UTC-Tag, Anbieter-Einheit, Frage); Fehlerzeile verliert, sonst naechster Zeitstempel zum planmaessigen Laufzeitpunkt (Kanon 04.09.2026)',
                                   'claude_web_units': 'Web-Tiers ohne Fremdmodelle im Werkzeug', 'retest': 'identischer Rubrik-Score am naechsten Messtag mit Messwert',
                                   'anchor_grid': 'alle 3 Tage ab 2026-08-19', 'questions': N_Q},
       'coverage': cov, 'anchors': anchors, 'anchor_grid': anchor_grid, 'anchor_complete': anchor_full,
       'off_anchor_measuring_days': {p: len(v) for p, v in off_anchor.items()},
       'claude_web_anchor_missing_nearest': cw_off_grid,
       'retest': retest, 'retest_by_question': retest_q,
       'level_by_day': level, 'level_partial_unit_days_excluded': dict(level_partial),
       'cusum': cusum_res, 'cusum_rebase': cusum_rebase_res, 'consistency_by_category': consistency_by_cat, 'cusum_rule': {'reference_days': B, 'k_sd': K_SD, 'h_sd': H_SD, 'restart_after_alarm': True},
       'consistency': consistency, 'prereg_chronicle': chron_prereg, 'dated_events': chron_events, 'preregs_frozen_at': pr['frozen_at_utc'],
       'gaps_in_window': [{'id': g['id'], 'channel': g['channel'], 'from': g['gap_start'], 'to': g['gap_end']} for g in g_in]}
json.dump(res, open(D/'results.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ('anchor_complete', 'off_anchor_measuring_days', 'claude_web_anchor_missing_nearest', 'retest')}, ensure_ascii=False))
print(json.dumps({'cusum': {p: (c and {k: c[k] for k in c if k != 'path'}) for p, c in cusum_res.items()}, 'cusum_rebase': cusum_rebase_res, 'consistency_by_category': consistency_by_cat, 'consistency': consistency, 'prereg_end_passed': [x['id'] for x in chron_prereg if x['sampling_end_passed_by_window_end']]}, ensure_ascii=False))
print({p: {k: (v if not isinstance(v, list) else len(v)) for k, v in c.items()} for p, c in cov.items()}); print('gaps', len(g_in))
