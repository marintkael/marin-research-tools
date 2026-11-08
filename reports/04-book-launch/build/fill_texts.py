#!/usr/bin/env python3
"""Füllt REPORT_DE.md / REPORT_EN.md aus den Vorlagen (*.vorlage.md).

Zahlenquellen (alle von build/analyze.py in einem Lauf geschrieben):
  data/results.json                  Hauptanalyse, kompakte Sensitivitäten (sensitivitaeten), Erweiterung (extension_0811),
                                     Zusatzangaben (zusatzangaben, nicht vorregistriert)
  data/results_regeln_nachtrag.json  Sensitivität Bewertungsregeln vom 02.11.2026 (Eintrag 71)
  data/results_erweiterung_0811.json Erweiterung bis Ankertag 08.11.2026 (Eintrag 83, nicht vorregistriert): Abzug und Register
Dazu Eingaben für Zuordnungen und Belegprüfungen: data/baseline_freeze/web_rows.corrections.json (Grundlinien-Korrekturen je
Ankertag), data/scorer_nachtrag_2026-11-02.json (Rückstellungen je Tag), data/leere_antworten.json (leere Antworten je Tag).
Jede Ersetzung prüft ihren Anker (genau ein Treffer), sonst Abbruch; feste Angaben der Vorlagen werden gegen die Quellen
geprüft (assert). Idempotent: schreibt immer aus der Vorlage.
"""
import io, json, os, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding='utf-8'))
D = load('data/results.json')
S71 = load('data/results_regeln_nachtrag.json')
XF = load('data/results_erweiterung_0811.json')
CORR = load('data/baseline_freeze/web_rows.corrections.json')
SN = load('data/scorer_nachtrag_2026-11-02.json')
LEER = load('data/leere_antworten.json')

assert D['phase'] == 'beobachtung_laufend', D['phase']
for ch, v in D['effects']['primary'].items():
    assert v['status'] == 'abgeschlossen', ch

CH = ['total', 'direct', 'longtail', 'discovery', 'recommend_gr']
P = ['OpenAI', 'Gemini']
E = D['effects']['primary']; ES = D['effects']['sensitivity']; E71 = S71['effects']['primary']
B = D['baseline']['baseline']; MDE = D['baseline']['mde_pp_assuming_10_effect_days']
DRI = D['baseline']['drift_implied_diff_pp']; TM = D['timing']; COV = D['coverage']
CL = D['claude']; FZ = D['freeze']['post']['effect_freeze']; INTG = D['freeze']['integrity']
PRE = D['preregistration']; EW = D['effect_window']['by_metric']; ZU = D['zusatzangaben']
SENS = D['sensitivitaeten']; LU = SENS['leere_antworten']['luecke']; FE = SENS['leere_antworten']['fehler']
O4 = SENS['ohne_aenderung4']; R71 = SENS['regeln_nachtrag']; EXT = D['extension_0811']
EXE = EXT['effects_primary']; EXT_T = EXT['timing']; EXC = EXT['coverage']
XFZ = XF['freeze']['post']['extension_freeze_0811']
REG = {int(g['id']): g for g in XF['data_gaps']}          # Register im Abzug der Erweiterung (bis Eintrag 83)
SR = D['freeze']['scorer_rules']
# Prüfung des Startwerts (build/startwert_pruefung.py, zusätzlich, nicht vorregistriert): weitere Startwerte für das
# Bootstrap-Intervall der Kopfzahl; der vorregistrierte Startwert muss results.json exakt reproduzieren
SW = load('data/results_startwerte.json')
assert SW['startwert_vorregistriert'] == D['definitions']['seed'] and SW['n_boot'] == D['definitions']['n_boot']
assert all(SW['vorregistriert'][k] == D['effects']['primary']['total'][k] for k in ('detrended', 'ci95_detrended', 'raw', 'ci95_raw'))
assert SW['bereinigt_untergrenze']['n_ueber_null'] == 0 and SW['bereinigt_obergrenze']['n_unter_null'] == 0
assert len(SW['laeufe']) == SW['n_weitere'] + 1
SW_K, SW_N = SW['unbereinigt_untergrenze']['n_ueber_null'], SW['n_weitere']
assert 0 < SW_K < SW_N, 'Satz zur Startwert-Prüfung setzt voraus, dass die Untergrenze je nach Startwert über oder unter null liegt'

MON_DE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
MON_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
WORD = {'de': {1: 'eine', 2: 'zwei', 3: 'drei', 4: 'vier', 5: 'fünf', 6: 'sechs', 7: 'sieben', 8: 'acht', 9: 'neun', 10: 'zehn', 11: 'elf', 12: 'zwölf'},
        'en': {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven', 12: 'twelve'}}

def num(x, lang, nd=2, sign=False):
    s = f'{abs(x):,.{nd}f}'
    if lang == 'de':
        s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    if x < 0 and round(abs(x), nd) != 0:
        s = '−' + s
    elif sign and round(x, nd) != 0:
        s = '+' + s
    return s

def ci(v, lang, table=False):
    a, b = num(v[0], lang), num(v[1], lang)
    if table:
        return f'[{a}; {b}]' if lang == 'de' else f'[{a}, {b}]'
    return f'{a} bis {b}' if lang == 'de' else f'{a} to {b}'

def dt(s, lang, year=False):
    d = date.fromisoformat(s)
    if lang == 'de':
        return f'{d.day}. {MON_DE[d.month-1]}' + (f' {d.year}' if year else '')
    return f'{d.day} {MON_EN[d.month-1]}' + (f' {d.year}' if year else '')

def dshort(s):
    d = date.fromisoformat(s); return f'{d.day:02d}.{d.month:02d}.'

def mean(xs):
    return sum(xs) / len(xs)

def excl0(c):
    return c is not None and (c[0] > 0 or c[1] < 0)

# Wirkungsfenster je Ankertag
EFF = [r for r in D['anchor_table'] if r['window'] == 'effect']
BOTH = [r for r in EFF if r['basis'] == 'beide']
ONLY = [r for r in EFF if r['basis'] != 'beide']
assert all(r['basis'] == 'nur_openai' for r in ONLY), [r['basis'] for r in ONLY]
def pvals(p, ch):
    return [r[p][ch] for r in EFF if r[p].get('state') == 'vollstaendig']
H_BOTH = [r['headline']['total'] for r in BOTH]
n_eff = {p: COV['effect'][p]['complete'] for p in P}
gem_missing = COV['effect']['Gemini']['not_complete']
assert COV['effect']['OpenAI']['not_complete'] == []

# Register-IDs der Gemini-Ausfälle im Wirkungsfenster
gaps = {str(g['id']): g for g in D['data_gaps']}
gem_ids = sorted((int(g['id']) for g in D['data_gaps'] if g['channel'] == 'gemini' and g['gap_start'] in gem_missing))
assert len(gem_ids) == len(gem_missing), (gem_ids, gem_missing)
for need in ('41', '42', '43', '44', '45', '50', '66', '68', '70', '71', '72'):
    assert need in gaps, need
for i, chn in {12: 'intervention_book_launch', 18: 'intervention_book_launch', 36: 'intervention_book_launch_amendment',
               38: 'intervention_book_launch_amendment2', 39: 'intervention_book_launch_amendment3', 41: 'method_claude_modelle',
               42: 'method_scorer_nichtfund', 43: 'method_scorer_kollision_pauline', 44: 'method_openai_nachholung',
               50: 'method_scorer_buchtitel', 66: 'method_leere_antwort', 70: 'method_leere_antwort_wiederholung',
               71: 'method_scorer_regeln_1102', 72: 'method_claude_websuche', 80: 'gemini', 81: 'openai_search',
               82: 'method_gemini_nachholung', 83: 'intervention_book_launch_extension'}.items():
    assert REG[i]['channel'] == chn, (i, REG[i]['channel'])
for i in gem_ids:
    assert REG[i]['channel'] == 'gemini'

# ---------- Belegprüfung fester Angaben der Vorlagen (Abschnitte 1, 2, 3 und 10) ----------
assert PRE['version'] == 'v1.4 · 2026-10-15', PRE['version']
assert PRE['register_entries'] == [12, 18, 36, 38, 39, 50], PRE['register_entries']
assert [(a['nr'], a['version'], a['fixed'], a['register_entry'], a['before_event']) for a in PRE['amendments']] == [
    (1, 'v1.1', '2026-10-07', 36, True), (2, 'v1.2', '2026-10-07', 38, True), (3, 'v1.3', '2026-10-07', 39, True), (4, 'v1.4', '2026-10-15', 50, False)]
assert (PRE['register_recorded_at']['12'], PRE['register_recorded_at']['18'], PRE['register_recorded_at']['50']) == ('2026-09-05', '2026-09-23', '2026-10-15')
assert REG[12]['recorded_at'][:10] == '2026-09-05' and REG[18]['recorded_at'][:10] == '2026-09-23'
assert sorted(PRE['method_addenda_register_entries']) == ['66', '71', '83']
A4 = O4['geaenderte_zeilen']
assert len(A4) == 2 and all(r['d'] == '2026-10-12' and r['question_id'] == 'L1' and r['score_mit_aenderung4'] == 2 and r['score_ohne'] == 0 for r in A4)
assert sorted(r['who'] for r in A4) == ['claude-opus-5-5', 'gemini']
assert [r['d'] for r in EFF if r['d'] <= '2026-10-15'] == ['2026-10-09', '2026-10-12', '2026-10-15']
DEF = D['definitions']
assert len(DEF['channels']['discovery']) == 10 and DEF['channels']['recommend_gr'] == ['GR1', 'GR2', 'GR3', 'GR4', 'GR5', 'GR6']
assert [round(DEF['sd_floor_pp'][k], 2) for k in CH] == [1.04, 5.56, 8.33, 1.67, 2.78]
assert round(B['hit_direct']['provider_balanced_mean'], 1) == 92.2 and round(100 - B['hit_direct']['provider_balanced_mean'], 1) == 7.8
# Empfehlungs-Kanal aus zehn Fragen = 0,6 × GR1–GR6 an jedem Anbieter-Tag, in Punkten und Trefferquote (G1, G2, C1, C2 ohne Punkte)
rel_rows = [r[p] for r in D['anchor_table'] + XF['anchor_table'] for p in P if r[p].get('state') == 'vollstaendig']
assert len(rel_rows) > 40
assert all(abs(x['discovery'] - 0.6 * x['recommend_gr']) <= 0.02 and abs(x['hit_discovery'] - 0.6 * x['hit_recommend_gr']) <= 0.02 for x in rel_rows)

# Grundlinien-Korrekturen je Ankertag
anch = {r['d']: r['window'] for r in D['anchor_table']}
corr_base = sorted({c['d'] for c in CORR if anch.get(c['d']) == 'baseline'})
corr_ref = sorted({c['d'] for c in CORR if anch.get(c['d']) == 'cusum_ref'})
corr_base_n = {d: sum(1 for c in CORR if c['d'] == d) for d in corr_base}
assert len(CORR) == D['freeze']['baseline_corrections_applied']['baseline_freeze/web_rows']

# Rückstellungen auf vorregistrierte Bewertungsregeln (Eintrag 71, Nachtrag 08.11.)
win_old = [e for e in SN['window'] if 'd' not in e]
win_0511 = [e for e in SN['window'] if e.get('d') == '2026-11-05']
win_0811 = [e for e in SN['window'] if e.get('fenster') == 'erweiterung_0811']
assert len(win_old) + len(win_0511) == SR['overrides'] == SR['nachtrag_eintraege']['window_je_fenster']['wirkung'] == O4['scorer_overrides'] == LU['scorer_overrides']
assert len(win_0811) == SR['nachtrag_eintraege']['window_je_fenster']['erweiterung_0811'] and SR['overrides'] + len(win_0811) == EXT['scorer_overrides']
assert len(win_0511) == 1 and win_0511[0]['table'] == 'claude_web_rows'          # am 05.11. weicht keine OpenAI-Antwort ab
g0511 = SN['nachtrag_2026-11-08']['geprueft']['2026-11-05']
assert g0511['gemini'] == 0 and g0511['openai_search'] + g0511['claude'] == 64
assert SR['nachtrag_eintraege']['baseline_auszug_500_zeichen'] == R71['scorer_overrides'] == 41

# Claude
CDAYS = CL['days']; CB = CL['baseline_0710']
c_anchor = [k for k, v in CDAYS.items() if v.get('kind') == 'ankertag']
c_tot = [CDAYS[k]['provider_mean']['total'] for k in c_anchor]
c_dir = [CDAYS[k]['provider_mean']['direct'] for k in c_anchor]
c_lt_pos = [k for k in c_anchor if CDAYS[k]['provider_mean']['longtail'] > 0]
c_disc_pos = [k for k in c_anchor if CDAYS[k]['provider_mean']['discovery'] > 0]
assert all(CDAYS[k]['n_valid'] == 48 for k in CDAYS)
last_c = c_anchor[-1]; DD = CL['descriptive_diff_to_baseline'][last_c]

def model_of(day, fam):
    return [m for m in CDAYS[day]['by_model'] if fam in m][0]

def first(ch, key):
    v = TM.get(ch, {}).get(key)
    return v

LBL = {'de': {'total': 'Kopfzahl', 'direct': 'Direkt', 'longtail': 'Saga-Wissen', 'discovery': 'Empfehlung', 'recommend_gr': 'davon GR1–GR6', 'hit_total': 'Trefferquote alle Fragen'},
       'en': {'total': 'Headline', 'direct': 'Direct', 'longtail': 'Saga knowledge', 'discovery': 'Recommendation', 'recommend_gr': 'of which GR1–GR6', 'hit_total': 'Hit rate, all questions'}}
TXT = {'de': {'total': 'Kopfzahl', 'direct': 'Direkt', 'longtail': 'Saga-Wissen', 'discovery': 'Empfehlung', 'recommend_gr': 'GR1 bis GR6'},
       'en': {'total': 'headline', 'direct': 'Direct', 'longtail': 'Saga knowledge', 'discovery': 'Recommendation', 'recommend_gr': 'GR1 to GR6'}}
HTXT = {'de': {'total': 'alle Fragen', 'direct': 'Direkt', 'longtail': 'Saga-Wissen', 'discovery': 'Empfehlung', 'recommend_gr': 'GR1 bis GR6'},
        'en': {'total': 'all questions', 'direct': 'Direct', 'longtail': 'Saga knowledge', 'discovery': 'Recommendation', 'recommend_gr': 'GR1 to GR6'}}

def table4(lang):
    rows = []
    none = 'keiner' if lang == 'de' else 'none'
    for ch in CH:
        v = E[ch]
        fa = first(ch, 'first_up_alarm') or first(ch, 'first_down_alarm')
        fp = first(ch, 'first_above_pi95')
        fa_s = (dshort(fa) if lang == 'de' else fa) if fa else none
        fp_s = (dshort(fp) if lang == 'de' else fp) if fp else none
        rows.append(f"| {LBL[lang][ch]} | {num(v['detrended'], lang, sign=True)} | {ci(v['ci95_detrended'], lang, True)} | {num(v['raw'], lang, sign=True)} | {fa_s} | {fp_s} |")
    return rows

def table5(lang):
    hdr = ('| Tag | Claude Kopfzahl | Direkt | Saga-Wissen | Empfehlung | Opus | Sonnet | Haiku |' if lang == 'de'
           else '| Day | Claude headline | Direct | Saga knowledge | Recommendation | Opus | Sonnet | Haiku |')
    out = [hdr, '|---|---|---|---|---|---|---|---|']
    for k, v in CDAYS.items():
        pm = v['provider_mean']; bm = v['by_model']
        lab = (dshort(k) if lang == 'de' else k) + ((' (Grundlinie)' if lang == 'de' else ' (baseline)') if v['kind'] == 'grundlinie' else '')
        out.append(f"| {lab} | {num(pm['total'], lang)} | {num(pm['direct'], lang)} | {num(pm['longtail'], lang)} | {num(pm['discovery'], lang)} | "
                   f"{num(bm[model_of(k, 'opus')]['total'], lang)} | {num(bm[model_of(k, 'sonnet')]['total'], lang)} | {num(bm[model_of(k, 'haiku')]['total'], lang)} |")
    return out

def table6(lang):
    de = lang == 'de'; none = 'keiner' if de else 'none'
    hdr = ('| Kanal | Hauptanalyse | Erweiterung | 95-%-Intervall | unbereinigt | 95-%-Intervall unbereinigt | erster Alarm |' if de
           else '| Channel | Main analysis | Extension | 95 % interval | unadjusted | 95 % interval unadjusted | first alarm |')
    out = [hdr, '|---|---|---|---|---|---|---|']
    for ch in CH + ['hit_total']:
        v = EXE[ch]; vh = EXT['vergleich_hauptanalyse'][ch]
        assert vh['haupt'] == E[ch]['detrended'] and vh['erweiterung'] == v['detrended'], ch
        fa = EXT_T[ch]['first_up_alarm'] or EXT_T[ch]['first_down_alarm']
        fa_s = (dshort(fa) if de else fa) if fa else none
        out.append(f"| {LBL[lang][ch]} | {num(vh['haupt'], lang, sign=True)} | {num(v['detrended'], lang, sign=True)} | {ci(v['ci95_detrended'], lang, True)} | "
                   f"{num(v['raw'], lang, sign=True)} | {ci(v['ci95_raw'], lang, True)} | {fa_s} |")
    return out

def dmon_en(s):
    d = date.fromisoformat(s); return f'{d.day} {MON_EN[d.month-1][:3]}'

def table7(lang):
    de = lang == 'de'
    gi = ', '.join(str(i) for i in gem_ids)
    E43 = SR['eintrag43_enger_umgesetzt']; e43w = E43['je_fenster'].get('wirkung', 0); e43x = e43w + E43['je_fenster'].get('erweiterung_0811', 0)
    if de:
        rows = [('Änderungen 1 bis 3: Panel OpenAI und Gemini, Claude beschreibend, Sensitivitäts-Grundlinie, Trefferquote, Einzelheiten der Auswertung, Direkt-Regel', '07.10., vor dem Ereignis', '36, 38, 39', 'Teil der Vorregistrierung (Abschnitte 1 und 3)'),
                ('Festlegungen: Claude mit drei Modellfamilien, ehrlicher Nichtfund', '07.10., vor dem Ereignis', '41, 42', 'in Grundlinie und Wirkungsfenster gleich angewendet (Abschnitte 1 und 2)'),
                ('Namens-Kollision mit Pauline Kael; der Bewerter in der vorregistrierten Fassung setzt den Teil zu echten Angaben über den Autor enger um als der Wortlaut', '07.10., vor dem Ereignis; als Fehler erkannt am 02.11.', '43, 71', f"vor dem Ereignis eine Gemini-Antwort nach dem Wortlaut nachbewertet; im Wirkungsfenster folgt die Hauptanalyse dem Bewerter: {e43w} Claude-Antworten (in der Erweiterung {e43x}) mit null Punkten, OpenAI und Gemini nicht betroffen; Claude-Werte nach dem Wortlaut beschreibend (Abschnitte 1 und 6)"),
                ('Nachhol-Regel für OpenAI', '07.10., vor dem Ereignis', '44', 'nur im Wirkungsfenster wirksam (02.11.; in der Erweiterung auch 08.11.), die Grundlinie enthält keine Nachmessung (Abschnitt 2)'),
                ('Empfehlungs-Kanal mit zehn Fragen statt GR1 bis GR6', '07.10., im Auswertungscode, nicht registriert', '–', 'GR1 bis GR6 überall mitberichtet, gleiches Urteil (Abschnitte 2 und 5)'),
                ('Änderung 4: Buch- oder Reihentitel als Anker', '15.10., im Wirkungsfenster', '50', 'Sensitivität ohne Änderung 4 (Abschnitt 7)'),
                ('Leere Antworten als Fehlmessung, Wiederholung im selben Lauf', '01.11. und 02.11., im Wirkungsfenster', '66, 70', 'vorher null Punkte; Sensitivität als Lücke und als Fehlmessung (Abschnitt 7)'),
                ('Bewertungsregeln vom 2. November', '02.11., im Wirkungsfenster', '71', f"Hauptanalyse mit den vorregistrierten Regeln, {SR['overrides']} Antworten zurückgesetzt; Sensitivität (Abschnitt 7)"),
                (f"Gemini fehlt an {len(gem_missing)} Wirkungs-Ankertagen", f"{dshort(gem_missing[0])} bis {dshort(gem_missing[-1])}", gi, 'nicht nachgemessen; Zusatzangabe mit den Tagen beider Anbieter (Abschnitt 7)'),
                ('Nachhol-Regel für Gemini', '08.11., nach dem Wirkungsfenster', '82', 'nur in der Erweiterung wirksam (Abschnitt 7)'),
                ('Erweiterung bis zum Ankertag 8. November', '08.11., nach dem Wirkungsfenster', '83', 'eigener Unterabschnitt, nicht vorregistriert, ohne Einfluss auf die Entscheidung (Abschnitt 7)'),
                ('Erfassungsdaten der Einträge 12 und 18', 'Vermerk vom 08.11.', '12, 18', 'Daten nach dem Register (Abschnitt 1)')]
        out = ['| Abweichung | festgelegt | Eintrag | Behandlung |', '|---|---|---|---|']
    else:
        rows = [('Amendments 1 to 3: panel OpenAI and Gemini, Claude descriptive, sensitivity baseline, hit rate, analysis details, Direct rule', '7 Oct, before the event', '36, 38, 39', 'part of the pre-registration (sections 1 and 3)'),
                ('Rules: Claude with three model families, honest non-result', '7 Oct, before the event', '41, 42', 'applied equally to baseline and effect window (sections 1 and 2)'),
                ('Name collision with Pauline Kael; the scorer in its pre-registered version implements the part on genuine statements about the author more narrowly than the wording', '7 Oct, before the event; identified as a fault on 2 Nov', '43, 71', f"before the event one Gemini answer re-scored according to the wording; in the effect window the main analysis follows the scorer: {e43w} Claude answers ({e43x} in the extension) with zero points, OpenAI and Gemini not affected; Claude values under the wording descriptive (sections 1 and 6)"),
                ('Catch-up rule for OpenAI', '7 Oct, before the event', '44', 'effective only in the effect window (2 Nov; in the extension also 8 Nov), the baseline contains no re-measurement (section 2)'),
                ('Recommendation channel with ten questions instead of GR1 to GR6', '7 Oct, in the analysis code, not registered', '–', 'GR1 to GR6 reported throughout, same verdict (sections 2 and 5)'),
                ('Amendment 4: book or series title as anchor', '15 Oct, during the effect window', '50', 'sensitivity without amendment 4 (section 7)'),
                ('Empty answers as failed measurements, repeat within the same run', '1 Nov and 2 Nov, during the effect window', '66, 70', 'zero points before; sensitivity as gaps and as failed measurements (section 7)'),
                ('Scoring rules of 2 November', '2 Nov, during the effect window', '71', f"main analysis under the pre-registered rules, {SR['overrides']} answers reset; sensitivity (section 7)"),
                (f"Gemini missing on {len(gem_missing)} effect anchor days", f"{dmon_en(gem_missing[0])} to {dmon_en(gem_missing[-1])}", gi, 'not re-measured; additional figure for the days with both providers (section 7)'),
                ('Catch-up rule for Gemini', '8 Nov, after the effect window', '82', 'effective only in the extension (section 7)'),
                ('Extension to anchor day 8 November', '8 Nov, after the effect window', '83', 'separate subsection, not pre-registered, no influence on the decision (section 7)'),
                ('Registration dates of entries 12 and 18', 'note of 8 Nov', '12, 18', 'dates as in the register (section 1)')]
        out = ['| Deviation | fixed | Entry | Handling |', '|---|---|---|---|']
    for r in rows:
        out.append('| ' + ' | '.join(r) + ' |')
    return out

def rng(xs, lang):
    return f'{num(min(xs), lang)} {"bis" if lang == "de" else "to"} {num(max(xs), lang)}'

def ids(lst, lang):
    s = [str(i) for i in lst]
    return (', '.join(s[:-1]) + (' und ' if lang == 'de' else ' and ') + s[-1]) if len(s) > 1 else s[0]

def build(lang):
    de = lang == 'de'
    W = WORD[lang]
    src = io.open(os.path.join(ROOT, f'REPORT_{lang.upper()}.vorlage.md'), encoding='utf-8').read()
    R = []
    def rep(old, new):
        R.append((old, new))
    n = lambda x, **k: num(x, lang, **k)
    c = lambda v, **k: ci(v, lang, **k)
    pc = lambda v: f"{n(v['detrended'], sign=True)} ({c(v['ci95_detrended'])})"          # Schätzwert mit Intervall
    pr_ = lambda v: f"{n(v['raw'], sign=True)} ({c(v['ci95_raw'])})"                    # unbereinigt mit Intervall
    t, bal = B['total'], B['total']['provider_balanced_mean']
    oa, ge = t['providers']['OpenAI'], t['providers']['Gemini']
    EWt = EW['total']; ewo, ewg = EWt['providers']['OpenAI'], EWt['providers']['Gemini']
    m_both = mean(H_BOTH)
    eff_first, eff_last = BOTH[0]['d'], BOTH[-1]['d']
    only_first = ONLY[0]['d']
    s71 = E71['total']
    gem_list = ids(gem_ids, lang)
    ep = E['total']; op, gp = ep['providers']['OpenAI'], ep['providers']['Gemini']
    MZ = ZU['mde_mit_drift_unsicherheit']
    alarm_day = TM['total']['first_up_alarm']

    # Belegprüfungen für Zusammenfassung und Abschnitt 4
    assert ewo['n_anchor_days'] == n_eff['OpenAI'] and ewg['n_anchor_days'] == n_eff['Gemini']
    assert abs((EWt['provider_balanced_mean'] - bal) - ep['raw']) <= 0.011            # gleiche Basis: Abstand = unbereinigte Differenz
    assert DRI['total']['basis'] == 'gemessene Wirkungstage je Anbieter' and DRI['total']['n_effect_days'] == n_eff
    assert abs((ep['raw'] - ep['detrended']) - DRI['total']['mean']) <= 0.02
    for p in P:
        assert abs((ep['providers'][p]['raw'] - ep['providers'][p]['detrended']) - DRI['total']['providers'][p]) <= 0.02, p
    assert ep['ci95_raw'][0] > 0 and O4['effects_primary']['total']['ci95_raw'][0] < 0 < O4['effects_primary']['total']['ci95_raw'][1]
    up_alarms = {k: v['first_up_alarm'] for k, v in TM.items() if v.get('first_up_alarm')}
    assert up_alarms == {'total': alarm_day, 'hit_total': alarm_day} and alarm_day in [r['d'] for r in ONLY], up_alarms
    assert all(v.get('first_down_alarm') is None for v in TM.values())
    assert D['hypothesis_order_gr1_gr6']['verdict'] == 'keine_abweichung'

    # ---------- Zusammenfassung: Grundlinie und Wirkungsfenster auf derselben Basis ----------
    if de:
        rep('In der Grundlinie lag die Kopfzahl im Mittel beider Anbieter bei 22,1 Prozent (OpenAI 24,0 an 6 Ankertagen, Gemini 20,3 an 10 Ankertagen).',
            f"In der Grundlinie lag die Kopfzahl im Mittel beider Anbieter bei {n(bal)} Prozent (OpenAI {n(oa['mean'])} an {oa['n_anchor_days']} Ankertagen, Gemini {n(ge['mean'])} an {ge['n_anchor_days']} Ankertagen) "
            f"und im Wirkungsfenster, ebenfalls als Mittel der beiden Anbietermittel, bei {n(EWt['provider_balanced_mean'])} Prozent (OpenAI {n(ewo['mean'])} an {ewo['n_anchor_days']} Ankertagen, Gemini {n(ewg['mean'])} an {ewg['n_anchor_days']} Ankertagen).")
        rep('Die Grundlinie dieses Berichts enthält die 8 Nachbewertungen (Abschnitt 2).',
            'Die Grundlinie dieses Berichts enthält diese 8 und weitere Nachbewertungen vom selben Tag (Abschnitt 2).')
    else:
        rep('In the baseline the headline averaged 22.1 percent across both providers (OpenAI 24.0 on 6 anchor days, Gemini 20.3 on 10 anchor days).',
            f"In the baseline the headline averaged {n(bal)} percent across both providers (OpenAI {n(oa['mean'])} on {oa['n_anchor_days']} anchor days, Gemini {n(ge['mean'])} on {ge['n_anchor_days']} anchor days), "
            f"and in the effect window, again as the mean of the two provider means, {n(EWt['provider_balanced_mean'])} percent (OpenAI {n(ewo['mean'])} on {ewo['n_anchor_days']} anchor days, Gemini {n(ewg['mean'])} on {ewg['n_anchor_days']} anchor days).")
        rep('The baseline of this report includes the 8 re-scored answers (section 2).',
            'The baseline of this report includes these 8 and further re-scorings of the same day (section 2).')

    # Abschnitt 2: Nachtrag/Korrektur
    cb = ', '.join(f"{dt(d, lang)} {corr_base_n[d]}" for d in corr_base)
    cr = ', '.join(dt(d, lang) for d in corr_ref)
    XA = EXT['abzug']; ab = XFZ['abgleich_effect_freeze']
    assert XA['frozen_at_utc'] == XFZ['frozen_at_utc'] and XA['cutoff_utc'] == '2026-11-08T23:59:59Z' and XA['rows'] == XFZ['rows']
    assert all(ab[k]['fehlend'] == 0 and ab[k]['geaendert'] == 0 for k in ('web_rows', 'claude_web_rows', 'runs'))
    assert ab['web_rows']['gemeinsam'] == FZ['rows']['web_rows'] and ab['claude_web_rows']['gemeinsam'] == FZ['rows']['claude_web_rows']
    assert ab['web_rows']['neu'] + FZ['rows']['web_rows'] == XA['rows']['web_rows'] and ab['claude_web_rows']['neu'] + FZ['rows']['claude_web_rows'] == XA['rows']['claude_web_rows']
    assert ab['web_rows']['neu_am'].startswith('2026-11-08') and ab['claude_web_rows']['neu_am'] == '2026-11-08'
    xs = dt(XA['frozen_at_utc'][:10], lang, True), XA['frozen_at_utc'][11:16], dt(XA['cutoff_utc'][:10], lang)
    if de:
        rep('Nachgetragen wurden die 16 Antworten der Claude-Grundlinienmessung vom 7. Oktober, als Korrektur übernommen die 8 Nachbewertungen aus Eintrag 37; davon liegt eine Ankertags-Messung in der Grundlinie (Gemini, 3. Oktober, zwei Antworten).',
            f"Nachgetragen wurden die {CB['n_valid']} Antworten der Claude-Grundlinienmessung vom 7. Oktober (16 je Modell), als Korrektur übernommen {len(CORR)} Nachbewertungen von OpenAI und Gemini (8 aus Eintrag 37, 9 aus Eintrag 42, eine aus Eintrag 43) und {D['freeze']['baseline_corrections_applied']['baseline_freeze/claude_web_rows']} der älteren Claude-Reihe. "
            f"Auf Grundlinien-Ankertage fallen davon {sum(corr_base_n.values())} Antworten von Gemini (Antworten je Tag: {cb}), auf Ankertage der Driftbasis {len(corr_ref)} ({cr}).")
        rep('Der zweite Abzug folgt zum Ende des Wirkungsfensters ([[ERGEBNIS: Zeitpunkt, Stichtag und Zeilenzahlen des Wirkungsfenster-Abzugs]]).',
            f"Der zweite Abzug wurde am {dt(FZ['frozen_at_utc'][:10], 'de', True)}, {FZ['frozen_at_utc'][11:16]} UTC, mit dem Stichtag {dt(FZ['cutoff_utc'][:10], 'de')}, 23:59 UTC, eingefroren. Er enthält {n(FZ['rows']['web_rows'], nd=0)} Antwortzeilen von OpenAI und Gemini, {n(FZ['rows']['claude_web_rows'], nd=0)} Antwortzeilen von Claude, {FZ['rows']['runs']} Messläufe und {FZ['rows']['data_gaps']} Einträge des Lückenregisters. "
            f"Gegen diesen Abzug ist der Grundlinienbestand vollständig und unverändert: von {n(INTG['web_rows']['baseline_rows'], nd=0)} Zeilen von OpenAI und Gemini und {n(INTG['claude_web_rows']['baseline_rows'], nd=0)} Claude-Zeilen fehlen {INTG['web_rows']['missing_in_later_pull'] + INTG['claude_web_rows']['missing_in_later_pull']}, geändert sind {INTG['web_rows']['changed_in_later_pull'] + INTG['claude_web_rows']['changed_in_later_pull']}. "
            f"Für die nicht vorregistrierte Erweiterung (Abschnitt 7) wurde ein dritter Abzug am {xs[0]}, {xs[1]} UTC, mit dem Stichtag {xs[2]}, 23:59 UTC, gezogen, nachdem alle Messungen dieses Tages vorlagen. Er enthält {n(XA['rows']['web_rows'], nd=0)} Antwortzeilen von OpenAI und Gemini, {n(XA['rows']['claude_web_rows'], nd=0)} von Claude, {XA['rows']['runs']} Messläufe und {XA['rows']['data_gaps']} Einträge des Lückenregisters. "
            f"Bis zum 7. November stimmt er mit dem zweiten Abzug überein ({ab['web_rows']['fehlend'] + ab['claude_web_rows']['fehlend']} fehlende, {ab['web_rows']['geaendert'] + ab['claude_web_rows']['geaendert']} geänderte Zeilen); neu sind die {ab['web_rows']['neu']} Antwortzeilen von OpenAI und Gemini und die {ab['claude_web_rows']['neu']} von Claude vom 8. November.")
    else:
        rep('The supplement holds the 16 answers of the Claude baseline measurement of 7 October, the corrections the 8 re-scored answers of entry 37; one anchor-day measurement in the baseline is affected (Gemini, 3 October, two answers).',
            f"The supplement holds the {CB['n_valid']} answers of the Claude baseline measurement of 7 October (16 per model), the corrections {len(CORR)} re-scored answers from OpenAI and Gemini (8 from entry 37, 9 from entry 42, one from entry 43) and {D['freeze']['baseline_corrections_applied']['baseline_freeze/claude_web_rows']} of the earlier Claude series. "
            f"Of these, {sum(corr_base_n.values())} Gemini answers fall on baseline anchor days (answers per day: {cb}) and {len(corr_ref)} on anchor days of the drift base ({cr}).")
        rep('The second pull follows at the end of the effect window ([[RESULT: time, cut-off and row counts of the effect-window pull]]).',
            f"The second pull was frozen on {dt(FZ['frozen_at_utc'][:10], 'en', True)}, {FZ['frozen_at_utc'][11:16]} UTC, with the cut-off {dt(FZ['cutoff_utc'][:10], 'en')}, 23:59 UTC. It contains {n(FZ['rows']['web_rows'], nd=0)} answer rows from OpenAI and Gemini, {n(FZ['rows']['claude_web_rows'], nd=0)} answer rows from Claude, {FZ['rows']['runs']} measurement runs and {FZ['rows']['data_gaps']} register entries. "
            f"Checked against this pull the baseline holdings are complete and unchanged: of {n(INTG['web_rows']['baseline_rows'], nd=0)} OpenAI and Gemini rows and {n(INTG['claude_web_rows']['baseline_rows'], nd=0)} Claude rows, {INTG['web_rows']['missing_in_later_pull'] + INTG['claude_web_rows']['missing_in_later_pull']} are missing and {INTG['web_rows']['changed_in_later_pull'] + INTG['claude_web_rows']['changed_in_later_pull']} changed. "
            f"For the extension, which is not pre-registered (section 7), a third pull was taken on {xs[0]}, {xs[1]} UTC, with the cut-off {xs[2]}, 23:59 UTC, after all measurements of that day were in. It contains {n(XA['rows']['web_rows'], nd=0)} answer rows from OpenAI and Gemini, {n(XA['rows']['claude_web_rows'], nd=0)} from Claude, {XA['rows']['runs']} measurement runs and {XA['rows']['data_gaps']} register entries. "
            f"Up to 7 November it matches the second pull ({ab['web_rows']['fehlend'] + ab['claude_web_rows']['fehlend']} rows missing, {ab['web_rows']['geaendert'] + ab['claude_web_rows']['geaendert']} changed); new are the {ab['web_rows']['neu']} answer rows from OpenAI and Gemini and the {ab['claude_web_rows']['neu']} from Claude of 8 November.")

    # Methoden: MDE (Planungswerte und mit Drift-Unsicherheit), Claude
    mk = lambda pre: [MDE[pre + k] for k in CH]
    m1, m2 = mk(''), mk('hit_')
    mz = [MZ[k]['wert'] for k in CH]
    assert all(MZ[k]['planungswert_10_tage_drift_bekannt'] == MDE[k] and MZ[k]['methode'].startswith('2,8-mal die Bootstrap-Standardabweichung') for k in CH)
    assert all(MZ[k]['wert'] > MDE[k] for k in CH)
    if de:
        rep('Kopfzahl 5,12 Prozentpunkte, Direkt 20,81, Saga-Wissen 20,12, Empfehlung 4,61, GR1 bis GR6 allein 7,68. Diese Werte dienen der Planung.',
            f'Kopfzahl {n(m1[0])} Prozentpunkte, Direkt {n(m1[1])}, Saga-Wissen {n(m1[2])}, Empfehlung {n(m1[3])}, GR1 bis GR6 allein {n(m1[4])}. Diese Werte dienen der Planung; sie wurden am 7. Oktober vor dem Ereignis mit der um die Einträge 42 und 43 korrigierten Grundlinie berechnet und behandeln die Drift als bekannt. '
            f'Gemini hat im Wirkungsfenster nur {n_eff["Gemini"]} vollständige Ankertage (Abschnitt 2). Mit der Unsicherheit der Driftgeraden und den tatsächlich gemessenen Wirkungstagen je Anbieter liegt die mindestens erkennbare Verschiebung bei {n(mz[0])} Prozentpunkten für die Kopfzahl, {n(mz[1])} im Direkt-Kanal, {n(mz[2])} für Saga-Wissen, {n(mz[3])} für Empfehlung und {n(mz[4])} für GR1 bis GR6, '
            f'gerechnet als 2,8-fache Bootstrap-Standardabweichung der driftbereinigten Schätzung; diese Werte sind nicht vorregistriert.')
        rep('alle Fragen 4,63 Prozentpunkte, Direkt 15,67, Saga-Wissen 23,20, Empfehlung 4,61, GR1 bis GR6 7,68.',
            f'alle Fragen {n(m2[0])} Prozentpunkte, Direkt {n(m2[1])}, Saga-Wissen {n(m2[2])}, Empfehlung {n(m2[3])}, GR1 bis GR6 {n(m2[4])}. Änderung 3 nennt für den Direkt-Kanal 15,7, den Wert vor den Korrekturen der Einträge 42 und 43 vom selben Tag.')
        rep('Gezählt wird je Tag die früheste Messung mit Messwerten.',
            'Der Tageswert ist das einfache Mittel der drei Modelle (Eintrag 41). Gezählt wird je Tag und Modell die früheste Messung mit Messwerten.')
        rep('weniger als die mindestens erkennbare Verschiebung von 15,67.', f'weniger als die mindestens erkennbare Verschiebung von {n(MDE["hit_direct"])}.')
    else:
        rep('headline 5.12 percentage points, Direct 20.81, Saga knowledge 20.12, Recommendation 4.61, GR1 to GR6 alone 7.68. These values serve planning only.',
            f'headline {n(m1[0])} percentage points, Direct {n(m1[1])}, Saga knowledge {n(m1[2])}, Recommendation {n(m1[3])}, GR1 to GR6 alone {n(m1[4])}. These values serve planning only; they were computed on 7 October, before the event, with the baseline corrected for entries 42 and 43, and treat the drift as known. '
            f'Gemini has only {n_eff["Gemini"]} complete anchor days in the effect window (section 2). Taking into account the uncertainty of the drift line and the anchor days actually measured per provider, the minimum detectable shift is {n(mz[0])} percentage points for the headline, {n(mz[1])} in the Direct channel, {n(mz[2])} for Saga knowledge, {n(mz[3])} for Recommendation and {n(mz[4])} for GR1 to GR6, '
            f'computed as 2.8 times the bootstrap standard deviation of the drift-adjusted estimate; these values are not pre-registered.')
        rep('all questions 4.63 percentage points, Direct 15.67, Saga knowledge 23.20, Recommendation 4.61, GR1 to GR6 7.68.',
            f'all questions {n(m2[0])} percentage points, Direct {n(m2[1])}, Saga knowledge {n(m2[2])}, Recommendation {n(m2[3])}, GR1 to GR6 {n(m2[4])}. Amendment 3 gives 15.7 for the Direct channel, the value before the corrections of entries 42 and 43 of the same day.')
        rep('For each day the earliest measurement with values counts.',
            'The daily value is the simple mean of the three models (entry 41). For each day and model the earliest measurement with values counts.')
        rep('less than the minimum detectable shift of 15.67.', f'less than the minimum detectable shift of {n(MDE["hit_direct"])}.')

    # Tabelle 2 (Kopfzahl, Direkt)
    def t2row(ch, label):
        x = B[ch]; o, g, hb = x['providers']['OpenAI'], x['providers']['Gemini'], x['headline_days_both']
        return f"| {label} | {n(o['mean'])} ({n(o['sd'])}) · {o['n_anchor_days']} | {n(g['mean'])} ({n(g['sd'])}) · {g['n_anchor_days']} | {n(x['provider_balanced_mean'])} | {n(hb['mean'])} ({n(hb['sd'])}) · {hb['n_anchor_days']} |"
    if de:
        rep('| Kopfzahl (16 Fragen) | 23,96 (3,42) · 6 | 20,31 (7,27) · 10 | 22,13 | 22,31 (4,71) · 6 |', t2row('total', 'Kopfzahl (16 Fragen)'))
        rep('| Direkt (D1–D3) | 81,48 (13,46) · 6 | 76,67 (27,44) · 10 | 79,08 | 80,56 (13,94) · 6 |', t2row('direct', 'Direkt (D1–D3)'))
    else:
        rep('| Headline (16 questions) | 23.96 (3.42) · 6 | 20.31 (7.27) · 10 | 22.13 | 22.31 (4.71) · 6 |', t2row('total', 'Headline (16 questions)'))
        rep('| Direct (D1–D3) | 81.48 (13.46) · 6 | 76.67 (27.44) · 10 | 79.08 | 80.56 (13.94) · 6 |', t2row('direct', 'Direct (D1–D3)'))
    # restliche Zeilen der Tabellen 2 und 3 gegen results.json prüfen (nicht ersetzen, nur Abbruch bei Abweichung)
    for ch, lde, len_ in [('longtail', 'Saga-Wissen (L1, L2)', 'Saga knowledge (L1, L2)'), ('discovery', 'Empfehlung (10 Fragen)', 'Recommendation (10 questions)'), ('recommend_gr', 'davon GR1–GR6', 'of which GR1–GR6')]:
        assert t2row(ch, lde if de else len_) in src, ('Tabelle 2 veraltet', ch)

    # Drift-Absatz (Drift je Anbieter über dessen gemessene Wirkungstage)
    gd, od = ge['drift_used'], oa['drift_used']
    if de:
        old = 'Die Driftgerade der Kopfzahl steigt bei Gemini um 0,277 Prozentpunkte je Tag (95-Prozent-Intervall 0,037 bis 0,516, 17 Ankertage) und ist bei OpenAI flach (−0,019; −0,174 bis 0,137; 13 Ankertage). Allein aus der fortgeschriebenen Drift ergibt sich zwischen Grundlinie und Wirkungsfenster ein Unterschied der Kopfzahl von 3,87 Prozentpunkten im Mittel beider Anbieter (Gemini 8,30, OpenAI −0,56), im Direkt-Kanal von 9,31 und im Empfehlungs-Kanal von 1,70; ohne Driftabzug würde er als Wirkung gelesen. In den Kanälen enthalten alle Steigungsintervalle die Null.'
        new = (f"Die Driftgerade der Kopfzahl steigt bei Gemini um {n(gd['slope_pp_per_day'], nd=3)} Prozentpunkte je Tag (95-Prozent-Intervall {n(gd['slope_ci95'][0], nd=3)} bis {n(gd['slope_ci95'][1], nd=3)}, {gd['n_days']} Ankertage) und ist bei OpenAI flach ({n(od['slope_pp_per_day'], nd=3)}; {n(od['slope_ci95'][0], nd=3)} bis {n(od['slope_ci95'][1], nd=3)}; {od['n_days']} Ankertage). "
               f"Allein aus der fortgeschriebenen Drift ergibt sich an den gemessenen Wirkungstagen ein Unterschied der Kopfzahl von {n(DRI['total']['mean'])} Prozentpunkten im Mittel beider Anbieter (Gemini {n(DRI['total']['providers']['Gemini'])} an {n_eff['Gemini']} Tagen, OpenAI {n(DRI['total']['providers']['OpenAI'])} an {n_eff['OpenAI']} Tagen), im Direkt-Kanal von {n(DRI['direct']['mean'])} und im Empfehlungs-Kanal von {n(DRI['discovery']['mean'])}; ohne Driftabzug würde er als Wirkung gelesen. Beide Steigungsintervalle der Kopfzahl und alle Steigungsintervalle der Kanäle enthalten die Null.")
    else:
        old = 'The drift line of the headline rises by 0.277 percentage points per day for Gemini (95 percent interval 0.037 to 0.516, 17 anchor days) and is flat for OpenAI (−0.019; −0.174 to 0.137; 13 anchor days). The extended drift alone implies a headline difference between baseline and effect window of 3.87 percentage points across both providers (Gemini 8.30, OpenAI −0.56), 9.31 in the Direct channel and 1.70 in the Recommendation channel; without drift removal it would be read as an effect. In the channels all slope intervals include zero.'
        new = (f"The drift line of the headline rises by {n(gd['slope_pp_per_day'], nd=3)} percentage points per day for Gemini (95 percent interval {n(gd['slope_ci95'][0], nd=3)} to {n(gd['slope_ci95'][1], nd=3)}, {gd['n_days']} anchor days) and is flat for OpenAI ({n(od['slope_pp_per_day'], nd=3)}; {n(od['slope_ci95'][0], nd=3)} to {n(od['slope_ci95'][1], nd=3)}; {od['n_days']} anchor days). "
               f"On the effect days actually measured, the extended drift alone implies a headline difference of {n(DRI['total']['mean'])} percentage points across both providers (Gemini {n(DRI['total']['providers']['Gemini'])} on {n_eff['Gemini']} days, OpenAI {n(DRI['total']['providers']['OpenAI'])} on {n_eff['OpenAI']} days), {n(DRI['direct']['mean'])} in the Direct channel and {n(DRI['discovery']['mean'])} in the Recommendation channel; without drift removal it would be read as an effect. Both slope intervals of the headline and all slope intervals of the channels include zero.")
    assert all(B[ch]['providers'][p]['drift_used']['slope_ci95'][0] <= 0 <= B[ch]['providers'][p]['drift_used']['slope_ci95'][1] for ch in CH for p in P)
    rep(old, new)
    # Driftprüfung-Alarm gegen results.json prüfen
    al = [(p, ch, a['d']) for p in P for ch, v in D['drift_check'][p].items() if not ch.startswith('hit_') for a in v['alarms']]
    assert al == [('Gemini', 'longtail', '2026-10-03')], al

    # Grenzen: MDE-Satz
    ub = ep['ci95_detrended'][1]; ub_pct = ZU['obergrenze_anteil_grundlinie_pct']['total']
    assert abs(ub / bal * 100 - ub_pct) <= 0.05
    if de:
        rep('Die mindestens erkennbare Verschiebung liegt bei der Kopfzahl um 5 Prozentpunkte und in den Kanälen Direkt und Saga-Wissen um 20 Prozentpunkte; kleinere Wirkungen bleiben unentdeckt.',
            f'Die mindestens erkennbare Verschiebung liegt als Planungswert bei zehn Wirkungstagen je Anbieter für die Kopfzahl bei {n(MDE["total"])} Prozentpunkten, im Direkt-Kanal bei {n(MDE["direct"])} und im Kanal Saga-Wissen bei {n(MDE["longtail"])}; mit der Unsicherheit der Drift und den tatsächlich gemessenen Wirkungstagen liegt sie bei {n(mz[0])}, {n(mz[1])} und {n(mz[2])}. '
            f'Kleinere Wirkungen erkennt das Design mit weniger als 80 Prozent Power. Mit den Daten vereinbar sind bei der Kopfzahl Wirkungen bis {n(ub, sign=True)} Prozentpunkte, das sind {num(ub_pct, lang, nd=1)} Prozent der Grundlinie.')
    else:
        rep('The minimum detectable shift is about 5 percentage points for the headline and about 20 percentage points in the Direct and Saga knowledge channels; smaller effects go undetected.',
            f'As a planning value with ten effect days per provider the minimum detectable shift is {n(MDE["total"])} percentage points for the headline, {n(MDE["direct"])} in the Direct channel and {n(MDE["longtail"])} in the Saga knowledge channel; with the uncertainty of the drift and the effect days actually measured it is {n(mz[0])}, {n(mz[1])} and {n(mz[2])}. '
            f'The design detects smaller effects with less than 80 percent power. For the headline the data are compatible with effects of up to {n(ub, sign=True)} percentage points, which is {num(ub_pct, lang, nd=1)} percent of the baseline.')

    # ---------- Ergebnis-Marken ----------
    pref = '[[ERGEBNIS' if de else '[[RESULT'
    def mark(stub, text):
        hits = [l for l in src.split('\n') if stub in l]
        assert len(hits) == 1, stub
        st = hits[0].index(stub); en_ = hits[0].index(']]', st) + 2
        R.append((hits[0][st:en_], text))

    datestr = dt(FZ['frozen_at_utc'][:10], lang, True)
    mark(f'{pref}: Datum des Wirkungsfenster-Abzugs]]' if de else f'{pref}: date of the effect-window pull]]', datestr)

    # Festlegungen neben den Änderungen (Abschnitt 1)
    n_old, n_tot = len(win_old), SR['overrides']
    E43 = SR['eintrag43_enger_umgesetzt']; e43w = E43['je_fenster'].get('wirkung', 0); e43x = e43w + E43['je_fenster'].get('erweiterung_0811', 0)
    assert E43['je_tabelle'] == {'claude_web_rows': e43x} and all(e['question_id'] == 'D1' and e['score_bewerter_vorregistriert'] == 0 and e['score_wortlaut_eintrag43'] == 1 for e in E43['zeilen'])
    # Eintrag 43 vor dem Ereignis: Gemini 06.09., D1, als Korrektur der Grundlinie übernommen (−3 auf +2)
    c43 = [c for c in CORR if c['d'] == '2026-09-06' and c['llm'] == 'gemini' and c['question_id'] == 'D1']
    assert len(c43) == 1 and c43[0]['score'] == 2 and anch.get('2026-09-06') == 'cusum_ref'
    if de:
        txt = (f"Neben den vier Änderungen wurden am 7. Oktober vor dem Ereignis vier Festlegungen registriert. "
               f"Claude wird ab dem 9. Oktober mit dem jeweils neuesten Modell der drei Familien Opus, Sonnet und Haiku gemessen; der Anbieterwert ist ihr Mittel (Eintrag 41). Auch die Grundlinienmessung am 7. Oktober umfasst alle drei Modelle, bei Haiku noch Haiku 4.5 (Einträge 45 und 49). "
               f"Antworten, die einen ehrlichen Nichtfund der Suche melden, zählen null statt minus drei Punkte (Eintrag 42). Ein Verweis auf die Filmkritikerin Pauline Kael gilt als Namens-Kollision mit null Punkten; echte Angaben über den Autor in derselben Antwort werden wie üblich bewertet (Eintrag 43). "
               f"Diese drei Festlegungen verändern die primäre Kennzahl nicht oder wirken in Grundlinie und Wirkungsfenster gleich, Eintrag 43 mit einer Einschränkung. "
               f"Den zweiten Teil von Eintrag 43 setzt der Bewerter in der vorregistrierten Fassung, also vor den Regeln vom 2. November, enger um: Eine Antwort, die den Autor zutreffend beschreibt und sich am Ende gegen Pauline Kael abgrenzt, wertet er als Kollision mit null Punkten (Fehler 1 in Eintrag 71). "
               f"Vor dem Ereignis betraf das bei OpenAI und Gemini nur eine Antwort (Gemini, 6. September, Frage D1), die am 7. Oktober nach dem Wortlaut nachbewertet wurde. Im Wirkungsfenster betrifft es {e43w} Antworten von Claude auf die Frage D1, in der Erweiterung {e43x}; die Hauptanalyse folgt hier dem Bewerter, OpenAI und Gemini sind nicht betroffen (Abschnitt 6). "
               f"Fällt OpenAI wegen eines erschöpften Kontingents aus, wird einmal innerhalb von 36 Stunden nachgemessen (Eintrag 44). Diese Festlegung wirkt nur im Wirkungsfenster, denn die Grundlinie enthält keine Nachmessung; so geht für OpenAI der 2. November ein (Abschnitt 2). "
               f"Im Wirkungsfenster kamen drei Festlegungen hinzu. Seit dem 1. November gilt eine leere Antwort als fehlgeschlagene Messung (Eintrag 66), seit dem Ankertag 5. November wird die Frage dann im selben Lauf einmal wiederholt (Eintrag 70); leere Antworten vor dem 1. November gehen mit null Punkten ein. "
               f"Am 2. November wurden vier Fehler der Bewertungsregeln behoben, rückwirkend für das Wirkungsfenster; die Messdatenbank trägt die neuen Regeln seit der Messung vom 5. November (Eintrag 71). "
               f"Die Hauptanalyse bewertet das Wirkungsfenster durchgehend nach den vorregistrierten Regeln, mit dem Bewerter in der Fassung vor dem 2. November: Sie setzt die {W[n_old]} rückwirkend geänderten Antworten zurück, und die {g0511['openai_search'] + g0511['claude']} gewerteten Antworten vom 5. November ({g0511['openai_search']} von OpenAI, {g0511['claude']} von Claude) wurden am Volltext nach den vorregistrierten Regeln neu bewertet. "
               f"Davon weicht {W[len(win_0511)]} Antwort von Claude ab, die {g0511['openai_search']} Antworten von OpenAI sind unter beiden Regeln gleich bewertet; zusammen setzt die Hauptanalyse {W[n_tot]} Antworten zurück. Eine Sensitivitätsrechnung wendet die neuen Regeln auch auf die Grundlinie an (Abschnitt 7). "
               f"Bei Claude ist die Websuche aktiviert, aber nicht erzwungen; ob gesucht wurde, wird seit dem 2. November je Antwort gespeichert (Eintrag 72). "
               f"Nach dem Ende des Wirkungsfensters kamen am 8. November eine Nachhol-Regel für Gemini (Eintrag 82) und die nicht vorregistrierte Erweiterung bis zum Ankertag 8. November hinzu (Eintrag 83, Abschnitt 7). Abschnitt 8 fasst alle Abweichungen vom Plan zusammen.")
    else:
        txt = (f"Besides the four amendments, four rules were registered on 7 October before the event. "
               f"From 9 October Claude is measured with the newest model of each of the three families Opus, Sonnet and Haiku; the provider value is their mean (entry 41). The baseline measurement on 7 October also covers all three models, with Haiku still at Haiku 4.5 (entries 45 and 49). "
               f"Answers that report an honest search non-result score zero instead of minus three (entry 42). A reference to the film critic Pauline Kael counts as a name collision with zero points; genuine statements about the author in the same answer are scored as usual (entry 43). "
               f"These three rules leave the primary metric unchanged or act equally on baseline and effect window, entry 43 with one qualification. "
               f"The scorer in its pre-registered version, that is before the rules of 2 November, implements the second part of entry 43 more narrowly: an answer that describes the author correctly and distinguishes him from Pauline Kael at the end is scored as a collision with zero points (fault 1 in entry 71). "
               f"Before the event this concerned only one OpenAI or Gemini answer (Gemini, 6 September, question D1), which was re-scored according to the wording on 7 October. In the effect window it concerns {e43w} Claude answers to question D1, in the extension {e43x}; here the main analysis follows the scorer, and OpenAI and Gemini are not affected (section 6). "
               f"If OpenAI fails because its quota is exhausted, it is measured once more within 36 hours (entry 44). This rule acts only in the effect window, because the baseline contains no re-measurement; this is how 2 November enters for OpenAI (section 2). "
               f"Three further rules followed inside the effect window. Since 1 November an empty answer counts as a failed measurement (entry 66), and from anchor day 5 November the question is then asked once more within the same run (entry 70); empty answers before 1 November enter with zero points. "
               f"On 2 November four errors in the scoring rules were corrected, retroactively for the effect window; the measurement database carries the new rules from the measurement of 5 November (entry 71). "
               f"The main analysis scores the effect window throughout under the pre-registered rules, with the scorer in its version before 2 November: it resets the {W[n_old]} retroactively changed answers, and the {g0511['openai_search'] + g0511['claude']} scored answers of 5 November ({g0511['openai_search']} from OpenAI, {g0511['claude']} from Claude) were re-scored on the full text under the pre-registered rules. "
               f"Of these, {W[len(win_0511)]} Claude answer differs, while the {g0511['openai_search']} OpenAI answers score the same under both rules; in total the main analysis resets {W[n_tot]} answers. A sensitivity analysis applies the new rules to the baseline as well (section 7). "
               f"For Claude, web search is enabled but not forced; since 2 November each answer records whether a search took place (entry 72). "
               f"After the effect window had closed, a catch-up rule for Gemini (entry 82) and the extension to anchor day 8 November, which is not pre-registered (entry 83, section 7), were added on 8 November. Section 8 summarises all deviations from the plan.")
    mark(f'{pref}: Festlegungen neben den Änderungen' if de else f'{pref}: rules besides the amendments', txt)

    # Abschnitt 2: Verhältnis der beiden Fassungen des Empfehlungs-Kanals
    if de:
        txt = 'Die Fragen G1, G2, C1 und C2 haben an allen Ankertagen null Punkte; der Kanal aus zehn Fragen ist deshalb an jedem Anbieter-Tag genau das 0,6-Fache des Kanals GR1 bis GR6, in Punkten wie in der Trefferquote.'
    else:
        txt = 'Questions G1, G2, C1 and C2 score zero on every anchor day; the ten-question channel is therefore exactly 0.6 times the channel GR1 to GR6 on every provider-day, in points and in the hit rate.'
    mark(f'{pref}: Verhältnis der beiden Fassungen' if de else f'{pref}: relation of the two versions', txt)

    # Zusammenfassung
    lu, o4, ex = LU['effects_primary']['total'], O4['effects_primary']['total'], EXE['total']
    assert FE['coverage']['effect']['Gemini']['complete'] == 1 and FE['effects_primary']['total']['ci95_detrended'] is None
    assert not any(excl0(v['ci95_detrended']) for v in (lu, o4, ex, ES['total'], s71))
    if de:
        s1 = (f"Ab dem {dt(only_first, lang)} fehlt Gemini wegen aufgebrauchten Guthabens. "
              f"Ohne Driftabzug beträgt die Differenz damit {n(ep['raw'], sign=True)} Prozentpunkte; driftbereinigt, wie vorregistriert, beträgt sie {n(ep['detrended'], sign=True)} Prozentpunkte (95-%-Intervall {c(ep['ci95_detrended'])}). Das Intervall enthält die Null; die Nullhypothese wird nicht verworfen.")
        s2 = (f"Auch in den Kanälen schließt kein Intervall die Null aus: Direkt {pc(E['direct'])}, Saga-Wissen {pc(E['longtail'])}, Empfehlung {pc(E['discovery'])}, davon GR1 bis GR6 {pc(E['recommend_gr'])}. "
              f"Weder Direkt noch Empfehlung zeigen bis zum {dt(COV['effect']['last'], lang)} eine erste Abweichung; die Reihenfolge-Hypothese erhält keine Stütze, auch mit dem vorregistrierten Empfehlungs-Kanal GR1 bis GR6. "
              f"Einen Aufwärtsalarm melden nur die Kopfzahl und die Trefferquote über alle Fragen, beide am {dt(alarm_day, lang)}, an einem Tag, für den nur OpenAI misst.")
        s3 = (f"Claude auf claude.ai lag in der Grundlinienmessung am 7. Oktober im Mittel der drei Modelle bei {n(CB['provider_mean']['total'])} Prozent (Direkt {n(CB['provider_mean']['direct'])}, Saga-Wissen und Empfehlung {n(0)}) und an den {len(c_anchor)} Ankertagen von {rng(c_tot, lang)} Prozent; "
              f"Empfehlungen nannten den Autor an keinem Tag. Diese Werte sind beschreibend.")
        s4 = (f"Gegen die Sensitivitäts-Grundlinie ohne Vorab-Verfügbarkeit (8. bis 29. September) beträgt die Differenz der Kopfzahl {pc(ES['total'])}, mit den Bewertungsregeln vom 2. November in beiden Fenstern {pc(s71)}, mit leeren Antworten als Lücke {pc(lu)} und ohne Änderung 4 {pc(o4)}; alle diese Rechnungen führen zur selben Entscheidung. "
              f"Werden leere Antworten als Fehlmessung gewertet, bleibt für Gemini ein Wirkungstag, und ein Intervall lässt sich nicht berechnen. "
              f"Eine nicht vorregistrierte Erweiterung des Wirkungsfensters bis zum Ankertag 8. November, an dem auch Gemini wieder gemessen ist, ergibt {pc(ex)}; entschieden wird allein mit der vorregistrierten Hauptanalyse. "
              f"OpenAI ist an allen {n_eff['OpenAI']} Ankertagen des Wirkungsfensters vollständig gemessen, Gemini an {n_eff['Gemini']}.")
    else:
        s1 = (f"From {dt(only_first, lang)} Gemini is missing because its credit was used up. "
              f"Without drift removal the difference is thus {n(ep['raw'], sign=True)} percentage points; drift-adjusted, as pre-registered, it is {n(ep['detrended'], sign=True)} percentage points (95 % interval {c(ep['ci95_detrended'])}). The interval includes zero; the null hypothesis is not rejected.")
        s2 = (f"No channel interval excludes zero either: Direct {pc(E['direct'])}, Saga knowledge {pc(E['longtail'])}, Recommendation {pc(E['discovery'])}, of which GR1 to GR6 {pc(E['recommend_gr'])}. "
              f"Neither Direct nor Recommendation shows a first deviation up to {dt(COV['effect']['last'], lang)}; the order hypothesis receives no support, also with the pre-registered Recommendation channel GR1 to GR6. "
              f"Only the headline and the hit rate across all questions raise an upward alarm, both on {dt(alarm_day, lang)}, a day measured by OpenAI alone.")
        s3 = (f"In the baseline measurement on 7 October Claude on claude.ai stood at {n(CB['provider_mean']['total'])} percent as the mean of the three models (Direct {n(CB['provider_mean']['direct'])}, Saga knowledge and Recommendation {n(0)}) and from {rng(c_tot, lang)} percent on the {len(c_anchor)} anchor days; "
              f"no recommendation named the author on any day. These values are descriptive.")
        s4 = (f"Against the sensitivity baseline without early availability (8 to 29 September) the headline difference is {pc(ES['total'])}; with the scoring rules of 2 November in both windows it is {pc(s71)}, with empty answers treated as gaps {pc(lu)} and without amendment 4 {pc(o4)}. All of these lead to the same decision. "
              f"If empty answers are treated as failed measurements, Gemini keeps {W[1]} effect day and no interval can be computed. "
              f"An extension of the effect window to anchor day 8 November, on which Gemini is measured again, is not pre-registered and gives {pc(ex)}; the decision rests on the pre-registered main analysis alone. "
              f"OpenAI is fully measured on all {n_eff['OpenAI']} anchor days of the effect window, Gemini on {n_eff['Gemini']}.")
    assert not ep['ci_excludes_zero']
    assert D['hypothesis_order']['verdict'] == 'keine_abweichung'
    assert all(not excl0(E[ch]['ci95_detrended']) for ch in CH)
    assert not c_disc_pos
    keys = (['Kopfzahl im Wirkungsfenster', 'Kanäle Direkt, Saga-Wissen', 'Claude auf claude.ai, beschreibend', 'Sensitivitäts-Grundlinie ohne Vorab'] if de else
            ['headline in the effect window, drift', 'channels Direct, Saga knowledge', 'Claude on claude.ai, descriptive', 'sensitivity baseline without early'])
    for k, s in zip(keys, [s1, s2, s3, s4]):
        line = [l for l in src.split('\n') if pref + ': ' + k in l]
        assert len(line) == 1, k
        st = line[0].index(pref); en_ = line[0].index(']]', st) + 2
        R.append((line[0][st:en_], s))

    # Tabelle 1
    if de:
        rep('| Wirkungsfenster | 08.10.–07.11.2026 | 10 | [[ERGEBNIS]] | [[ERGEBNIS]] |', f"| Wirkungsfenster | 08.10.–07.11.2026 | {COV['effect']['anchor_days']} | {n_eff['OpenAI']} | {n_eff['Gemini']} |")
        rep('| Beobachtung verzögerter Wirkung | 08.11.2026–06.01.2027 | 20 | [[ERGEBNIS]] | [[ERGEBNIS]] |', f"| Beobachtung verzögerter Wirkung | 08.11.2026–06.01.2027 | {COV['delayed']['anchor_days']} | läuft | läuft |")
    else:
        rep('| Effect window | 2026-10-08–11-07 | 10 | [[RESULT]] | [[RESULT]] |', f"| Effect window | 2026-10-08–11-07 | {COV['effect']['anchor_days']} | {n_eff['OpenAI']} | {n_eff['Gemini']} |")
        rep('| Delayed-effect observation | 2026-11-08–2027-01-06 | 20 | [[RESULT]] | [[RESULT]] |', f"| Delayed-effect observation | 2026-11-08–2027-01-06 | {COV['delayed']['anchor_days']} | ongoing | ongoing |")
    assert COV['delayed']['OpenAI']['complete'] == 0 and len(COV['delayed']['OpenAI']['pending']) == COV['delayed']['anchor_days']
    assert EXT['window_effect'] == ['2026-10-08', '2026-11-08'] and EXC['effect']['last'] == '2026-11-08' == COV['delayed']['first']
    assert EXC['effect']['anchor_days'] == COV['effect']['anchor_days'] + 1 and EXC['effect']['OpenAI']['complete'] == n_eff['OpenAI'] + 1 and EXC['effect']['Gemini']['complete'] == n_eff['Gemini'] + 1
    mark(f'{pref}: Erweiterung Tabelle 1]]' if de else f'{pref}: extension table 1]]', f"{EXC['effect']['anchor_days']} | {EXC['effect']['OpenAI']['complete']} | {EXC['effect']['Gemini']['complete']}")

    # Abschnitt 2: Ausfälle
    gm = ids([dt(d, lang) for d in gem_missing], lang)
    if de:
        txt = (f"Im Wirkungsfenster hat OpenAI an allen {n_eff['OpenAI']} Ankertagen 16 Messwerte; am 2. November lehnte die Schnittstelle zunächst alle Fragen ab (Kontingent erschöpft), die Nachmessung nach der Nachhol-Regel lag innerhalb der Frist von 36 Stunden (Einträge 44 und 68). "
               f"Gemini lehnte an den Ankertagen {gm} alle Fragen ab, weil das Guthaben des Messkontos aufgebraucht war (Einträge {gem_list}); nachgemessen wurde nicht, und diese Tage werden auch nachträglich nicht nachgemessen, weil die Nachhol-Regel für Gemini erst ab dem 8. November gilt (Eintrag 82). Für Gemini gehen damit {n_eff['Gemini']} Wirkungs-Ankertage ein, die Kopfzahl ist an {len(BOTH)} Ankertagen definiert, die übrigen {len(ONLY)} sind Basiswechsel. "
               f"Die Effektschätzung je Anbieter bleibt davon formal unberührt, weil jede Anbieter-Differenz gegen die eigene Grundlinie gerechnet wird; die Gemini-Differenz stützt sich aber nur auf die erste Hälfte des Fensters. "
               f"Messungen an Zwischentagen gab es im Wirkungsfenster nicht.")
    else:
        txt = (f"In the effect window OpenAI has 16 values on all {n_eff['OpenAI']} anchor days; on 2 November the interface first refused every question (quota exhausted), and the repeat measurement under the catch-up rule fell within the 36-hour limit (entries 44 and 68). "
               f"Gemini refused every question on the anchor days {gm} because the credit of the measurement account was used up (entries {gem_list}); no repeat measurement was made, and these days will not be re-measured later, because the catch-up rule for Gemini applies only from 8 November (entry 82). Gemini therefore contributes {n_eff['Gemini']} effect anchor days, the headline is defined on {len(BOTH)} anchor days, and the remaining {len(ONLY)} are basis changes. "
               f"Formally the per-provider estimate is unaffected, because each provider difference is computed against its own baseline; the Gemini difference, however, rests on the first half of the window only. "
               f"There were no measurements on intermediate days in the effect window.")
    assert all(dd < '2026-10-08' for p in P for dd in D['off_anchor_days'][p])
    mark('[[ERGEBNIS: Ausfälle und Registereinträge im Wirkungsfenster.]]' if de else '[[RESULT: outages and register entries in the effect window.]]', txt)

    # Abschnitt 4: gepoolte Direkt-Trefferquote
    HP = ZU['hit_direct_grundlinie_gepoolt']
    assert HP['mittel_der_anbieter'] == B['hit_direct']['provider_balanced_mean'] and abs(HP['hits'] / HP['answers'] * 100 - HP['pct']) < 0.01
    mark(f'{pref}: gepoolte Direkt-Trefferquote]]' if de else f'{pref}: pooled Direct hit rate]]',
         (f"über alle Antworten gezählt {HP['hits']} von {HP['answers']} ({n(HP['pct'])} Prozent)" if de else f"counted over all answers it is {HP['hits']} of {HP['answers']} ({n(HP['pct'])} percent)"))

    # Abschnitt 4: Kopfzahl
    hb = ', '.join(f"{n(r['headline']['total'])} ({dshort(r['d']) if de else dt(r['d'], lang)})" for r in BOTH)
    ob = ', '.join(f"{n(r['OpenAI']['total'])}" for r in ONLY)
    if de:
        txt = (f"An den {len(BOTH)} Ankertagen mit beiden Anbietern lag die Kopfzahl bei {hb}, im Mittel {n(m_both)} Prozent. An den {len(ONLY)} folgenden Ankertagen misst nur OpenAI ({ob}); für diese Tage ist keine Kopfzahl definiert. "
               f"OpenAI lag im Wirkungsfenster im Mittel bei {n(ewo['mean'])} Prozent ({n_eff['OpenAI']} Tage), Gemini bei {n(ewg['mean'])} ({n_eff['Gemini']} Tage). "
               f"Driftbereinigt beträgt die Differenz bei OpenAI {n(op['detrended'], sign=True)} Prozentpunkte ({c(op['ci95_detrended'])}), bei Gemini {n(gp['detrended'], sign=True)} ({c(gp['ci95_detrended'])}), im Mittel {n(ep['detrended'], sign=True)} ({c(ep['ci95_detrended'])}). "
               f"Unbereinigt sind es {n(op['raw'], sign=True)}, {n(gp['raw'], sign=True)} und im Mittel {n(ep['raw'], sign=True)} ({c(ep['ci95_raw'])}). "
               f"Das Intervall der bereinigten Differenz enthält die Null; die Nullhypothese wird nicht verworfen. Das Intervall der unbereinigten Differenz liegt knapp über null; ohne Änderung 4 enthält es die Null (Abschnitt 7). "
               f"Eine zusätzliche, nicht vorregistrierte Prüfung mit {SW_N} weiteren Startwerten des Zufallsgenerators zeigt, wie knapp das ist: Die Untergrenze des unbereinigten Intervalls reicht von {rng([SW['unbereinigt_untergrenze']['min'], SW['unbereinigt_untergrenze']['max']], lang)} (im Mittel {n(SW['unbereinigt_untergrenze']['mittel'])}) und liegt bei {SW_K} der {SW_N} Startwerte über null. "
               f"Ob das unbereinigte Intervall die Null ausschließt, hängt bei {n(SW['n_boot'], nd=0)} Ziehungen also vom Startwert ab. Das bereinigte Intervall enthält die Null bei jedem Startwert (Untergrenze {rng([SW['bereinigt_untergrenze']['min'], SW['bereinigt_untergrenze']['max']], lang)}, Obergrenze {rng([SW['bereinigt_obergrenze']['min'], SW['bereinigt_obergrenze']['max']], lang)}). "
               f"Der Abstand zwischen unbereinigter und bereinigter Differenz ({n(ep['raw'] - ep['detrended'])} Prozentpunkte) ist bis auf Rundung die an den gemessenen Wirkungstagen fortgeschriebene Drift ({n(DRI['total']['mean'])}); maßgeblich ist nach der Vorregistrierung die bereinigte Differenz. "
               f"Der einseitige CUSUM der Kopfzahl alarmiert am {dt(alarm_day, lang)} aufwärts. Die Residuen reichen an den Tagen mit beiden Anbietern von {rng([TM['total']['residuals'][r['d']]['resid'] for r in BOTH], lang)} und an den Tagen mit nur OpenAI von {rng([TM['total']['residuals'][r['d']]['resid'] for r in ONLY], lang)} Prozentpunkten; der Alarm fällt damit mit dem Basiswechsel zusammen (Einordnung in Abschnitt 7). Die 95-Prozent-Prognosegrenze überschreitet kein Tag.")
    else:
        txt = (f"On the {len(BOTH)} anchor days with both providers the headline was {hb}, {n(m_both)} percent on average. On the {len(ONLY)} following anchor days only OpenAI measures ({ob}); no headline is defined for these days. "
               f"In the effect window OpenAI averaged {n(ewo['mean'])} percent ({n_eff['OpenAI']} days), Gemini {n(ewg['mean'])} ({n_eff['Gemini']} days). "
               f"Drift-adjusted, the difference is {n(op['detrended'], sign=True)} percentage points for OpenAI ({c(op['ci95_detrended'])}), {n(gp['detrended'], sign=True)} for Gemini ({c(gp['ci95_detrended'])}) and {n(ep['detrended'], sign=True)} on average ({c(ep['ci95_detrended'])}). "
               f"Unadjusted it is {n(op['raw'], sign=True)}, {n(gp['raw'], sign=True)} and {n(ep['raw'], sign=True)} on average ({c(ep['ci95_raw'])}). "
               f"The interval of the adjusted difference includes zero; the null hypothesis is not rejected. The interval of the unadjusted difference lies just above zero; without amendment 4 it includes zero (section 7). "
               f"An additional check, not pre-registered, with {SW_N} further seeds of the random number generator shows how narrow this is: the lower bound of the unadjusted interval ranges from {rng([SW['unbereinigt_untergrenze']['min'], SW['unbereinigt_untergrenze']['max']], lang)} ({n(SW['unbereinigt_untergrenze']['mittel'])} on average) and lies above zero for {SW_K} of the {SW_N} seeds. "
               f"With {n(SW['n_boot'], nd=0)} draws, whether the unadjusted interval excludes zero therefore depends on the seed. The adjusted interval includes zero for every seed (lower bound {rng([SW['bereinigt_untergrenze']['min'], SW['bereinigt_untergrenze']['max']], lang)}, upper bound {rng([SW['bereinigt_obergrenze']['min'], SW['bereinigt_obergrenze']['max']], lang)}). "
               f"The gap between the unadjusted and the adjusted difference ({n(ep['raw'] - ep['detrended'])} percentage points) is, up to rounding, the drift extended over the effect days actually measured ({n(DRI['total']['mean'])}); under the pre-registration the adjusted difference is the one that counts. "
               f"The one-sided CUSUM of the headline raises an upward alarm on {dt(alarm_day, lang)}. Residuals range from {rng([TM['total']['residuals'][r['d']]['resid'] for r in BOTH], lang)} on the days with both providers and from {rng([TM['total']['residuals'][r['d']]['resid'] for r in ONLY], lang)} percentage points on the days with OpenAI alone; the alarm thus coincides with the basis change (assessment in section 7). No day exceeds the 95 percent prediction limit.")
    assert TM['total']['first_above_pi95'] is None
    mark('[[ERGEBNIS: Kopfzahl je Ankertag im Wirkungsfenster' if de else '[[RESULT: headline per anchor day in the effect window', txt)

    # Abschnitt 5: Kanalverlauf
    def pr(p, ch):
        xs = pvals(p, ch); return rng(xs, lang), n(mean(xs))
    parts = []
    for p in P:
        d_, lt, ds = pr(p, 'direct'), pr(p, 'longtail'), pr(p, 'discovery')
        if de:
            parts.append(f"{p} ({n_eff[p]} Tage): Direkt {d_[0]} (Mittel {d_[1]}), Saga-Wissen {lt[0]} (Mittel {lt[1]}), Empfehlung {ds[0]} (Mittel {ds[1]})")
        else:
            parts.append(f"{p} ({n_eff[p]} days): Direct {d_[0]} (mean {d_[1]}), Saga knowledge {lt[0]} (mean {lt[1]}), Recommendation {ds[0]} (mean {ds[1]})")
    if de:
        txt = ('Spannweite der Kanäle an den Ankertagen des Wirkungsfensters, Prozent der höchstmöglichen Bewertung: ' + '; '.join(parts) + '. '
               'Der Kanal Saga-Wissen hat nur zwei Fragen und springt deshalb in Schritten von bis zu 50 Prozentpunkten. Im Empfehlungs-Kanal haben alle Antworten über null die volle Punktzahl; 10 Prozent entsprechen damit einer der zehn Antworten. OpenAI erreicht dort höchstens 10, Gemini höchstens 20 Prozent.')
    else:
        txt = ('Range of the channels on the anchor days of the effect window, percent of the maximum score: ' + '; '.join(parts) + '. '
               'The Saga knowledge channel has only two questions and therefore moves in steps of up to 50 percentage points. In the Recommendation channel every answer above zero has full points, so 10 percent equals one of the ten answers. OpenAI reaches at most 10 percent there, Gemini at most 20.')
    assert max(pvals('OpenAI', 'discovery')) <= 10.0 and max(pvals('Gemini', 'discovery')) <= 20.0
    # jede positive Empfehlungs-Antwort hat volle Punkte: Trefferquote == Punktwert je Anbieter-Tag
    assert all(r[p]['discovery'] == r[p]['hit_discovery'] for r in EFF for p in P if r[p].get('state') == 'vollstaendig')
    for p in P:   # Mittel aus den Tageswerten stimmen mit effect_window überein (Rundung vor dem Mitteln)
        assert all(abs(mean(pvals(p, ch)) - EW[ch]['providers'][p]['mean']) <= 0.011 for ch in ('direct', 'longtail', 'discovery'))
    mark('[[ERGEBNIS: Verlauf der drei Kanäle im Wirkungsfenster je Anbieter.]]' if de else '[[RESULT: course of the three channels in the effect window per provider.]]', txt)

    # Tabelle 4
    t4 = table4(lang)
    for ch, row in zip(CH, t4):
        lab = LBL[lang][ch]
        old = f"| {lab} | " + ' | '.join([('[[ERGEBNIS]]' if de else '[[RESULT]]')] * 5) + ' |'
        rep(old, row)

    # Reihenfolge
    big = max(abs(E[ch]['detrended']) for ch in CH)
    if de:
        txt = (f"Keiner der beiden für die Reihenfolge-Hypothese maßgeblichen Kanäle alarmiert im Wirkungsfenster, weder nach CUSUM noch nach der Prognosegrenze; die Hypothese, dass der Direkt-Kanal vor dem Empfehlungs-Kanal reagiert, erhält damit keine Stütze. Mit dem vorregistrierten Empfehlungs-Kanal GR1 bis GR6 lautet das Urteil gleich. "
               f"Alle Schätzwerte liegen unter den Planungswerten der mindestens erkennbaren Verschiebung des jeweiligen Kanals (Kopfzahl {n(MDE['total'])}, Direkt {n(MDE['direct'])}, Saga-Wissen {n(MDE['longtail'])}, Empfehlung {n(MDE['discovery'])}, GR1 bis GR6 {n(MDE['recommend_gr'])}) und unter den Werten mit Drift-Unsicherheit (Abschnitt 3); der größte Betrag ist {n(big)} Prozentpunkte. "
               f"Eine Wirkung dieser Größe kann das Design nicht von null unterscheiden. Die Kanal-Differenzen von OpenAI und Gemini haben im Direkt-Kanal entgegengesetzte Vorzeichen (OpenAI {n(E['direct']['providers']['OpenAI']['detrended'], sign=True)}, Gemini {n(E['direct']['providers']['Gemini']['detrended'], sign=True)}), ebenso im Kanal Saga-Wissen (OpenAI {n(E['longtail']['providers']['OpenAI']['detrended'], sign=True)}, Gemini {n(E['longtail']['providers']['Gemini']['detrended'], sign=True)}).")
    else:
        txt = (f"Neither of the two channels that decide the order hypothesis raises an alarm in the effect window, by CUSUM or by the prediction limit; the hypothesis that the Direct channel responds before the Recommendation channel therefore receives no support. The verdict is the same with the pre-registered Recommendation channel GR1 to GR6. "
               f"All estimates lie below the planning values of the minimum detectable shift of their channel (headline {n(MDE['total'])}, Direct {n(MDE['direct'])}, Saga knowledge {n(MDE['longtail'])}, Recommendation {n(MDE['discovery'])}, GR1 to GR6 {n(MDE['recommend_gr'])}) and below the values that include the drift uncertainty (section 3); the largest absolute value is {n(big)} percentage points. "
               f"The design cannot distinguish an effect of this size from zero. The OpenAI and Gemini differences have opposite signs in the Direct channel (OpenAI {n(E['direct']['providers']['OpenAI']['detrended'], sign=True)}, Gemini {n(E['direct']['providers']['Gemini']['detrended'], sign=True)}) and in the Saga knowledge channel (OpenAI {n(E['longtail']['providers']['OpenAI']['detrended'], sign=True)}, Gemini {n(E['longtail']['providers']['Gemini']['detrended'], sign=True)}).")
    assert all(abs(E[ch]['detrended']) < MDE[ch] for ch in CH)
    assert all(TM[ch]['first_up_alarm'] is None and TM[ch]['first_above_pi95'] is None for ch in ('direct', 'discovery', 'recommend_gr', 'longtail'))
    assert D['hypothesis_order_gr1_gr6']['first_up_direct'] is None and D['hypothesis_order_gr1_gr6']['first_up_recommend_gr'] is None
    assert E['direct']['providers']['OpenAI']['detrended'] * E['direct']['providers']['Gemini']['detrended'] < 0
    assert E['longtail']['providers']['OpenAI']['detrended'] * E['longtail']['providers']['Gemini']['detrended'] < 0
    mark('[[ERGEBNIS: Reihenfolge der ersten Abweichungen' if de else '[[RESULT: order of the first deviations', txt)

    # Abschnitt 6: Claude
    mods_b = ', '.join(CB['models']); mods_a = ', '.join(CDAYS[c_anchor[0]]['models'])
    t5 = '\n'.join(table5(lang))
    lt_txt = ', '.join(f"{dt(k, lang)} ({n(CDAYS[k]['provider_mean']['longtail'])})" for k in c_lt_pos)
    son = win_0511[0]
    assert son['anbieter'] == model_of('2026-11-05', 'sonnet') and son['question_id'] == 'D1' and son['score_vorregistriert'] == 0
    # Eintrag 43 nach dem Wortlaut (nur Kennzeichnung): betroffene Claude-Antworten und Tageswerte
    C43 = CL['eintrag43_wortlaut']['days']
    assert sorted(C43) == sorted({e['d'] for e in SR['eintrag43_enger_umgesetzt']['zeilen'] if e['fenster'] == 'wirkung'}) and last_c in C43
    assert [a['rid'] for a in C43[last_c]['antworten']] == [son['rid']]
    fam = lambda m: next(f for f in ('Opus', 'Sonnet', 'Haiku') if f.lower() in m)
    for d_, x in C43.items():
        assert x['provider_mean']['total']['bewerter_vorregistriert'] == CDAYS[d_]['provider_mean']['total'] and x['provider_mean']['total']['wortlaut_eintrag43'] > CDAYS[d_]['provider_mean']['total']
    oth = [(d_, [fam(a['modell']) for a in x['antworten']]) for d_, x in sorted(C43.items()) if d_ != last_c]
    andj = lambda xs: (', '.join(xs[:-1]) + (' und ' if de else ' and ') + xs[-1]) if len(xs) > 1 else xs[0]
    if de:
        e43_other = (f"die Antworten von {andj(oth[0][1])} " + andj([f"am {dt(d_, lang)}" for d_, _ in oth]) if all(ms == oth[0][1] for _, ms in oth)
                     else andj([f"die Antworten von {andj(ms)} am {dt(d_, lang)}" for d_, ms in oth]))
        e43_days = andj([f"am {dt(d_, lang)} bei {n(x['provider_mean']['total']['wortlaut_eintrag43'])} statt {n(x['provider_mean']['total']['bewerter_vorregistriert'])}" for d_, x in sorted(C43.items())]) + ' Prozent'
    else:
        e43_other = (f"the answers of {andj(oth[0][1])} on " + andj([dt(d_, lang) for d_, _ in oth]) if all(ms == oth[0][1] for _, ms in oth)
                     else andj([f"the answers of {andj(ms)} on {dt(d_, lang)}" for d_, ms in oth]))
        e43_days = andj([f"{n(x['provider_mean']['total']['wortlaut_eintrag43'])} instead of {n(x['provider_mean']['total']['bewerter_vorregistriert'])} on {dt(d_, lang)}" for d_, x in sorted(C43.items())])
    e43_son = C43[last_c]['by_model'][son['anbieter']]['total']
    if de:
        txt = (f"Gemessen wurde je das neueste Modell der drei Familien: in der Grundlinienmessung am 7. Oktober {mods_b}, ab dem 9. Oktober {mods_a}. Bei Haiku wechselte damit das Modell zwischen Grundlinie und erstem Ankertag (Einträge 45 und 49); Opus und Sonnet blieben gleich. An jedem Tag liegen {CB['n_valid']} von 48 Antworten mit Messwert vor, das Register verzeichnet für Claude im Wirkungsfenster keinen Ausfall.\n\n"
               f"*Tabelle 5 · Claude auf claude.ai je Messtag: Mittel der drei Modelle je Kanal und Tageswert je Modell, Prozent der höchstmöglichen Bewertung.*\n\n{t5}\n\n"
               f"In der Grundlinienmessung lag der Tageswert bei {n(CB['provider_mean']['total'])} Prozent (Opus {n(CB['by_model'][model_of('2026-10-07', 'opus')]['total'])}, Sonnet {n(CB['by_model'][model_of('2026-10-07', 'sonnet')]['total'])}, Haiku {n(CB['by_model'][model_of('2026-10-07', 'haiku')]['total'])}). An den Ankertagen reichte er von {rng(c_tot, lang)}, im Direkt-Kanal von {rng(c_dir, lang)}. "
               f"Saga-Wissen lag nur am {lt_txt} über null, Empfehlung an keinem Tag. Am letzten Ankertag, dem {dt(last_c, lang)}, beträgt die Differenz zur Grundlinienmessung im Mittel {n(DD['claude_mittel']['total'], sign=True)} Prozentpunkte (Direkt {n(DD['claude_mittel']['direct'], sign=True)}); je Modell Opus {n(DD['opus']['total'], sign=True)}, Sonnet {n(DD['sonnet']['total'], sign=True)}, Haiku {n(DD['haiku']['total'], sign=True)}. "
               f"Auch die Claude-Werte folgen durchgehend dem Bewerter in der vorregistrierten Fassung; am {dt(last_c, lang)} ist dafür die Antwort von Sonnet auf die Frage D1 nach der Neubewertung am Volltext mit null Punkten gezählt. "
               f"Sie beschreibt den Autor zutreffend und grenzt ihn am Ende gegen Pauline Kael ab; dasselbe gilt für {e43_other} (Abschnitt 1). "
               f"Nach dem Wortlaut von Eintrag 43 erhielte jede dieser Antworten einen Punkt. Der Tageswert im Mittel der drei Modelle läge dann {e43_days}; Sonnet läge am {dt(last_c, lang)} bei {n(e43_son['wortlaut_eintrag43'])} statt {n(e43_son['bewerter_vorregistriert'])} Prozent. "
               f"Für Claude gibt es keine Signifikanzaussage. Die Tageswerte von Claude liegen an allen Tagen unter denen von OpenAI und Gemini.")
    else:
        txt = (f"Each family was measured with its newest model: {mods_b} in the baseline measurement on 7 October, {mods_a} from 9 October. For Haiku the model therefore changed between baseline and first anchor day (entries 45 and 49); Opus and Sonnet stayed the same. Each day has {CB['n_valid']} of 48 answers with values; the register lists no Claude outage in the effect window.\n\n"
               f"*Table 5 · Claude on claude.ai per measurement day: mean of the three models per channel and daily value per model, percent of the maximum score.*\n\n{t5}\n\n"
               f"In the baseline measurement the daily value was {n(CB['provider_mean']['total'])} percent (Opus {n(CB['by_model'][model_of('2026-10-07', 'opus')]['total'])}, Sonnet {n(CB['by_model'][model_of('2026-10-07', 'sonnet')]['total'])}, Haiku {n(CB['by_model'][model_of('2026-10-07', 'haiku')]['total'])}). On the anchor days it ranged from {rng(c_tot, lang)}, the Direct channel from {rng(c_dir, lang)}. "
               f"Saga knowledge was above zero only on {lt_txt}, Recommendation on no day. On the last anchor day, {dt(last_c, lang)}, the difference to the baseline measurement is {n(DD['claude_mittel']['total'], sign=True)} percentage points on average (Direct {n(DD['claude_mittel']['direct'], sign=True)}); per model Opus {n(DD['opus']['total'], sign=True)}, Sonnet {n(DD['sonnet']['total'], sign=True)}, Haiku {n(DD['haiku']['total'], sign=True)}. "
               f"The Claude values, too, follow the scorer in its pre-registered version throughout; on {dt(last_c, lang)} the Sonnet answer to question D1 therefore counts with zero points after re-scoring on the full text. "
               f"It describes the author correctly and distinguishes him from Pauline Kael at the end; the same holds for {e43_other} (section 1). "
               f"Under the wording of entry 43 each of these answers would score one point. The daily value as the mean of the three models, in percent, would then be {e43_days}; Sonnet would be at {n(e43_son['wortlaut_eintrag43'])} instead of {n(e43_son['bewerter_vorregistriert'])} percent on {dt(last_c, lang)}. "
               f"There is no significance statement for Claude. Claude's daily values are below those of OpenAI and Gemini on every day.")
    assert max(c_tot) < min(pvals('OpenAI', 'total') + pvals('Gemini', 'total'))
    mark('[[ERGEBNIS: Modellkennung, Grundlinienmessung am 7. Oktober' if de else '[[RESULT: model label, baseline measurement on 7 October', txt)

    # Abschnitt 7: Trefferquote
    hp = lambda ch: E['hit_' + ch]
    dr = D['direct_effect_rule']['primary']; rr = D['robustness_rule']['primary']
    assert dr['verdict'] == 'kein_effekt' and not any(v['robust'] for v in rr.values())
    hk = ['hit_direct', 'hit_longtail', 'hit_discovery', 'hit_recommend_gr']
    assert all(TM[k]['first_up_alarm'] is None and TM[k].get('first_down_alarm') is None for k in hk)          # Trefferquote: alle Kanäle aus results.json
    hs = [TM[k]['max_s_up'] for k in hk]; h_ = DEF['cusum_h_sd']
    assert max(hs) < h_ and TM['hit_total']['first_up_alarm'] == alarm_day
    if de:
        txt = (f"Trefferquote, driftbereinigte Differenz Wirkungsfenster minus Grundlinie im Mittel beider Anbieter (Prozentpunkte, 95-%-Intervall): alle Fragen {pc(hp('total'))}, Direkt {pc(hp('direct'))}, Saga-Wissen {pc(hp('longtail'))}, Empfehlung {pc(hp('discovery'))}, GR1 bis GR6 {pc(hp('recommend_gr'))}. "
               f"Alle Intervalle enthalten die Null. Der CUSUM der Trefferquote über alle Fragen alarmiert wie die Kopfzahl am {dt(alarm_day, lang)} aufwärts, an einem Tag mit nur OpenAI; die Kanäle alarmieren nicht, ihre höchste CUSUM-Summe liegt zwischen {n(min(hs))} und {n(max(hs))} bei der Schwelle {num(h_, lang, nd=0)}. "
               f"Nach der Intervall-Regel ist in keinem Kanal ein Effekt robust, weil schon die Intervalle der Punkt-Differenzen die Null enthalten. Im Direkt-Kanal gibt es nach Änderung 3 keinen zu prüfenden Punkt-Effekt; der Schätzwert der Trefferquote ({n(dr['hit_estimate'], sign=True)}) wird deshalb nicht als Bestätigung gelesen.")
    else:
        txt = (f"Hit rate, drift-adjusted difference effect window minus baseline, mean of both providers (percentage points, 95 % interval): all questions {pc(hp('total'))}, Direct {pc(hp('direct'))}, Saga knowledge {pc(hp('longtail'))}, Recommendation {pc(hp('discovery'))}, GR1 to GR6 {pc(hp('recommend_gr'))}. "
               f"All intervals include zero. Like the headline, the CUSUM of the hit rate across all questions raises an upward alarm on {dt(alarm_day, lang)}, a day with OpenAI alone; the channels raise none, their highest CUSUM sum lies between {n(min(hs))} and {n(max(hs))} at the threshold {num(h_, lang, nd=0)}. "
               f"Under the interval rule no channel shows a robust effect, because the intervals of the point differences already include zero. In the Direct channel there is no point effect to check under amendment 3; the hit-rate estimate ({n(dr['hit_estimate'], sign=True)}) is therefore not read as confirmation.")
    assert all(not excl0(hp(ch)['ci95_detrended']) for ch in CH)
    mark('[[ERGEBNIS: Trefferquote je Kanal' if de else '[[RESULT: hit rate by channel', txt)

    # Sensitivität: Grundlinie 8.–29.9., Bewertungsregeln vom 2.11.
    def provider_hits(lang_):
        out = []
        for nm, EE in (('primary', E), ('sensitivity', ES)):
            for pre_, lab in (('', TXT[lang_]), ('hit_', HTXT[lang_])):
                for ch in CH:
                    for p in P:
                        x = EE[pre_ + ch]['providers'][p]
                        if excl0(x['ci95_detrended']):
                            out.append((nm, pre_, ch, p, x))
        return out
    ph = provider_hits(lang)
    assert ph and all(o[0] == 'sensitivity' for o in ph)          # nur gegen die Sensitivitäts-Grundlinie
    raw_ex = [(nm, k, EE[k]) for nm, EE in (('primary', E), ('sensitivity', ES)) for k in [pre_ + ch for pre_ in ('', 'hit_') for ch in CH] if excl0(EE[k]['ci95_raw'])]
    assert all(v['detrended'] < v['raw'] for _, _, v in raw_ex)
    def lab_of(k, lang_):
        return (('Trefferquote ' if lang_ == 'de' else 'hit rate ') + HTXT[lang_][k[4:]]) if k.startswith('hit_') else TXT[lang_][k]
    def ph_item(o):
        nm, pre_, ch, p, x = o
        if de:
            return f"{p}, {'Trefferquote ' + HTXT['de'][ch] if pre_ else TXT['de'][ch] + ' in Punkten'} {n(x['detrended'], sign=True)} ({c(x['ci95_detrended'])})"
        return f"{p}, {'hit rate ' + HTXT['en'][ch] if pre_ else TXT['en'][ch] + ' in points'} {n(x['detrended'], sign=True)} ({c(x['ci95_detrended'])})"
    def andjoin(xs):
        return (', '.join(xs[:-1]) + (' und ' if de else ' and ') + xs[-1]) if len(xs) > 1 else xs[0]
    raw_p = andjoin([f"{lab_of(k, lang)} {pr_(v)}" for nm, k, v in raw_ex if nm == 'primary'])
    raw_s = andjoin([f"{lab_of(k, lang)} {pr_(v)}" for nm, k, v in raw_ex if nm == 'sensitivity'])
    bl71 = R71['baseline_balanced_mean']['total']
    assert bl71 == S71['baseline']['baseline']['total']['provider_balanced_mean'] and R71['timing']['total']['first_up_alarm'] == '2026-10-30'
    assert R71['effects_primary']['total']['detrended'] == s71['detrended']
    a71 = R71['timing']['total']['first_up_alarm']
    nb_web = sum(1 for e in SN['baseline'] if e['table'] == 'web_rows'); nb_all = len(SN['baseline'])
    BA = SR['nachtrag_eintraege']['baseline_auszug_aufteilung']
    assert BA['openai_gemini'] == nb_web and BA['openai_gemini'] + BA['claude_aeltere_reihe'] + BA['claude_grundlinie_0710'] == nb_all
    assert BA['openai_gemini_ankertage_gewertet'] + BA['openai_gemini_nicht_gewertet'] == nb_web and BA['openai_gemini_nicht_gewertet'] == BA['openai_gemini_nicht_gewertet_zwischentage']
    assert sum(BA['openai_gemini_ankertage_je_anbieter'].values()) == BA['openai_gemini_ankertage_gewertet']
    ba_p = ', '.join(f"{p} {BA['openai_gemini_ankertage_je_anbieter'][p]}" for p in ('Gemini', 'OpenAI') if p in BA['openai_gemini_ankertage_je_anbieter'])
    assert nb_all == SR['nachtrag_eintraege']['baseline_auszug_500_zeichen'] and all(e['d'] < '2026-10-08' for e in SN['baseline'])
    if de:
        txt = (f"Gegen die Sensitivitäts-Grundlinie vom 8. bis 29. September (OpenAI {COV['sensitivity']['OpenAI']['complete']}, Gemini {COV['sensitivity']['Gemini']['complete']} Ankertage) betragen die driftbereinigten Differenzen: Kopfzahl {pc(ES['total'])}, Direkt {pc(ES['direct'])}, Saga-Wissen {pc(ES['longtail'])}, Empfehlung {pc(ES['discovery'])}, GR1 bis GR6 {pc(ES['recommend_gr'])}. "
               f"Auch hier schließt kein Intervall im Mittel beider Anbieter die Null aus. Für einzelne Anbieter schließen driftbereinigt nur diese Intervalle die Null aus, alle gegen die Sensitivitäts-Grundlinie: {'; '.join(ph_item(o) for o in ph)}. Die Entscheidung der Vorregistrierung stützt sich auf das Mittel beider Anbieter. "
               f"Ohne Driftabzug schließen in der Hauptanalyse die Intervalle für {raw_p} die Null aus, gegen die Sensitivitäts-Grundlinie die für {raw_s}; bei der Kopfzahl der Hauptanalyse hängt das vom Startwert ab (Abschnitt 4). Maßgeblich ist nach der Vorregistrierung die driftbereinigte Differenz; die Driftbereinigung verkleinert jeden dieser Werte. "
               f"Mit den Bewertungsregeln vom 2. November in Grundlinie und Wirkungsfenster (Eintrag 71) ergeben sich Kopfzahl {pc(E71['total'])}, Direkt {pc(E71['direct'])} und Saga-Wissen {pc(E71['longtail'])}; die Grundlinie der Kopfzahl liegt dann bei {n(bl71)} statt {n(bal)} Prozent. "
               f"In Driftbasis und Grundlinie sind die neuen Regeln dabei nur am gespeicherten Auszug von 500 Zeichen angewendet. Das ändert {nb_all} gespeicherte Antworten: {nb_web} von OpenAI und Gemini, {BA['claude_aeltere_reihe']} aus der älteren Claude-Reihe und {W[BA['claude_grundlinie_0710']]} aus der Claude-Grundlinienmessung vom 7. Oktober. "
               f"In die Kennzahlen von OpenAI und Gemini gehen davon {BA['openai_gemini_ankertage_gewertet']} ein, die auf Ankertagen liegen ({ba_p}); die übrigen {BA['openai_gemini_nicht_gewertet']} liegen auf Zwischentagen, die nicht ausgewertet werden (Abschnitt 2). Vor dem 15. September bleibt der damals gültige Termin 22. September gewertet. Mit diesen Regeln alarmiert der CUSUM der Kopfzahl schon am {dt(a71, lang)}. Die Entscheidung bleibt gleich. "
               f"Der Abgleich des Grundlinienbestands mit dem Abzug vom 8. November ergibt keine fehlenden, geänderten oder neuen Zeilen (Abschnitt 2).")
    else:
        txt = (f"Against the sensitivity baseline of 8 to 29 September (OpenAI {COV['sensitivity']['OpenAI']['complete']}, Gemini {COV['sensitivity']['Gemini']['complete']} anchor days) the drift-adjusted differences are: headline {pc(ES['total'])}, Direct {pc(ES['direct'])}, Saga knowledge {pc(ES['longtail'])}, Recommendation {pc(ES['discovery'])}, GR1 to GR6 {pc(ES['recommend_gr'])}. "
               f"Here too no interval of the two-provider mean excludes zero. For single providers only these drift-adjusted intervals exclude zero, all against the sensitivity baseline: {'; '.join(ph_item(o) for o in ph)}. The pre-registered decision rests on the mean of both providers. "
               f"Without drift removal, the intervals for {raw_p} exclude zero in the main analysis, and those for {raw_s} against the sensitivity baseline; for the headline of the main analysis this depends on the seed (section 4). Under the pre-registration the drift-adjusted difference is the one that counts; drift adjustment reduces each of these values. "
               f"With the scoring rules of 2 November applied to baseline and effect window (entry 71) the results are headline {pc(E71['total'])}, Direct {pc(E71['direct'])} and Saga knowledge {pc(E71['longtail'])}; the headline baseline is then {n(bl71)} instead of {n(bal)} percent. "
               f"In drift base and baseline the new rules were applied to the stored 500-character excerpt only. This changes {nb_all} stored answers: {nb_web} from OpenAI and Gemini, {BA['claude_aeltere_reihe']} from the earlier Claude series and {W[BA['claude_grundlinie_0710']]} from the Claude baseline measurement of 7 October. "
               f"Of these, {BA['openai_gemini_ankertage_gewertet']} enter the OpenAI and Gemini metrics because they lie on anchor days ({ba_p}); the other {BA['openai_gemini_nicht_gewertet']} lie on intermediate days, which are not analysed (section 2). Before 15 September the then valid release date of 22 September still counts. Under these rules the CUSUM of the headline raises an alarm as early as {dt(a71, lang)}. The decision is unchanged. "
               f"Comparing the baseline holdings with the pull of 8 November finds no missing, changed or new rows (section 2).")
    assert all(not excl0(ES[ch]['ci95_detrended']) for ch in CH)
    assert all(not excl0(E71[ch]['ci95_detrended']) for ch in CH)
    assert ES['total']['detrended'] < ES['total']['raw'] and E['total']['detrended'] < E['total']['raw']
    mark('[[ERGEBNIS: Differenzen gegen die Sensitivitäts-Grundlinie' if de else '[[RESULT: differences against the sensitivity baseline', txt)

    # Sensitivität leere Antworten (Eintrag 66)
    LA = SENS['leere_antworten']['leere_antworten']; jf = LA['je_fenster_ankertage']
    anchor_days = {r['d'] for r in D['anchor_table']}
    leer_anchor = [r for r in LEER['rows'] if r['d'] in anchor_days]
    assert LA['auf_ankertagen'] == len(leer_anchor) == jf['cusum_ref'] + jf['baseline'] + jf['effect'] and jf['delayed'] == 0
    assert LA['je_anbieter_ankertage'] == {'Gemini': LA['auf_ankertagen']} and LA['gesamt'] == LEER['n']
    assert max(r['d'] for r in leer_anchor) < '2026-11-01'
    LE = LU['effects_primary']
    assert all(not excl0(LE[k]['ci95_detrended']) for k in LE)
    assert all(v['first_up_alarm'] is None and v.get('first_down_alarm') is None for v in LU['timing'].values())
    assert LU['hypothesis_order']['verdict'] == LU['hypothesis_order_gr1_gr6']['verdict'] == 'keine_abweichung'
    assert LU['coverage']['effect']['Gemini']['complete'] == n_eff['Gemini'] and LU['coverage']['baseline']['Gemini']['complete'] == ge['n_anchor_days']
    FC = FE['coverage']; FT = FE['timing']
    fe_days = [d for d in [r['d'] for r in EFF] if d not in FC['effect']['Gemini']['not_complete']]
    assert len(fe_days) == FC['effect']['Gemini']['complete'] == 1
    assert FE['effects_primary']['total']['providers']['Gemini']['ci95_detrended'] is None and FE['effects_primary']['total']['providers']['OpenAI']['ci95_detrended'] == op['ci95_detrended']
    assert FT['direct']['first_up_alarm'] is None and FT['discovery']['first_up_alarm'] == FT['recommend_gr']['first_up_alarm'] == alarm_day and FT['total']['first_up_alarm'] == FT['hit_total']['first_up_alarm'] == '2026-10-30'
    assert {k for k, v in FT.items() if v.get('first_up_alarm')} == {'total', 'hit_total', 'discovery', 'recommend_gr'} and not any(v.get('first_down_alarm') for v in FT.values())
    assert FE['hypothesis_order']['verdict'] == FE['hypothesis_order_gr1_gr6']['verdict'] == 'empfehlung_frueher'
    fpt = FE['effects_primary']['total']['detrended']
    if de:
        txt = (f"Leere Antworten. Vor dem 1. November gehen sie als Antwort ohne Fund mit null Punkten ein (Eintrag 66). Auf den Ankertagen sind das {LA['auf_ankertagen']} Antworten, alle von Gemini: {jf['cusum_ref']} in der Driftbasis, {jf['baseline']} in der Grundlinie und {jf['effect']} im Wirkungsfenster; bei OpenAI gab es auf Ankertagen keine leere Antwort. "
               f"Als Lücke gewertet fehlt die Frage an diesem Tag, und der Tageswert wird aus den übrigen Fragen gebildet. Dann beträgt die Differenz der Kopfzahl {pc(LE['total'])}, unbereinigt {pr_(LE['total'])}; Direkt {pc(LE['direct'])}, Saga-Wissen {pc(LE['longtail'])}, Empfehlung {pc(LE['discovery'])}, GR1 bis GR6 {pc(LE['recommend_gr'])}. "
               f"Weder die Kopfzahl noch ein Kanal oder eine Trefferquote alarmiert, der Alarm der Hauptanalyse am {dt(alarm_day, lang)} entfällt also, und die Entscheidung bleibt gleich. "
               f"Als Fehlmessung gewertet ist der Anbieter-Tag unvollständig und entfällt. Gemini bleiben dann {FC['cusum_ref']['Gemini']['complete']} Ankertage in der Driftbasis, {FC['baseline']['Gemini']['complete']} in der Grundlinie und {W[1]}r im Wirkungsfenster ({dt(fe_days[0], lang)}); für Gemini lässt sich kein Intervall berechnen, und der Schätzwert der Kopfzahl im Mittel beider Anbieter ({n(fpt, sign=True)}) ist nicht deutbar. "
               f"In dieser Variante alarmiert der CUSUM der Kopfzahl und der Trefferquote über alle Fragen am {dt(FT['total']['first_up_alarm'], lang)}, der des Empfehlungs-Kanals und der Fragen GR1 bis GR6 am {dt(FT['discovery']['first_up_alarm'], lang)}; der Direkt-Kanal alarmiert nicht. Der Empfehlungs-Kanal reagiert damit vor dem Direkt-Kanal, und die Reihenfolge-Hypothese erhält auch hier keine Stütze. Wegen der wenigen verbleibenden Gemini-Tage ist diese Variante nicht aussagekräftig.")
    else:
        txt = (f"Empty answers. Before 1 November they enter as answers without a finding, with zero points (entry 66). On the anchor days these are {LA['auf_ankertagen']} answers, all from Gemini: {jf['cusum_ref']} in the drift base, {jf['baseline']} in the baseline and {jf['effect']} in the effect window; OpenAI gave no empty answer on anchor days. "
               f"Treated as gaps, the question is missing on that day and the daily value is formed from the remaining questions. The headline difference is then {pc(LE['total'])}, unadjusted {pr_(LE['total'])}; Direct {pc(LE['direct'])}, Saga knowledge {pc(LE['longtail'])}, Recommendation {pc(LE['discovery'])}, GR1 to GR6 {pc(LE['recommend_gr'])}. "
               f"Neither the headline nor any channel or hit rate raises an alarm, so the alarm of the main analysis on {dt(alarm_day, lang)} disappears, and the decision is unchanged. "
               f"Treated as failed measurements, the provider-day is incomplete and drops out. Gemini then keeps {FC['cusum_ref']['Gemini']['complete']} anchor days in the drift base, {FC['baseline']['Gemini']['complete']} in the baseline and {W[1]} in the effect window ({dt(fe_days[0], lang)}); no interval can be computed for Gemini, and the headline estimate as the mean of both providers ({n(fpt, sign=True)}) cannot be interpreted. "
               f"In this variant the CUSUM of the headline and of the hit rate across all questions raises an alarm on {dt(FT['total']['first_up_alarm'], lang)}, those of the Recommendation channel and of questions GR1 to GR6 on {dt(FT['discovery']['first_up_alarm'], lang)}; the Direct channel raises none. The Recommendation channel thus responds before the Direct channel, and the order hypothesis receives no support here either. This variant is not informative because so few Gemini days remain.")
    mark(f'{pref}: leere Antworten als Lücke' if de else f'{pref}: empty answers as gaps', txt)

    # Sensitivität ohne Änderung 4 (Eintrag 50)
    OE = O4['effects_primary']
    for k in ('direct', 'discovery', 'recommend_gr'):
        assert OE[k]['detrended'] == E[k]['detrended'] and OE[k]['ci95_detrended'] == E[k]['ci95_detrended'], k
    assert all(not excl0(OE[k]['ci95_detrended']) for k in OE) and not excl0(OE['total']['ci95_raw'])
    assert O4['timing']['total']['first_up_alarm'] == alarm_day and O4['hypothesis_order']['verdict'] == O4['hypothesis_order_gr1_gr6']['verdict'] == 'keine_abweichung'
    TA = O4['volltextpruefung_titelanker']; ta1 = TA['nur_vorregistriert_ueber_null']
    assert TA == {'datei': 'data/results_erweiterung_0811.json', **EXT['titelanker_pruefung']} and TA['zeitraum'] == ['2026-10-18', '2026-11-08']
    assert '54 nennen den Autor namentlich, 2 Direkt-Antworten zu D3' in O4['beschreibung'] and 'Claude nicht geprüft' in O4['beschreibung']
    assert 54 + 2 == TA['ueber_null_messdatenbank'] and len(ta1) == 1 and TA['ueber_null_vorregistriert'] == TA['ueber_null_messdatenbank'] + 1
    assert ta1[0]['question_id'] == 'R1' and ta1[0]['status'] == 'name_only_echo' and ta1[0]['score'] == 0.5 and ta1[0]['anbieter'] == 'openai_search'
    if de:
        txt = (f"Ohne Änderung 4. Werden die beiden am 15. Oktober rückwirkend geänderten Antworten vom 12. Oktober wieder mit null Punkten gezählt, beträgt die Differenz der Kopfzahl {pc(OE['total'])}, unbereinigt {pr_(OE['total'])}, und im Kanal Saga-Wissen {pc(OE['longtail'])}; Direkt, Empfehlung und GR1 bis GR6 bleiben gleich. "
               f"Das unbereinigte Intervall der Kopfzahl schließt die Null in der Hauptanalyse also nur wegen dieser einen Gemini-Antwort aus, und auch dann nicht bei jedem Startwert (Abschnitt 4). Der CUSUM-Alarm der Kopfzahl am {dt(alarm_day, lang)} bleibt, und die Entscheidung ändert sich nicht. "
               f"Durchgesehen wurden die Volltexte aller {TA['ueber_null_vorregistriert']} Antworten von OpenAI und Gemini, die an den Ankertagen vom 18. Oktober bis 8. November nach den vorregistrierten Regeln Punkte über null haben. 54 nennen den Autor namentlich, 2 Direkt-Antworten zur Frage D3 nennen ihn über die Domain, und eine Antwort von OpenAI zur Frage R1 vom {dt(ta1[0]['d'], lang)} erhält einen halben Punkt, weil sie das Wort Marin aus der Frage wiederholt; nach den Werten der Messdatenbank hat sie null Punkte, dort sind es {TA['ueber_null_messdatenbank']} Antworten. "
               f"Keine weitere Antwort hängt damit allein am Titel als Anker; für D2 und D3 gilt der Titel-Anker ohnehin nicht. Für Claude wurde das nicht geprüft.")
    else:
        txt = (f"Without amendment 4. If the two answers of 12 October that were changed retroactively on 15 October count with zero points again, the headline difference is {pc(OE['total'])}, unadjusted {pr_(OE['total'])}, and {pc(OE['longtail'])} in the Saga knowledge channel; Direct, Recommendation and GR1 to GR6 are unchanged. "
               f"In the main analysis the unadjusted headline interval therefore excludes zero only because of this one Gemini answer, and even then not for every seed (section 4). The CUSUM alarm of the headline on {dt(alarm_day, lang)} remains, and the decision does not change. "
               f"The full texts of all {TA['ueber_null_vorregistriert']} OpenAI and Gemini answers that score above zero under the pre-registered rules on the anchor days from 18 October to 8 November were reviewed. 54 name the author, 2 Direct answers to question D3 identify him through the domain, and one OpenAI answer to question R1 of {dt(ta1[0]['d'], lang)} receives half a point because it repeats the word Marin from the question; under the values in the measurement database it scores zero, and there are {TA['ueber_null_messdatenbank']} answers. "
               f"No further answer therefore depends on the title as anchor alone; for D2 and D3 the title anchor does not apply anyway. This was not checked for Claude.")
    mark(f'{pref}: Auswertung ohne Änderung 4' if de else f'{pref}: analysis without amendment 4', txt)

    # Zusatzangaben, nicht vorregistriert
    assert ZU['status'] == 'zusatzangaben_nicht_vorregistriert'
    TB = ZU['tage_beide_anbieter']; tbt = TB['effects']['total']
    assert TB['n_days'] == len(BOTH) and tbt['detrended'] < 0 < ep['detrended'] and tbt['providers']['Gemini']['detrended'] == gp['detrended']
    HA = ZU['haelften_gegen_driftgerade']['OpenAI']['total']; h1, h2 = HA['erste_haelfte'], HA['zweite_haelfte']
    assert h1['anchor_days'] == [BOTH[0]['d'], BOTH[-1]['d']] and h2['anchor_days'] == [ONLY[0]['d'], ONLY[-1]['d']] and h1['n'] == h2['n'] == 5
    CK = ZU['cusum_streuung_kritisch']['total']
    assert CK['first_up_alarm'] == alarm_day and CK['h'] == h_ and CK['max_s_up'] == TM['total']['max_s_up'] and CK['sd_used'] < CK['alarm_solange_sd_unter']
    if de:
        txt = (f"Zusatzangaben, nicht vorregistriert. Beschränkt auf die {TB['n_days']} Ankertage mit beiden Anbietern ({dt(BOTH[0]['d'], lang)} bis {dt(BOTH[-1]['d'], lang)}) liegt die Kopfzahl driftbereinigt bei {pc(tbt)}, unbereinigt bei {pr_(tbt)}; der positive Schätzwert der Hauptanalyse stammt damit aus den späteren Tagen, an denen nur OpenAI misst. "
               f"Gegen die eigene Driftgerade liegt OpenAI in der ersten Hälfte des Wirkungsfensters ({dt(h1['anchor_days'][0], lang)} bis {dt(h1['anchor_days'][1], lang)}) im Mittel bei {n(h1['mean_resid'], sign=True)}, in der zweiten ({dt(h2['anchor_days'][0], lang)} bis {dt(h2['anchor_days'][1], lang)}) bei {n(h2['mean_resid'], sign=True)} Prozentpunkten. "
               f"Der CUSUM-Alarm der Kopfzahl am {dt(alarm_day, lang)} ist knapp: Die höchste Summe beträgt {n(CK['max_s_up'])} bei der Schwelle {num(CK['h'], lang, nd=0)}. Er tritt nur auf, solange die Standardabweichung, mit der standardisiert wird, unter {n(CK['alarm_solange_sd_unter'], nd=3)} liegt; verwendet wurde die nach dem vorab festgelegten Verfahren aus der Grundlinie berechnete {n(CK['sd_used'], nd=3)}. "
               f"Mit den Bewertungsregeln vom 2. November alarmiert die Kopfzahl schon am {dt(a71, lang)}. Die Entscheidung über die Nullhypothese hängt nicht an diesem Alarm.")
    else:
        txt = (f"Additional figures, not pre-registered. Restricted to the {TB['n_days']} anchor days with both providers ({dt(BOTH[0]['d'], lang)} to {dt(BOTH[-1]['d'], lang)}) the headline is {pc(tbt)} drift-adjusted and {pr_(tbt)} unadjusted; the positive estimate of the main analysis thus comes from the later days on which OpenAI measures alone. "
               f"Against its own drift line OpenAI averages {n(h1['mean_resid'], sign=True)} percentage points in the first half of the effect window ({dt(h1['anchor_days'][0], lang)} to {dt(h1['anchor_days'][1], lang)}) and {n(h2['mean_resid'], sign=True)} in the second ({dt(h2['anchor_days'][0], lang)} to {dt(h2['anchor_days'][1], lang)}). "
               f"The CUSUM alarm of the headline on {dt(alarm_day, lang)} is narrow: the highest sum is {n(CK['max_s_up'])} at the threshold {num(CK['h'], lang, nd=0)}. It occurs only while the standard deviation used for standardisation is below {n(CK['alarm_solange_sd_unter'], nd=3)}; the value used, computed from the baseline by the procedure fixed in advance, is {n(CK['sd_used'], nd=3)}. "
               f"Under the scoring rules of 2 November the headline raises an alarm as early as {dt(a71, lang)}. The decision on the null hypothesis does not depend on this alarm.")
    mark(f'{pref}: Zusatzangaben, nicht vorregistriert' if de else f'{pref}: additional figures, not pre-registered', txt)

    # Beobachtung
    if de:
        txt = (f"Die Beobachtung verzögerter Wirkung umfasst {COV['delayed']['anchor_days']} Ankertage vom {dt(COV['delayed']['first'], lang)} bis {dt(COV['delayed']['last'], lang, True)}. In der Hauptanalyse ist keiner davon ausgewertet; den ersten, den {dt(COV['delayed']['first'], lang)}, zählt nur die nicht vorregistrierte Erweiterung im folgenden Unterabschnitt zum Wirkungsfenster. "
               f"Die Beobachtung wird nach dem 6. Januar 2027 eingefroren und als Nachtrag beschreibend berichtet; eine neue Signifikanzaussage folgt daraus nicht.")
    else:
        txt = (f"The delayed-effect observation covers {COV['delayed']['anchor_days']} anchor days from {dt(COV['delayed']['first'], lang)} to {dt(COV['delayed']['last'], lang, True)}. None of them is analysed in the main analysis; only the extension in the following subsection, which is not pre-registered, counts the first of them, {dt(COV['delayed']['first'], lang)}, as part of the effect window. "
               f"The observation will be frozen after 6 January 2027 and reported descriptively as an addendum; it does not lead to a new significance statement.")
    mark('[[ERGEBNIS: Stand der Beobachtung verzögerter Wirkung' if de else '[[RESULT: state of the delayed-effect observation', txt)

    # Erweiterung bis 08.11. (Eintrag 83, nicht vorregistriert)
    assert EXT['status'] == 'nicht_vorregistriert' and EXT['register_entry'] == 83 and XF['variante']['status'] == 'nicht_vorregistriert'
    abz = XFZ['abzug']
    assert 'OpenAI nachgemessen 14:24 UTC' in abz and 'Gemini nachgemessen 15:48 UTC' in abz
    assert REG[83]['recorded_at'] == '2026-11-08 15:52:51' and REG[82]['recorded_at'] == '2026-11-08 14:30:34'
    assert EXT['register_recorded_at'] == '2026-11-08' and EXT['register_recorded_at_utc'] == REG[83]['recorded_at']
    x83 = EXT['register_recorded_at_utc'][11:16]
    assert all(e['d'] == '2026-11-08' for e in win_0811) and sorted(e['table'] for e in win_0811) == ['claude_web_rows', 'claude_web_rows', 'web_rows']
    g0811 = SN['nachtrag_2026-11-08']['geprueft']['2026-11-08']
    assert g0811['openai_search'] == 16 and g0811['gemini'] == 16 and g0811['claude'] == 48
    A8 = EXT['anchor_0811']
    assert A8['d'] == '2026-11-08' and A8['basis'] == 'beide' and A8['OpenAI']['state'] == A8['Gemini']['state'] == 'vollstaendig'
    if de:
        txt = (f"Nach dem Ende des Wirkungsfensters habe ich entschieden, zusätzlich zur vorregistrierten Hauptanalyse eine Erweiterung des Wirkungsfensters bis einschließlich des Ankertages 8. November zu berichten (Eintrag 83). Anlass ist die Gemini-Messung dieses Tages: Gemini fehlte an den letzten {W[len(gem_missing)]} Ankertagen des Wirkungsfensters, am 8. November ist es wieder gemessen. "
               f"Die Erweiterung ist nicht vorregistriert. Hypothese, Nullhypothese, Kennzahlen, Driftbereinigung, Bewertungsregeln und Entscheidungsregel bleiben unverändert, und über die Hypothesen entscheidet allein die Hauptanalyse mit dem Wirkungsfenster bis 7. November. Nach der Vorregistrierung gehört der 8. November zur Beobachtung verzögerter Wirkung. "
               f"Am Morgen des 8. November lehnten beide Schnittstellen alle Fragen ab (Einträge 80 und 81). Nachgemessen wurden OpenAI um 14:24 UTC nach der Nachhol-Regel aus Eintrag 44 und Gemini um 15:48 UTC nach der Nachhol-Regel aus Eintrag 82, die am selben Tag um 14:30 UTC vor ihrer ersten Anwendung erfasst wurde. Die Erweiterung selbst ist im Register um {x83} UTC erfasst, nach beiden Nachmessungen; sie ist deshalb als nachträgliche Auswertung zu lesen. "
               f"Die Gemini-Lücken vom {dt(gem_missing[0], lang)} bis {dt(gem_missing[-1], lang)} werden nicht nachgemessen. Grundlage ist der dritte Abzug vom 8. November (Abschnitt 2). Die {g0811['openai_search'] + g0811['gemini'] + g0811['claude']} Antworten des 8. November sind am Volltext nach den vorregistrierten Regeln bewertet; {W[len(win_0811)]} davon weichen vom Wert der Messdatenbank ab, keine von Gemini, und zusammen mit den {W[SR['overrides']]} der Hauptanalyse setzt die Erweiterung {EXT['scorer_overrides']} Antworten zurück. "
               f"Gerechnet wird mit demselben Verfahren und demselben Startwert wie in der Hauptanalyse.")
    else:
        txt = (f"After the effect window had closed I decided to report, in addition to the pre-registered main analysis, an extension of the effect window up to and including anchor day 8 November (entry 83). The reason is the Gemini measurement of that day: Gemini was missing on the last {W[len(gem_missing)]} anchor days of the effect window and is measured again on 8 November. "
               f"The extension is not pre-registered. Hypothesis, null hypothesis, metrics, drift removal, scoring rules and decision rule are unchanged, and the hypotheses are decided by the main analysis alone, with the effect window ending on 7 November. Under the pre-registration, 8 November belongs to the delayed-effect observation. "
               f"On the morning of 8 November both interfaces refused every question (entries 80 and 81). OpenAI was re-measured at 14:24 UTC under the catch-up rule of entry 44, and Gemini at 15:48 UTC under the catch-up rule of entry 82, which was recorded on the same day at 14:30 UTC before its first use. The extension itself was recorded in the register at {x83} UTC, after both re-measurements; it should therefore be read as a post-hoc analysis. "
               f"The Gemini gaps from {dt(gem_missing[0], lang)} to {dt(gem_missing[-1], lang)} are not re-measured. The basis is the third pull of 8 November (section 2). The {g0811['openai_search'] + g0811['gemini'] + g0811['claude']} answers of 8 November are scored on the full text under the pre-registered rules; {W[len(win_0811)]} of them differ from the value in the measurement database, none from Gemini, and together with the {W[SR['overrides']]} of the main analysis the extension resets {EXT['scorer_overrides']} answers. "
               f"The procedure and the seed are the same as in the main analysis.")
    mark(f'{pref}: Erweiterung, Begründung und Grundlage' if de else f'{pref}: extension, reason and basis', txt)
    mark(f'{pref}: Tabelle 6]]' if de else f'{pref}: table 6]]', '\n'.join(table6(lang)))

    ext_d = EXT['drift_implied_diff_pp']['total']
    assert ext_d['n_effect_days'] == {'OpenAI': EXC['effect']['OpenAI']['complete'], 'Gemini': EXC['effect']['Gemini']['complete']}
    assert all(not excl0(EXE[k]['ci95_detrended']) for k in EXE) and excl0(ex['ci95_raw']) and ex['ci95_raw'][0] > 0
    assert {k: v['first_up_alarm'] for k, v in EXT_T.items() if v['first_up_alarm']} == {'total': alarm_day, 'hit_total': alarm_day}
    assert EXT['hypothesis_order']['verdict'] == EXT['hypothesis_order_gr1_gr6']['verdict'] == 'keine_abweichung'
    assert EXT['direct_effect_rule']['verdict'] == 'kein_effekt' and not any(v['robust'] for v in EXT['robustness_rule'].values())
    assert EXC['effect']['both_complete'] == len(BOTH) + 1 and EXC['effect']['Gemini']['not_complete'] == gem_missing
    vg = EXT['vergleich_hauptanalyse']['total']; xsb = EXT['effects_sensitivity_baseline']['total']
    assert not excl0(xsb['ci95_detrended']) and vg['differenz'] > 0
    eo, eg = ex['providers']['OpenAI'], ex['providers']['Gemini']
    # Vollständig über alle Kennzahlen, wie in der Hauptanalyse: unbereinigte Intervalle ohne Null gegen Grundlinie und
    # Sensitivitäts-Grundlinie, driftbereinigte Einzelanbieter-Intervalle ohne Null
    XS = EXT['effects_sensitivity_baseline']; MK = [pre_ + ch for pre_ in ('', 'hit_') for ch in CH]
    assert all(not excl0(XS[k]['ci95_detrended']) for k in MK)
    x_raw = [(nm, k, EE[k]) for nm, EE in (('primary', EXE), ('sensitivity', XS)) for k in MK if excl0(EE[k]['ci95_raw'])]
    assert x_raw and all(v['detrended'] < v['raw'] for _, _, v in x_raw) and excl0(EXE['total']['ci95_raw'])
    x_ph = [(nm, pre_, ch, p, EE[pre_ + ch]['providers'][p]) for nm, EE in (('primary', EXE), ('sensitivity', XS)) for pre_ in ('', 'hit_') for ch in CH for p in P
            if excl0(EE[pre_ + ch]['providers'][p]['ci95_detrended'])]
    assert x_ph and all(o[0] == 'sensitivity' for o in x_ph)          # nur gegen die Sensitivitäts-Grundlinie
    x_raw_p = andjoin([f"{lab_of(k, lang)} {pr_(v)}" for nm, k, v in x_raw if nm == 'primary'])
    x_raw_s = andjoin([f"{lab_of(k, lang)} {pr_(v)}" for nm, k, v in x_raw if nm == 'sensitivity'])
    x_ph_s = '; '.join(ph_item(o) for o in x_ph)
    C8 = EXT['claude_0811']['provider_mean']
    if de:
        txt = (f"Am 8. November lag OpenAI bei {n(A8['OpenAI']['total'])} und Gemini bei {n(A8['Gemini']['total'])} Prozent, die Kopfzahl bei {n(A8['headline']['total'])} Prozent. Mit diesem Tag gehen für OpenAI {EXC['effect']['OpenAI']['complete']} und für Gemini {EXC['effect']['Gemini']['complete']} Wirkungs-Ankertage ein, die Kopfzahl ist an {EXC['effect']['both_complete']} Ankertagen definiert. "
               f"Driftbereinigt beträgt die Differenz der Kopfzahl bei OpenAI {pc(eo)}, bei Gemini {pc(eg)} und im Mittel {n(ex['detrended'], sign=True)} Prozentpunkte ({c(ex['ci95_detrended'])}); unbereinigt sind es im Mittel {pr_(ex)}, und die an den gemessenen Wirkungstagen fortgeschriebene Drift beträgt {n(ext_d['mean'])}. "
               f"Das Intervall der bereinigten Differenz enthält die Null. In den Kanälen und in der Trefferquote enthält jedes driftbereinigte Intervall im Mittel beider Anbieter die Null (Tabelle 6), auch gegen die Sensitivitäts-Grundlinie; dort beträgt die Differenz der Kopfzahl {pc(xsb)}. "
               f"Für einzelne Anbieter schließen driftbereinigt nur diese Intervalle die Null aus, alle gegen die Sensitivitäts-Grundlinie: {x_ph_s}. "
               f"Ohne Driftabzug schließen gegen die Grundlinie die Intervalle für {x_raw_p} die Null aus, gegen die Sensitivitäts-Grundlinie die für {x_raw_s}. Maßgeblich ist wie in der Hauptanalyse die driftbereinigte Differenz im Mittel beider Anbieter; die Driftbereinigung verkleinert jeden dieser Werte. "
               f"Der CUSUM alarmiert wie in der Hauptanalyse nur für die Kopfzahl und die Trefferquote über alle Fragen, beide am {dt(alarm_day, lang)}. Direkt und Empfehlung alarmieren nicht, auch nicht mit GR1 bis GR6, und die Reihenfolge-Hypothese erhält keine Stütze. Nach der Intervall-Regel ist in keinem Kanal ein Effekt robust, und im Direkt-Kanal gibt es keinen zu prüfenden Punkt-Effekt.\n\n"
               f"Gegenüber der Hauptanalyse steigt der Schätzwert der Kopfzahl um {n(vg['differenz'])} Prozentpunkte. Das Intervall enthält weiterhin die Null, und die Entscheidung über die Nullhypothese wäre dieselbe. "
               f"Für Gemini kommt ein einzelner Tag am Ende des Fensters hinzu; die Lücke vom {dt(gem_missing[0], lang)} bis {dt(gem_missing[-1], lang)} bleibt, und die Gemini-Differenz beruht weiterhin auf {W[n_eff['Gemini']]} Tagen der ersten Fensterhälfte und diesem einen Tag. "
               f"Claude lag am 8. November im Mittel der drei Modelle bei {n(C8['total'])} Prozent (Direkt {n(C8['direct'])}); dieser Wert ist beschreibend.")
    else:
        txt = (f"On 8 November OpenAI stood at {n(A8['OpenAI']['total'])} and Gemini at {n(A8['Gemini']['total'])} percent, the headline at {n(A8['headline']['total'])} percent. With this day OpenAI contributes {EXC['effect']['OpenAI']['complete']} and Gemini {EXC['effect']['Gemini']['complete']} effect anchor days, and the headline is defined on {EXC['effect']['both_complete']} anchor days. "
               f"Drift-adjusted, the headline difference is {pc(eo)} for OpenAI, {pc(eg)} for Gemini and {n(ex['detrended'], sign=True)} percentage points on average ({c(ex['ci95_detrended'])}); unadjusted it is {pr_(ex)} on average, and the drift extended over the effect days actually measured is {n(ext_d['mean'])}. "
               f"The interval of the adjusted difference includes zero. In the channels and in the hit rate every drift-adjusted interval of the two-provider mean includes zero (Table 6), also against the sensitivity baseline, where the headline difference is {pc(xsb)}. "
               f"For single providers only these drift-adjusted intervals exclude zero, all against the sensitivity baseline: {x_ph_s}. "
               f"Without drift removal, the intervals for {x_raw_p} exclude zero against the baseline, and those for {x_raw_s} against the sensitivity baseline. As in the main analysis, the drift-adjusted difference of the two-provider mean is the one that counts; drift adjustment reduces each of these values. "
               f"As in the main analysis, the CUSUM raises an alarm only for the headline and the hit rate across all questions, both on {dt(alarm_day, lang)}. Direct and Recommendation raise none, also with GR1 to GR6, and the order hypothesis receives no support. Under the interval rule no channel shows a robust effect, and in the Direct channel there is no point effect to check.\n\n"
               f"Compared with the main analysis the headline estimate rises by {n(vg['differenz'])} percentage points. The interval still includes zero, and the decision on the null hypothesis would be the same. "
               f"For Gemini a single day is added at the end of the window; the gap from {dt(gem_missing[0], lang)} to {dt(gem_missing[-1], lang)} remains, and the Gemini difference still rests on {W[n_eff['Gemini']]} days in the first half of the window and this one day. "
               f"Claude stood at {n(C8['total'])} percent on 8 November as the mean of the three models (Direct {n(C8['direct'])}); this value is descriptive.")
    mark(f'{pref}: Erweiterung, Ergebnis und Einordnung' if de else f'{pref}: extension, result and assessment', txt)

    # Abschnitt 8: Tabelle 7
    mark(f'{pref}: Tabelle 7]]' if de else f'{pref}: table 7]]', '\n'.join(table7(lang)))

    # Grenzen
    if de:
        txt = (f"Im Wirkungsfenster fehlt Gemini an {len(gem_missing)} von {COV['effect']['anchor_days']} Ankertagen; die Gemini-Differenz beruht auf der ersten Hälfte des Fensters, und eine spät einsetzende Wirkung kann bei Gemini nicht sichtbar werden. Beschränkt auf die Tage mit beiden Anbietern ist der Schätzwert der Kopfzahl negativ (Abschnitt 7). "
               f"Der CUSUM-Alarm der Kopfzahl am {dt(alarm_day, lang)} fällt in die Tage mit nur einem Anbieter und ist von diesem Basiswechsel nicht zu trennen; er ist zudem knapp und hängt an der Streuung der Grundlinie (Abschnitt 7). "
               f"Änderung 4 wurde im laufenden Wirkungsfenster festgelegt; sie wirkt auf Grundlinie und Wirkungsfenster nach derselben Regel, ändert aber eine Gemini-Antwort im Wirkungsfenster, und ohne sie enthält auch das unbereinigte Intervall der Kopfzahl die Null. "
               f"Die Bewertungsregeln vom 2. November sind in der Hauptanalyse zurückgesetzt, der 5. November ist dafür am Volltext nach den vorregistrierten Regeln neu bewertet; in der Sensitivität sind die neuen Regeln in Driftbasis und Grundlinie nur am Auszug von 500 Zeichen angewendet ({SR['nachtrag_eintraege']['baseline_auszug_500_zeichen']} geänderte Antworten, davon {SR['nachtrag_eintraege']['baseline_auszug_aufteilung']['openai_gemini_ankertage_gewertet']} von OpenAI und Gemini auf Ankertagen). "
               f"Den Teil von Eintrag 43 zu echten Angaben über den Autor setzt der Bewerter in der vorregistrierten Fassung enger um als dessen Wortlaut; das betrifft nur beschreibende Claude-Werte (Abschnitte 1 und 6). "
               f"Leere Antworten vor dem 1. November gehen mit null Punkten ein, auf Ankertagen {LA['auf_ankertagen']}, alle bei Gemini; als Lücke gewertet bleibt die Entscheidung gleich, als Fehlmessung gewertet bleibt für Gemini ein einziger Wirkungstag, und die Variante ist wegen der wenigen Gemini-Tage nicht aussagekräftig. "
               f"Der Empfehlungs-Kanal der Entscheidung umfasst zehn Fragen statt der vorregistrierten sechs; beide Fassungen führen zum selben Urteil. "
               f"Die Erweiterung bis zum 8. November ist nicht vorregistriert, nach dem Ende des Wirkungsfensters und nach den Messungen dieses Tages erfasst und fügt für Gemini nur einen Tag hinzu. "
               f"Bei Claude wechselte das Haiku-Modell zwischen Grundlinie und erstem Ankertag, und die Websuche ist nicht erzwungen; vor dem 2. November ist nicht bekannt, bei wie vielen Antworten gesucht wurde.")
    else:
        txt = (f"In the effect window Gemini is missing on {len(gem_missing)} of {COV['effect']['anchor_days']} anchor days; the Gemini difference rests on the first half of the window, and a late-onset effect cannot become visible for Gemini. Restricted to the days with both providers the headline estimate is negative (section 7). "
               f"The CUSUM alarm of the headline on {dt(alarm_day, lang)} falls on the days with a single provider and cannot be separated from this basis change; it is also narrow and depends on the baseline scatter (section 7). "
               f"Amendment 4 was fixed during the effect window; it acts on baseline and effect window under the same rule but changes one Gemini answer in the effect window, and without it the unadjusted headline interval includes zero as well. "
               f"The scoring rules of 2 November are reset in the main analysis, and 5 November has been re-scored on the full text under the pre-registered rules for this purpose; in the sensitivity analysis the new rules were applied in drift base and baseline to the 500-character excerpt only ({SR['nachtrag_eintraege']['baseline_auszug_500_zeichen']} changed answers, {SR['nachtrag_eintraege']['baseline_auszug_aufteilung']['openai_gemini_ankertage_gewertet']} of them from OpenAI and Gemini on anchor days). "
               f"The scorer in its pre-registered version implements the part of entry 43 on genuine statements about the author more narrowly than its wording; this affects only descriptive Claude values (sections 1 and 6). "
               f"Empty answers before 1 November enter with zero points, {LA['auf_ankertagen']} of them on anchor days, all from Gemini; treated as gaps the decision is unchanged, treated as failed measurements Gemini keeps a single effect day, and the variant is not informative because so few Gemini days remain. "
               f"The Recommendation channel of the decision comprises ten questions instead of the six pre-registered ones; both versions lead to the same verdict. "
               f"The extension to 8 November is not pre-registered, was recorded after the end of the effect window and after the measurements of that day, and adds only one day for Gemini. "
               f"For Claude the Haiku model changed between baseline and first anchor day, and web search is not forced; before 2 November it is unknown for how many answers a search took place.")
    assert (tbt['detrended'] < 0) and len(DEF['channels']['discovery']) == 10 and len(DEF['channels']['recommend_gr']) == 6
    mark('[[ERGEBNIS: weitere Grenzen aus dem Wirkungsfenster.]]' if de else '[[RESULT: further limitations from the effect window.]]', txt)

    out = src
    for old, new in R:
        k = out.count(old)
        assert k == 1, (lang, k, old[:90])
        out = out.replace(old, new, 1)
    left = [l for l in out.split('\n') if '[[' in l and not any(m in l for m in ('[[FIG', '[[DOI]]'))]
    assert not left, left
    return out

if __name__ == '__main__':
    for lang in ('de', 'en'):
        txt = build(lang)
        p = os.path.join(ROOT, f'REPORT_{lang.upper()}.md')
        io.open(p, 'w', encoding='utf-8').write(txt)
        print('geschrieben', p, len(txt))
