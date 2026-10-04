#!/usr/bin/env python3
"""Validierungsbericht Q3/2026: Figuren 1–5 (DE + EN, PNG + SVG). Liest NUR data/results.json, data/event_codes.json,
data/wikidata_snapshots.json, data/kg_snapshots.json. Stil wie Bericht 03 (figstyle.py)."""
import json, sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import figstyle as S
import matplotlib.pyplot as plt, matplotlib.dates as mdates, numpy as np
from matplotlib.patches import Rectangle
R = Path(__file__).resolve().parent.parent; D = R/'data'
res = json.load(open(D/'results.json')); s3 = res['stage3']; EV = json.load(open(D/'event_codes.json'))['events']
PROVS = ('OpenAI', 'Gemini', 'Claude-Web')
W0, W1 = (dt.date.fromisoformat(x) for x in res['freeze']['window'])
ANCH = set(res['anchors']); A0 = dt.date(2026, 8, 19)
def d(x): return dt.date.fromisoformat(x)
def num(x, lang, nd=1):
    s = f"{x:.{nd}f}"; return s.replace('.', ',') if lang == 'de' else s
def dlab(x, lang):
    x = d(x) if isinstance(x, str) else x
    return f"{x.day:02d}.{x.month:02d}." if lang == 'de' else x.strftime('%-d %b')
def month_axis(ax, lang):
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=[8, 15, 22]))
    names = {'de': ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt'], 'en': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']}[lang]
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: names[mdates.num2date(v).month - 1]))
SRC = {'de': 'Quelle: eingefrorener Datenstand 01.10.2026 (Fenster 11.05.–30.09.2026) · Auswertung data/results.json',
       'en': 'Source: frozen data state 1 Oct 2026 (window 11 May–30 Sep 2026) · analysis data/results.json'}
PL = {'de': {'OpenAI': 'OpenAI Search', 'Gemini': 'Gemini', 'Claude-Web': 'Claude (claude.ai)'},
      'en': {'OpenAI': 'OpenAI Search', 'Gemini': 'Gemini', 'Claude-Web': 'Claude (claude.ai)'}}
def missing_spans(prov):
    return [(d(e['from']), d(e['to'])) for e in EV if prov in e['providers'] and e['effect'] == 'missing' and e['from'] <= W1.isoformat()]

# ------------------------------------------------------------------ FIG 1: Abdeckungs-Kalender
for lang in ('de', 'en'):
    fig, ax = S.base(11.5, 5.0)
    cb = s3['coverage_balance']; st = s3['day_state']
    rowy = {'OpenAI': 2, 'Gemini': 1, 'Claude-Web': 0}
    for prov in PROVS:
        y = rowy[prov]; col = S.PROV_COLOR[prov]; first = d(cb[prov]['first_day'])
        for a, b in missing_spans(prov):
            ax.add_patch(Rectangle((mdates.date2num(a) - 0.5, y - 0.46), (b - a).days + 1, 0.92, color='#000', alpha=0.05, lw=0, zorder=0))
        x = W0
        while x <= W1:
            k = x.isoformat(); state = st[prov].get(k); scheduled = x >= first and (x < A0 or k in ANCH)
            xn = mdates.date2num(x) - 0.42; h = 0.62 if scheduled else 0.30; yy = y - h / 2
            if state == 'complete': ax.add_patch(Rectangle((xn, yy), 0.84, h, color=col, lw=0, zorder=2, alpha=1 if scheduled else 0.45))
            elif state == 'partial': ax.add_patch(Rectangle((xn, yy), 0.84, h, color=col, lw=0, zorder=2, alpha=0.32 if scheduled else 0.18))
            elif state == 'error_only': ax.add_patch(Rectangle((xn, yy), 0.84, h, facecolor='white', edgecolor='#777', hatch='//////', lw=0.4, zorder=2))
            elif scheduled: ax.add_patch(Rectangle((xn, yy), 0.84, h, facecolor='white', edgecolor='#b5b5b5', lw=0.5, zorder=2))
            x += dt.timedelta(days=1)
        ax.text(mdates.date2num(W0) - 3, y, PL[lang][prov], ha='right', va='center', fontsize=10.5, color=col, fontweight='bold')
        c = cb[prov]
        ax.text(mdates.date2num(W1) + 3, y + 0.12, (f"{c['complete']} von {c['soll_days']} Soll-Tagen vollständig" if lang == 'de' else f"{c['complete']} of {c['soll_days']} scheduled days complete"),
                ha='left', va='center', fontsize=9, color=S.INK)
        ax.text(mdates.date2num(W1) + 3, y - 0.2, (f"{c['partial']} teilweise · {c['error_only']} nur Fehler · {c['none']} ohne Lauf" if lang == 'de' else f"{c['partial']} partial · {c['error_only']} errors only · {c['none']} no run"),
                ha='left', va='center', fontsize=8.2, color=S.MUTE)
    ax.plot([mdates.date2num(A0) - 0.5] * 2, [-0.55, 2.95], color='#666', lw=0.7, ls=(0, (2, 2)), zorder=1)
    ax.text(mdates.date2num(A0) + 0.5, 2.68, 'ab 19.08. jeder dritte Tag' if lang == 'de' else 'from 19 Aug every third day', fontsize=8.5, color='#555', va='bottom')
    # Legende als Direkt-Beschriftung unter der Grafik
    lx = mdates.date2num(W0); ly = -0.95
    items = [('full', 'vollständig' if lang == 'de' else 'complete'), ('part', 'teilweise' if lang == 'de' else 'partial'),
             ('err', 'nur Fehlerzeilen' if lang == 'de' else 'error rows only'), ('none', 'Soll-Tag ohne Lauf' if lang == 'de' else 'scheduled, no run'),
             ('off', 'Messung neben dem Raster' if lang == 'de' else 'off-grid measurement'), ('gap', 'Ausfall laut Register' if lang == 'de' else 'outage in register')]
    x0 = lx - 0.0
    for i, (k, lab) in enumerate(items):
        if i: x0 += 5.5 + len(items[i - 1][1]) * 1.05
        if k == 'full': ax.add_patch(Rectangle((x0, ly - 0.2), 1.6, 0.4, color='#555', lw=0))
        if k == 'part': ax.add_patch(Rectangle((x0, ly - 0.2), 1.6, 0.4, color='#555', alpha=0.32, lw=0))
        if k == 'err': ax.add_patch(Rectangle((x0, ly - 0.2), 1.6, 0.4, facecolor='white', edgecolor='#777', hatch='//////', lw=0.4))
        if k == 'none': ax.add_patch(Rectangle((x0, ly - 0.2), 1.6, 0.4, facecolor='white', edgecolor='#b5b5b5', lw=0.5))
        if k == 'off': ax.add_patch(Rectangle((x0, ly - 0.1), 1.6, 0.2, color='#555', alpha=0.45, lw=0))
        if k == 'gap': ax.add_patch(Rectangle((x0, ly - 0.25), 1.6, 0.5, color='#000', alpha=0.08, lw=0))
        ax.text(x0 + 2.4, ly, lab, va='center', fontsize=8.4, color='#444')
    ax.set_xlim(mdates.date2num(W0) - 1, mdates.date2num(W1) + 1); ax.set_ylim(-1.3, 3.0)
    ax.set_yticks([]); ax.spines['left'].set_visible(False); month_axis(ax, lang)
    t = {'de': ('Abdeckung je Anbieter', 'Ein Kästchen je Tag · Soll: täglich ab dem ersten Messtag bis 18.08., danach jeder dritte Tag · vollständig = alle 16 Fragen je Modellstufe mit Messwert'),
         'en': ('Coverage by provider', 'One cell per day · scheduled: daily from the first measurement day to 18 Aug, then every third day · complete = all 16 questions per model tier with a value')}[lang]
    S.title(fig, *t); S.footer(fig, SRC[lang] + (' · Schattierung: Ausfälle laut Lückenregister' if lang == 'de' else ' · shading: outages per gap register'))
    fig.subplots_adjust(top=0.79, bottom=0.12, left=0.13, right=0.78); S.save(fig, f'fig1_coverage_{lang}', R)

# ------------------------------------------------------------------ FIG 2: Wiederhol-Übereinstimmung je Frage
CATS = [('Direct', ['D1', 'D2', 'D3'], 'Direkt', 'Direct'), ('LongTail', ['L1', 'L2'], 'Saga-Wissen', 'Saga knowledge'), ('Research', ['R1'], 'Forschung', 'Research'),
        ('Genre', ['G1', 'G2'], 'Genre', 'Genre'), ('CompCluster', ['C1', 'C2'], 'Vergleichsautoren', 'Comparable authors'),
        ('GenreRecommend', ['GR1', 'GR2', 'GR3', 'GR4', 'GR5', 'GR6'], 'Genre-Empfehlung', 'Genre recommendation')]
rq = {(x['provider'], x['question_id']): x for x in res['retest_by_question']}
for lang in ('de', 'en'):
    fig, ax = S.base(11, 7.4)
    ys = {}; y = 0; labels = []
    for cat, qs, de, en in CATS:
        for q in qs: ys[q] = y; y -= 1
        labels.append(((ys[qs[0]] + ys[qs[-1]]) / 2, de if lang == 'de' else en)); y -= 0.7
    off = {'OpenAI': 0.18, 'Gemini': 0.0, 'Claude-Web': -0.18}
    zv = {p: set(res['consistency'][p]['zero_variance_items']) for p in PROVS}
    for q, yy in ys.items():
        ax.plot([40, 100], [yy, yy], color=S.RULE, lw=0.4, zorder=0)
        ax.text(38.5, yy, q, ha='right', va='center', fontsize=9.4, color=S.INK)
        allzero = all(q in zv[p] for p in PROVS)
        if allzero: ax.text(101.2, yy, 'ohne Varianz bei allen drei' if lang == 'de' else 'no variance at all three', va='center', fontsize=8.2, color=S.MUTE)
        for p in PROVS:
            x = rq[(p, q)]['share_pct']
            ax.scatter(x, yy + off[p], s=34, color=S.PROV_COLOR[p], zorder=3, edgecolors='white', linewidths=0.6)
    for yy, lab in labels: ax.text(28.5, yy, lab, ha='right', va='center', fontsize=9.6, color='#555', style='italic')
    top = max(ys.values()) + 0.9
    for i, p in enumerate(PROVS):
        ax.scatter(42 + i * 16, top, s=34, color=S.PROV_COLOR[p]); ax.text(43.2 + i * 16, top, PL[lang][p], va='center', fontsize=9.2, color=S.PROV_COLOR[p], fontweight='bold')
    ax.set_xlim(40, 100.5); ax.set_ylim(min(ys.values()) - 0.8, top + 0.6); ax.set_yticks([])
    ax.set_xticks([40, 50, 60, 70, 80, 90, 100]); ax.set_xticklabels([f'{v} %' for v in [40, 50, 60, 70, 80, 90, 100]]); ax.spines['left'].set_visible(False)
    ax.set_xlabel('Anteil identischer Bewertung am nächsten Messtag mit Messwert' if lang == 'de' else 'Share of identical score on the next measurement day with a value')
    rt = res['retest']; rv = s3['summary']['retest_varying_questions']
    sub = {'de': f"Gesamt: OpenAI {num(rt['OpenAI']['share_pct'], 'de')} %, Gemini {num(rt['Gemini']['share_pct'], 'de')} %, Claude {num(rt['Claude-Web']['share_pct'], 'de')} % · nur Fragen mit Varianz: {num(rv['OpenAI']['share_pct'], 'de')} / {num(rv['Gemini']['share_pct'], 'de')} / {num(rv['Claude-Web']['share_pct'], 'de')} %",
           'en': f"Overall: OpenAI {rt['OpenAI']['share_pct']} %, Gemini {rt['Gemini']['share_pct']} %, Claude {rt['Claude-Web']['share_pct']} % · questions with variance only: {rv['OpenAI']['share_pct']} / {rv['Gemini']['share_pct']} / {rv['Claude-Web']['share_pct']} %"}[lang]
    S.title(fig, 'Wiederhol-Übereinstimmung je Frage' if lang == 'de' else 'Test-retest agreement by question', sub)
    S.footer(fig, SRC[lang] + (' · Paare je Frage und Modellstufe, aufeinanderfolgende Messtage' if lang == 'de' else ' · pairs per question and model tier, consecutive measurement days'))
    fig.subplots_adjust(top=0.84, bottom=0.11, left=0.2, right=0.8); S.save(fig, f'fig2_retest_{lang}', R)

# ------------------------------------------------------------------ FIG 3: Tageswert + CUSUM-Alarme + Ereignisse
lvl = res['level_by_day']; reb = res['cusum_rebase']; chk = {(a['provider'], a['alarm_day']): a for a in s3['alarm_check_rebase_down']}
for lang in ('de', 'en'):
    fig, axes = S.base(11.5, 9.0, rows=3, cols=1, sharex=True)
    for ax, prov in zip(axes, PROVS):
        col = S.PROV_COLOR[prov]; xs = [mdates.date2num(d(k)) for k in lvl[prov]]; ys = list(lvl[prov].values())
        for a, b in missing_spans(prov):
            ax.axvspan(mdates.date2num(a) - 0.5, mdates.date2num(b) + 0.5, color='#000', alpha=0.05, lw=0, zorder=0)
        ax.plot(xs, ys, color=col, lw=0.8, alpha=0.55, zorder=2); ax.scatter(xs, ys, s=9, color=col, zorder=3, linewidths=0)
        segs = reb[prov]
        for i, sg in enumerate(segs):
            if not sg: continue
            a0, a1 = d(sg['baseline_days'][0]), d(sg['baseline_days'][1])
            end = d(sg['first_alarm']['d']) if 'first_alarm' in sg else W1
            ax.plot([mdates.date2num(a0), mdates.date2num(a1)], [sg['mu']] * 2, color=S.INK, lw=1.8, zorder=4, solid_capstyle='butt')
            ax.plot([mdates.date2num(a1), mdates.date2num(end)], [sg['mu']] * 2, color=S.INK, lw=0.7, ls=(0, (2, 2)), zorder=4)
            if 'first_alarm' in sg:
                fa = sg['first_alarm']; xa = mdates.date2num(d(fa['d']))
                if fa['direction'] == 'down':
                    ax.scatter(xa, fa['x'] - 3.2, marker='v', s=70, color=S.WAX, zorder=6)
                    ax.text(xa, fa['x'] - 7.8, dlab(fa['d'], lang), ha='center', va='top', fontsize=8.6, color=S.WAX, fontweight='bold')
                else:
                    ax.scatter(xa, fa['x'] + 3.2, marker='^', s=46, color='#888', zorder=6)
        # Ereignisse mit moeglicher Pegelwirkung
        marks = [(e['from'], f"E{e['id']}") for e in EV if prov in e['providers'] and e['effect'] == 'level'] + \
                [(k[-10:], 'M') for k in s3['model_change_detected'] if k.startswith('M-' + prov + '-')]
        for day_, lab in marks:
            xe = mdates.date2num(d(day_)); ax.axvline(xe, color='#555', lw=0.7, ls=':', zorder=1)
            ax.text(xe + 0.6, 37.5, lab, fontsize=8.2, color='#444', va='top')
        ax.axvline(mdates.date2num(A0) - 0.5, color='#999', lw=0.6, ls=(0, (4, 3)), zorder=1)
        ax.set_ylim(-22, 40); ax.set_yticks([-20, 0, 20, 40]); ax.set_yticklabels([f'{v} %' for v in [-20, 0, 20, 40]])
        ax.grid(axis='y', color=S.RULE, lw=0.4); ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
        ax.text(0.0, 1.02, PL[lang][prov], transform=ax.transAxes, fontsize=11, color=col, fontweight='bold', va='bottom')
        nd = sum(1 for a in s3['alarm_check_rebase_down'] if a['provider'] == prov)
        ax.text(1.0, 1.02, (f"{nd} Abwärts-Alarm" + ("e" if nd != 1 else "") + " · keiner durch das Register erklärt") if lang == 'de' else f"{nd} downward alarm{'s' if nd != 1 else ''} · none explained by the register",
                transform=ax.transAxes, fontsize=8.6, color=S.MUTE, ha='right', va='bottom')
    month_axis(axes[-1], lang); axes[-1].set_xlim(mdates.date2num(W0), mdates.date2num(W1) + 2)
    t = {'de': ('Tageswert je Anbieter mit CUSUM-Alarmen', 'Punkte = Tageswert (Punktsumme ÷ Maximum, 16 Fragen) · schwarze Linie = Referenzmittel aus 10 Messtagen, gestrichelt bis zum Alarm · rotes Dreieck = Abwärts-, graues = Aufwärts-Alarm (k = 0,5, h = 5 SD)\nE5 Eintrag in Fremdliste · E8 Konnektor abgeschaltet · E18 Erscheinungstermin verschoben · M Modell-Etikett gewechselt · gestrichelt grau: Kadenzwechsel 19.08.'),
         'en': ('Daily value by provider with CUSUM alarms', 'Dots = daily value (score sum ÷ maximum, 16 questions) · black line = reference mean of 10 measurement days, dashed until the alarm · red triangle = downward, grey = upward alarm (k = 0.5, h = 5 SD)\nE5 third-party list entry · E8 connector disabled · E18 release date moved · M model label changed · dashed grey: cadence change 19 Aug')}[lang]
    S.title(fig, t[0], t[1], y=0.975); S.footer(fig, SRC[lang] + (' · Schattierung: Ausfälle laut Lückenregister' if lang == 'de' else ' · shading: outages per gap register'), y=0.01)
    fig.subplots_adjust(top=0.84, bottom=0.06, left=0.07, right=0.97, hspace=0.32); S.save(fig, f'fig3_cusum_{lang}', R)

# ------------------------------------------------------------------ FIG 4: Cronbachs alpha
for lang in ('de', 'en'):
    fig, ax = S.base(11, 4.6)
    ax.axvspan(0.5, 0.7, color=S.SAND, alpha=0.16, lw=0, zorder=0)
    ax.axvline(0.7, color=S.INK, lw=0.8, ls=(0, (3, 2)))
    ax.text(0.6, 3.05, 'vorregistriertes Band\nKI-Flächen 0,5–0,7' if lang == 'de' else 'pre-registered band\nAI surfaces 0.5–0.7', ha='center', va='bottom', fontsize=8.6, color='#7a5a1e')
    ax.text(0.705, 3.05, 'Schwelle API-Flächen 0,7' if lang == 'de' else 'threshold API surfaces 0.7', ha='left', va='bottom', fontsize=8.6, color=S.INK)
    for i, p in enumerate(PROVS):
        y = 2 - i; c = res['consistency'][p]; col = S.PROV_COLOR[p]
        ax.plot(c['ci95'], [y, y], color=col, lw=2.2, solid_capstyle='butt'); ax.scatter(c['alpha'], y, s=70, color=col, zorder=3, edgecolors='white', linewidths=1)
        ax.text(c['alpha'], y + 0.2, num(c['alpha'], lang, 2), ha='center', va='bottom', fontsize=10, color=col, fontweight='bold')
        ax.text(0.198, y, PL[lang][p], ha='right', va='center', fontsize=10.5, color=col, fontweight='bold')
        zv = len(c['zero_variance_items'])
        ax.text(0.93, y + 0.08, (f"{zv} von 16 Fragen ohne Varianz" if lang == 'de' else f"{zv} of 16 questions without variance"), va='center', fontsize=9.2, color=S.INK)
        ax.text(0.93, y - 0.2, (f"{c['cases']} Fälle (Messtag × Modellstufe)" if lang == 'de' else f"{c['cases']} cases (day × model tier)"), va='center', fontsize=8.2, color=S.MUTE)
    ax.set_xlim(0.2, 1.12); ax.set_ylim(-0.6, 3.6); ax.set_yticks([])
    ax.set_xticks([0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]); ax.set_xticklabels([num(v, lang, 1) for v in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]])
    ax.spines['left'].set_visible(False); ax.set_xlabel('Cronbachs α über 16 Fragen, Bootstrap-95-%-Intervall' if lang == 'de' else "Cronbach's α across 16 questions, bootstrap 95 % interval")
    S.title(fig, 'Interne Konsistenz des Fragensets' if lang == 'de' else 'Internal consistency of the question set',
            'Fragen ohne Varianz tragen zur Skala nichts bei · Schwellen laut Vorregistrierung Q0-INST (H-Q0-INST-04)' if lang == 'de' else 'Questions without variance add nothing to the scale · thresholds per pre-registration Q0-INST (H-Q0-INST-04)')
    S.footer(fig, SRC[lang] + (' · 2.000 Bootstrap-Ziehungen über Fälle' if lang == 'de' else ' · 2,000 bootstrap draws over cases'))
    fig.subplots_adjust(top=0.74, bottom=0.17, left=0.17, right=0.98); S.save(fig, f'fig4_alpha_{lang}', R)

# ------------------------------------------------------------------ FIG 5: Anker-Messflächen Wikidata und Knowledge Graph
wd = json.load(open(D/'wikidata_snapshots.json')); kg = json.load(open(D/'kg_snapshots.json')); an = s3['anchor_surfaces']
KGQ = {'Marin T. Kael': 'author', 'Das vierte Feld Marin Kael': 'book', 'Prägungen des Reiches Marin Kael': 'series'}
kgd = {}
for r in sorted(kg, key=lambda r: r['snapshot_at']): kgd.setdefault((r['d'], KGQ[r['query']]), int(r['response_count'] > 0))
for lang in ('de', 'en'):
    fig, ax = S.base(11.5, 5.4)
    rows = [('reg_a', 'Wikidata Q139720807 · Autor (registrierter Anker)' if lang == 'de' else 'Wikidata Q139720807 · author (registered anchor)'),
            ('reg_b', 'Wikidata Q139720798 · Buch (registrierter Anker)' if lang == 'de' else 'Wikidata Q139720798 · book (registered anchor)'),
            ('suc_a', 'Wikidata Q140004504 · Autor (Nachfolge)' if lang == 'de' else 'Wikidata Q140004504 · author (successor)'),
            ('suc_b', 'Wikidata Q140004740 · Buch (Nachfolge)' if lang == 'de' else 'Wikidata Q140004740 · book (successor)'),
            ('kg_a', 'Knowledge Graph · Autorname' if lang == 'de' else 'Knowledge Graph · author name'),
            ('kg_b', 'Knowledge Graph · Buchtitel + Autor' if lang == 'de' else 'Knowledge Graph · book title + author'),
            ('kg_s', 'Knowledge Graph · Reihentitel + Autor' if lang == 'de' else 'Knowledge Graph · series title + author')]
    Y = {k: len(rows) - 1 - i for i, (k, _) in enumerate(rows)}
    for k, lab in rows: ax.text(mdates.date2num(W0) - 2, Y[k], lab, ha='right', va='center', fontsize=9.2, color=S.INK)
    for qid, k in (('Q139720807', 'reg_a'), ('Q139720798', 'reg_b')):
        dl = an['wikidata_registered_anchor'][qid]['deleted_detected']; xd = mdates.date2num(d(dl))
        ax.plot([mdates.date2num(W0), xd], [Y[k]] * 2, color='#bbb', lw=0.8, ls=(0, (1, 2)))
        ax.scatter(xd, Y[k], marker='x', s=46, color=S.WAX, zorder=3, linewidths=1.6)
        ax.text(xd + 2, Y[k], ('Löschung festgestellt ' if lang == 'de' else 'deletion detected ') + dlab(dl, lang), va='center', fontsize=8.6, color=S.WAX)
    for qid, k in (('Q140004504', 'suc_a'), ('Q140004740', 'suc_b')):
        for r in wd:
            if r['qid'] == qid and not r['deleted']:
                ax.add_patch(Rectangle((mdates.date2num(d(r['d'])) - 0.42, Y[k] - 0.28), 0.84, 0.56, color=S.BLUE, lw=0))
        sc = an['wikidata_successor'][qid]
        ax.text(mdates.date2num(W1) + 3, Y[k], (f"Abdeckung {num(sc['coverage_mean'], lang, 2)} · {sc['claim_count_min']}–{sc['claim_count_max']} Aussagen" if lang == 'de' else f"coverage {sc['coverage_mean']:.2f} · {sc['claim_count_min']}–{sc['claim_count_max']} statements"), va='center', fontsize=8.4, color=S.INK)
    for kk, k in (('author', 'kg_a'), ('book', 'kg_b'), ('series', 'kg_s')):
        for (dd_, q), h in kgd.items():
            if q != kk: continue
            x = mdates.date2num(d(dd_))
            if h: ax.add_patch(Rectangle((x - 0.42, Y[k] - 0.28), 0.84, 0.56, color=S.WAX, lw=0))
            else: ax.add_patch(Rectangle((x - 0.42, Y[k] - 0.28), 0.84, 0.56, facecolor='white', edgecolor='#c4c4c4', lw=0.4))
        g = an['kg'][kk]
        ax.text(mdates.date2num(W1) + 3, Y[k], (f"Treffer an {g['hit_days']} von {g['days']} Tagen" if lang == 'de' else f"hit on {g['hit_days']} of {g['days']} days"), va='center', fontsize=8.4, color=S.INK)
    ax.set_xlim(mdates.date2num(W0) - 1, mdates.date2num(W1) + 1); ax.set_ylim(-0.8, len(rows) - 0.2); ax.set_yticks([]); ax.spines['left'].set_visible(False); month_axis(ax, lang)
    kp = an['kappa_wd_kg']
    sub = {'de': f"Blau: Item vorhanden · Rot: Knowledge Graph liefert einen Treffer · Cohens κ Wikidata – Knowledge Graph = {num(kp['kappa'], 'de', 2)} ({kp['pairs']} Tagespaare Autor + Buch)",
           'en': f"Blue: item present · red: Knowledge Graph returns a hit · Cohen's κ Wikidata – Knowledge Graph = {kp['kappa']:.2f} ({kp['pairs']} day pairs author + book)"}[lang]
    S.title(fig, 'Anker-Messflächen: Wikidata und Knowledge Graph' if lang == 'de' else 'Anchor surfaces: Wikidata and Knowledge Graph', sub)
    S.footer(fig, SRC[lang] + (' · Wikidata-Schnappschüsse der registrierten Items erst ab der Löschungsfeststellung' if lang == 'de' else ' · Wikidata snapshots of the registered items only from the detection of deletion'))
    fig.subplots_adjust(top=0.8, bottom=0.12, left=0.33, right=0.82); S.save(fig, f'fig5_anchors_{lang}', R)
