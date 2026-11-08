#!/usr/bin/env python3
"""Bericht 04: Abbildungen 1–5 (DE + EN, PNG + SVG). Liest NUR data/results.json. Stil wie Q3 / Bericht 03 (figstyle.py).
Abb. 1 Kopfzahl OpenAI + Gemini je Ankertag mit Grundlinie, Drift und Ereignismarken; Marken nach Basis (gefüllt beide,
       ○ nur Gemini, □ nur OpenAI, Legende aus anchor_table); Ankertag 08.11. aus der nicht vorregistrierten Erweiterung
       (results.json → extension_0811) als eigene Raute, ohne die Linien der Hauptanalyse zu verändern
Abb. 2 Drei Kanäle je Ankertag
Abb. 3 Vorher-Nachher-Differenzen mit 95-%-Intervallen je Kanal; unten abgesetzt die Kopfzahl der Erweiterung bis 08.11.
Abb. 4 Claude (je neuestes Opus, Sonnet, Haiku auf claude.ai; Mittel = Anbieter), beschreibend
Abb. 5 Trefferquote je Kanal (Robustheit, Änderung 2 vom 07.10.2026)
Fehlende Werte bleiben leer (Lücke ist kein Nullwert); vor dem Wirkungsfenster zeigen die Abbildungen nur die Grundlinie.
Die Datenelemente tragen SVG-ids (gid, Präfix f1_ bis f5_), damit sich ihre Werte aus den SVG-Koordinaten gegen results.json prüfen lassen.
Nachtrag 08.11.2026: Marken nach Basis, Versatz ±0,3 Tage, Einheit je Sprache, Erweiterung gekennzeichnet."""
import json, sys, datetime as dt
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); import figstyle as S
import matplotlib.pyplot as plt, matplotlib.dates as mdates, numpy as np
from matplotlib.lines import Line2D

R = Path(__file__).resolve().parent.parent; D = R / 'data'
res = json.load(open(D / 'results.json', encoding='utf-8'))
WIN = res['preregistration']['windows']; AT = res['anchor_table']
EVENT = dt.date(2026, 10, 8); PRE = dt.date(2026, 9, 30)
X0, X1 = dt.date(2026, 8, 16), dt.date(2026, 11, 9)
PC = {'OpenAI': S.WAX, 'Gemini': '#b0763a'}
UNTIL = dt.date.fromisoformat(res['freeze']['data_until_utc'][:10])
EXT = res.get('extension_0811') or {}          # nicht vorregistrierte Erweiterung bis Ankertag 08.11. (Eintrag 83)
EXC = '#7a5a1e'                                 # Farbe der Erweiterung (dunkles Ocker, wie die Beschriftung des Wirkungsfensters)


def d(x): return dt.date.fromisoformat(x)
def xn(x): return mdates.date2num(d(x) if isinstance(x, str) else x)
def num(x, lang, nd=1):
    from decimal import Decimal, ROUND_HALF_UP   # 22,45 -> 22,5 wie im Text (float-Format rundet 22.45 auf 22.4)
    s = str(Decimal(str(x)).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP)); return s.replace('.', ',').replace('-', '−') if lang == 'de' else s.replace('-', '−')
def pp(lang): return 'Pp.' if lang == 'de' else 'pp'   # Einheit Prozentpunkte je Sprache
def dlab(x, lang):
    x = d(x) if isinstance(x, str) else x
    return f"{x.day}.{x.month}." if lang == 'de' else x.strftime('%-d %b')
def drange(a, b, lang):
    """Datumsspanne kompakt: 18.–27.9. / 24.10.–5.11. bzw. 18–27 Sep / 24 Oct – 5 Nov."""
    a, b = (d(x) if isinstance(x, str) else x for x in (a, b))
    if a == b: return dlab(a, lang)
    if lang == 'de': return f"{a.day}.–{b.day}.{b.month}." if a.month == b.month else f"{a.day}.{a.month}.–{b.day}.{b.month}."
    return f"{a.day}–{b.day} {b.strftime('%b')}" if a.month == b.month else f"{a.day} {a.strftime('%b')} – {b.day} {b.strftime('%b')}"
def utc_hm(ts, lang):
    t = dt.datetime.fromisoformat(ts.replace('Z', '+00:00'))
    return f"{t.day}.{t.month}.{t.year} {t:%H:%M} UTC" if lang == 'de' else f"{t.day} {t:%b} {t.year} {t:%H:%M} UTC"


SRC = {'de': f"Quelle: Messdatenbank, Grundlinie eingefroren zum 07.10.2026 23:59 UTC · Daten bis {dlab(UNTIL, 'de')}{UNTIL.year} · Auswertung data/results.json",
       'en': f"Source: measurement database, baseline frozen at 7 Oct 2026 23:59 UTC · data until {dlab(UNTIL, 'en')} {UNTIL.year} · analysis data/results.json"}
CHN = {'de': {'total': 'Kopfzahl (16 Fragen)', 'direct': 'Direkt (D1–D3)', 'longtail': 'Saga-Wissen (L1, L2)', 'discovery': 'Empfehlung (G, C, GR; 10 Fragen)', 'recommend_gr': 'davon GR1–GR6'},
       'en': {'total': 'Headline (16 questions)', 'direct': 'Direct (D1–D3)', 'longtail': 'Saga knowledge (L1, L2)', 'discovery': 'Recommendation (G, C, GR; 10 questions)', 'recommend_gr': 'of which GR1–GR6'}}


def time_axis(ax, lang):
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_minor_locator(mdates.DayLocator(bymonthday=[8, 15, 22]))
    names = {'de': ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'],
             'en': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']}[lang]
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: names[mdates.num2date(v).month - 1]))
    ax.set_xlim(xn(X0), xn(X1))


def windows(ax, lang, top, labels=True):
    ax.axvspan(xn(WIN['baseline'][0]) - 0.5, xn(WIN['baseline'][1]) + 0.5, color='#000', alpha=0.035, lw=0, zorder=0)
    ax.axvspan(xn(WIN['effect'][0]) - 0.5, xn(WIN['effect'][1]) + 0.5, color=S.SAND, alpha=0.13, lw=0, zorder=0)
    ax.axvline(xn(PRE), color='#666', lw=0.7, ls=':', zorder=1)
    ax.axvline(xn(EVENT) - 0.5, color=S.WAX, lw=1.0, zorder=1)
    if labels:
        T = ax.get_xaxis_transform()
        ax.text(xn(WIN['baseline'][0]) + 0.6, 0.98, 'Grundlinie' if lang == 'de' else 'Baseline', fontsize=8.4, color='#555', va='top', transform=T)
        ax.text(xn(WIN['effect'][0]) + 0.6, 0.91, 'Wirkungsfenster' if lang == 'de' else 'Effect window', fontsize=8.4, color='#7a5a1e', va='top', transform=T)
        ax.text(xn(PRE) - 0.6, 0.98, 'vorab bestellbar 30.9.' if lang == 'de' else 'orderable 30 Sep', fontsize=8.0, color='#555', va='top', ha='right', transform=T)
        ax.text(xn(EVENT) + 0.6, 0.98, 'Erscheinen 8.10.' if lang == 'de' else 'Release 8 Oct', fontsize=8.4, color=S.WAX, va='top', fontweight='bold', transform=T)


def drift_avg(m, w='baseline'):
    """Mittel der beiden Anbieter-Driftgeraden (Niveau am 08.10. und Steigung)."""
    pr = res['baseline'][w][m]['providers']; f = [pr[p]['drift_used'] for p in ('OpenAI', 'Gemini') if pr[p]['drift_used']]
    if len(f) < 2: return None
    return float(np.mean([x['level_at_event_pp'] for x in f])), float(np.mean([x['slope_pp_per_day'] for x in f]))


def draw_drift(ax, m, gid=None):
    da = drift_avg(m)
    if not da: return
    lv, sl = da
    def y(t): return lv + sl * (t - EVENT).days
    a, b, c = d('2026-08-19'), d(WIN['baseline'][1]), d(WIN['effect'][1])
    ax.plot([xn(a), xn(b)], [y(a), y(b)], color=S.BLUE, lw=1.2, zorder=2, gid=f'{gid}_drift_fit' if gid else None)
    ax.plot([xn(b), xn(c)], [y(b), y(c)], color=S.BLUE, lw=1.2, ls=(0, (4, 3)), zorder=2, gid=f'{gid}_drift_ext' if gid else None)


def headline_pts(m):
    both = [(r['d'], r['headline'][m]) for r in AT if r['basis'] == 'beide' and r['headline'][m] is not None]
    single = [(r['d'], r['single_provider_value'][m], r['basis']) for r in AT if r['basis'] and r['basis'] != 'beide' and r['single_provider_value'][m] is not None]
    return both, single


def pending_note(ax, lang, y):
    if UNTIL < EVENT or not any(r['basis'] for r in AT if r['window'] == 'effect'):
        ax.text(xn(WIN['effect'][0]) + 15, y, 'Messung ab 9.10.\nalle drei Tage' if lang == 'de' else 'measured from 9 Oct\nevery third day',
                fontsize=8.6, color='#7a5a1e', ha='center', va='center', style='italic')


# ------------------------------------------------------------------ Abb. 1: Kopfzahl
# Einzelwerte nach Basis getrennt: ○ nur Gemini, □ nur OpenAI; Legende mit Daten aus anchor_table.
BASIS = {'nur_gemini': ('o', 'Gemini', 'OpenAI'), 'nur_openai': ('s', 'OpenAI', 'Gemini')}   # Marke, gemessen, ausgefallen
def basis_runs(basis, m='total'):
    """Zusammenhängende Ankertage gleicher Basis in der Reihenfolge von anchor_table."""
    out, cur = [], []
    for r in AT:
        if r['basis'] == basis and r['single_provider_value'][m] is not None: cur.append(r['d'])
        elif cur: out.append(cur); cur = []
    if cur: out.append(cur)
    return out
def ext_anchor(m='total'):
    """Ankertag 08.11. aus der Erweiterung (results.json → extension_0811.anchor_0811): (Datum, Wert, Basis) oder None."""
    a = EXT.get('anchor_0811') or {}
    if not a.get('basis'): return None
    v = a['headline'][m] if a['basis'] == 'beide' else a['single_provider_value'][m]
    return (a['d'], v, a['basis']) if v is not None else None

for lang in ('de', 'en'):
    fig, ax = S.base(11.5, 5.6)
    both, single = headline_pts('total')
    windows(ax, lang, 49)
    draw_drift(ax, 'total', gid='f1')
    # 07.10.2026, Entscheidung des Autors: Beschriftung = vorregistrierter Grundlinienwert (Anbieter erst einzeln gemittelt, dann ausgeglichen)
    blt = res['baseline']['baseline']['total']
    blm = blt.get('provider_balanced_mean')
    if blm is not None:
        npv = {p: v.get('n_anchor_days') for p, v in (blt.get('providers') or {}).items()}
        ns = ' · '.join(f"{p} {n} Tage" if lang == 'de' else f"{p} {n} days" for p, n in npv.items() if n)
        ax.plot([xn(WIN['baseline'][0]), xn(WIN['baseline'][1])], [blm] * 2, color=S.INK, lw=0.9, zorder=2, gid='f1_baseline')
        ax.annotate('', xy=(xn(WIN['baseline'][0]) + 2, blm), xytext=(xn(WIN['baseline'][0]) + 2, blm + 9.3),
                    arrowprops=dict(arrowstyle='-', color=S.INK, lw=0.5))
        ax.text(xn(WIN['baseline'][0]) + 0.6, blm + 9.6, (f"Grundlinie {num(blm, lang)} % ({ns})" if lang == 'de' else f"baseline {num(blm, lang)} % ({ns})"),
                fontsize=8.4, color=S.INK, va='bottom')
    H = []
    if both:
        ax.plot([xn(x) for x, _ in both], [v for _, v in both], color='#999', lw=0.6, zorder=2, gid='f1_both_line')
        ax.scatter([xn(x) for x, _ in both], [v for _, v in both], s=34, color=S.INK, zorder=4, edgecolors='white', linewidths=0.8, gid='f1_both')
        H.append(Line2D([], [], ls='none', marker='o', ms=6.2, mfc=S.INK, mec='white', mew=0.8,
                        label='beide gemessen: Kopfzahl' if lang == 'de' else 'both measured: headline'))
    for b, (mk, has, miss) in BASIS.items():
        pts = [(x, v) for x, v, bb in single if bb == b]
        if not pts: continue
        ax.scatter([xn(x) for x, _ in pts], [v for _, v in pts], s=34 if mk == 'o' else 30, marker=mk, facecolors='white', edgecolors=S.INK, linewidths=1.0, zorder=4, gid=f'f1_{b}')
        rn = basis_runs(b); n = sum(len(x) for x in rn); spans = ', '.join(drange(x[0], x[-1], lang) for x in rn)
        H.append(Line2D([], [], ls='none', marker=mk, ms=6.2 if mk == 'o' else 5.8, mfc='white', mec=S.INK, mew=1.0,
                        label=(f"nur {has}: {spans} ({n} Ankertage, {miss} ausgefallen)" if lang == 'de' else f"{has} only: {spans} ({n} anchor days, {miss} failed)")))
    ea = ext_anchor()
    if ea:   # eigene Marke; nicht mit der Linie der Hauptanalyse verbunden, Drift und Grundlinie unverändert
        ax.scatter([xn(ea[0])], [ea[1]], s=40, marker='D', facecolors=S.SAND, edgecolors=S.INK, linewidths=0.9, zorder=5, gid='f1_ext0811')
        ax.annotate(('8.11.: Erweiterung,\nnicht vorregistriert' if lang == 'de' else '8 Nov: extension,\nnot pre-registered'),
                    xy=(xn(ea[0]) - 0.4, ea[1] + 0.6), xytext=(xn(ea[0]) - 2.2, ea[1] + 6.5), fontsize=8.0, color=EXC, ha='right', va='center',
                    arrowprops=dict(arrowstyle='-', color=EXC, lw=0.5, shrinkA=1, shrinkB=1))
        bt = {'beide': ('beide gemessen', 'both measured')}.get(ea[2], (ea[2], ea[2]))
        H.append(Line2D([], [], ls='none', marker='D', ms=5.6, mfc=S.SAND, mec=S.INK, mew=0.9,
                        label=(f"{dlab(ea[0], 'de')}: Erweiterung, nicht vorregistriert ({bt[0]})" if lang == 'de' else f"{dlab(ea[0], 'en')}: extension, not pre-registered ({bt[1]})")))
    if H: ax.legend(handles=H, frameon=False, fontsize=8.4, loc='lower left', bbox_to_anchor=(0.0, 1.015), ncol=2, borderaxespad=0,
                    handletextpad=0.3, columnspacing=2.4, labelspacing=0.45)
    pending_note(ax, lang, 30)
    ax.set_ylim(0, 50); ax.set_yticks([0, 10, 20, 30, 40, 50]); ax.set_yticklabels([f'{v} %' for v in [0, 10, 20, 30, 40, 50]])
    ax.grid(axis='y', color=S.RULE, lw=0.4); ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
    time_axis(ax, lang)
    t = {'de': ('Kopfzahl OpenAI und Gemini je Ankertag',
                'Punktsumme ÷ Höchstwert über 16 Fragen · gefüllt: Mittel beider Anbieter · hohl: Einzelwerte, keine Kopfzahl, nicht gegen die gemittelte Driftlinie zu lesen\nblaue Linie: lineare Drift aus den Ankertagen ab 19.8., gestrichelt fortgeschrieben · schwarze Linie: Grundlinie (Anbieter einzeln gemittelt, dann ausgeglichen, wie vorregistriert)'),
         'en': ('Headline of OpenAI and Gemini by anchor day',
                'Score sum ÷ maximum over 16 questions · filled: mean of both providers · hollow: single values, not the headline, not to be read against the averaged drift line\nblue line: linear drift from the anchor days since 19 Aug, dashed where extrapolated · black line: baseline (providers averaged separately, then balanced, as pre-registered)')}[lang]
    ft = SRC[lang]
    if ea and (EXT.get('abzug') or {}).get('frozen_at_utc'):
        ft += (f" · Raute {dlab(ea[0], 'de')}: Erweiterung, Eintrag {EXT.get('register_entry')}, Abzug {utc_hm(EXT['abzug']['frozen_at_utc'], 'de')}" if lang == 'de'
               else f" · diamond {dlab(ea[0], 'en')}: extension, entry {EXT.get('register_entry')}, snapshot {utc_hm(EXT['abzug']['frozen_at_utc'], 'en')}")
    S.title(fig, *t); S.footer(fig, ft)
    fig.subplots_adjust(top=0.70, bottom=0.1, left=0.07, right=0.97); S.save(fig, f'fig1_headline_{lang}', R)

# ------------------------------------------------------------------ Abb. 2: drei Kanäle
for lang in ('de', 'en'):
    fig, axes = S.base(11.5, 8.6, rows=3, cols=1, sharex=True)
    for ax, m, top in zip(axes, ('direct', 'longtail', 'discovery'), (105, 105, 26)):
        windows(ax, lang, top * 0.97, labels=(m == 'direct'))
        draw_drift(ax, m, gid=f'f2_{m}')
        for p in ('OpenAI', 'Gemini'):
            pts = [(r['d'], r[p][m]) for r in AT if r[p]['state'] == 'vollstaendig' and r[p][m] is not None]
            ax.scatter([xn(x) for x, _ in pts], [v for _, v in pts], s=16, color=PC[p], alpha=0.75, zorder=3, lw=0, gid=f'f2_{m}_{p}')
        both, _ = headline_pts(m)
        if both:
            ax.plot([xn(x) for x, _ in both], [v for _, v in both], color=S.INK, lw=1.0, zorder=4, gid=f'f2_{m}_mean')
        ax.set_ylim(-5 if m != 'discovery' else -2, top)
        ax.grid(axis='y', color=S.RULE, lw=0.4); ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{int(v)} %'))
        bl = res['baseline']['baseline'][m]
        lab = CHN[lang][m]
        ax.text(0.0, 1.03, lab, transform=ax.transAxes, fontsize=11, color=S.INK, fontweight='bold', va='bottom')
        ax.text(1.0, 1.03, (f"Grundlinie OpenAI {num(bl['providers']['OpenAI']['mean'], lang)} % (n = {bl['providers']['OpenAI']['n_anchor_days']}) · Gemini {num(bl['providers']['Gemini']['mean'], lang)} % (n = {bl['providers']['Gemini']['n_anchor_days']})" if lang == 'de'
                            else f"Baseline OpenAI {num(bl['providers']['OpenAI']['mean'], lang)} % (n = {bl['providers']['OpenAI']['n_anchor_days']}) · Gemini {num(bl['providers']['Gemini']['mean'], lang)} % (n = {bl['providers']['Gemini']['n_anchor_days']})"),
                transform=ax.transAxes, fontsize=8.6, color=S.MUTE, ha='right', va='bottom')
        if m == 'direct': pending_note(ax, lang, 50)
    time_axis(axes[-1], lang)
    t = {'de': ('Drei Kanäle je Ankertag',
                'Punkte: OpenAI (rot) und Gemini (ocker) · schwarze Linie: Mittel beider Anbieter an Tagen mit beiden Messungen · blau: Drift, gestrichelt fortgeschrieben\nKanäle wie im Messdienst: Direkt = Frage nennt Autor oder Werk · Saga-Wissen = Begriffe aus dem Werk · Empfehlung = Frage nennt weder Autor noch Werk'),
         'en': ('Three channels by anchor day',
                'Dots: OpenAI (red) and Gemini (ochre) · black line: mean of both providers on days with both measurements · blue: drift, dashed where extrapolated\nChannels as in the measurement service: Direct = question names author or work · Saga knowledge = terms from the work · Recommendation = question names neither')}[lang]
    S.title(fig, *t, y=0.975); S.footer(fig, SRC[lang], y=0.01)
    fig.subplots_adjust(top=0.83, bottom=0.06, left=0.07, right=0.97, hspace=0.38); S.save(fig, f'fig2_channels_{lang}', R)

# ------------------------------------------------------------------ Abb. 3: Vorher-Nachher-Differenzen
ROWS = ['total', 'direct', 'longtail', 'discovery', 'recommend_gr']
EXT_ROW = (EXT.get('effects_primary') or {}).get('total')   # Erweiterung bis 08.11.: nur die Kopfzahl, abgesetzt unter den Kanälen
if EXT_ROW and EXT_ROW.get('detrended') is None: EXT_ROW = None
def effect_row(ax, e, y, col, lang, lim, gid, s=None, bold=False):
    if e['ci95_detrended']: ax.plot(e['ci95_detrended'], [y + 0.1] * 2, color=col, lw=2.2, solid_capstyle='butt', zorder=2, gid=f'{gid}_ci')
    ax.scatter(e['detrended'], y + 0.1, s=60, color=col, zorder=3, edgecolors='white', linewidths=1, gid=f'{gid}_det')
    ax.scatter(e['raw'], y + 0.1, s=36, facecolors='white', edgecolors=col, linewidths=1.0, zorder=3, gid=f'{gid}_raw')
    if s is not None and s['detrended'] is not None:
        if s['ci95_detrended']: ax.plot(s['ci95_detrended'], [y - 0.18] * 2, color=S.COOL, lw=1.4, solid_capstyle='butt', zorder=2, gid=f'{gid}_sens_ci')
        ax.scatter(s['detrended'], y - 0.18, s=30, color=S.COOL, zorder=3, gid=f'{gid}_sens')
    ax.text(lim * 1.04, y, f"{num(e['detrended'], lang)} {pp(lang)}" + (f"  [{num(e['ci95_detrended'][0], lang)}; {num(e['ci95_detrended'][1], lang)}]" if e['ci95_detrended'] else ''),
            ha='left', va='center', fontsize=9, color=S.INK if col != EXC else EXC)

for lang in ('de', 'en'):
    fig, ax = S.base(11.5, 6.0 if EXT_ROW else 5.4)
    mde = res['baseline']['mde_pp_assuming_10_effect_days']
    lim = max([30] + [abs(x) for m in ROWS for lab in ('primary', 'sensitivity') for x in (res['effects'][lab][m]['ci95_detrended'] or [])]
              + [abs(x) for x in ((EXT_ROW or {}).get('ci95_detrended') or [])])
    lim = float(np.ceil(lim / 10) * 10)
    for i, m in enumerate(ROWS):
        y = len(ROWS) - 1 - i
        if mde.get(m): ax.add_patch(plt.Rectangle((-mde[m], y - 0.32), 2 * mde[m], 0.64, color='#000', alpha=0.05, lw=0, zorder=0))
        ax.text(-lim - lim * 0.04, y, CHN[lang][m], ha='right', va='center', fontsize=10, color=S.INK, fontweight='bold' if m != 'recommend_gr' else 'normal')
        e, s = res['effects']['primary'][m], res['effects']['sensitivity'][m]
        if e['detrended'] is None:
            ax.text(0, y, 'ausstehend' if lang == 'de' else 'pending', ha='center', va='center', fontsize=9, color=S.MUTE, style='italic',
                    bbox=dict(facecolor='white', edgecolor='none', pad=1.5)); continue
        effect_row(ax, e, y, S.WAX, lang, lim, f'f3_{m}', s=s)
    y0 = -0.7
    if EXT_ROW:   # Zusatzzeile, durch eine Linie abgesetzt; geht in die Entscheidung nicht ein
        ye = -1.35; y0 = -1.85
        ax.plot([-lim - lim * 0.55, lim * 1.5], [-0.72] * 2, color=S.RULE, lw=0.8, ls=(0, (3, 2)), clip_on=False, zorder=1)
        ax.text(-lim - lim * 0.04, ye, ('Kopfzahl, Erweiterung bis 8.11.\n(nicht vorregistriert, Eintrag %s)' if lang == 'de'
                                        else 'Headline, extension to 8 Nov\n(not pre-registered, entry %s)') % EXT.get('register_entry'),
                ha='right', va='center', fontsize=9.4, color=EXC, style='italic', linespacing=1.25)
        effect_row(ax, EXT_ROW, ye - 0.1, EXC, lang, lim, 'f3_ext_total')
    ax.axvline(0, color=S.INK, lw=0.8)
    ax.set_xlim(-lim, lim); ax.set_ylim(y0, len(ROWS) - 0.3); ax.set_yticks([]); ax.spines['left'].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: num(v, lang, 0)))
    ax.set_xlabel('Differenz Wirkungsfenster − Grundlinie, driftbereinigt, Prozentpunkte' if lang == 'de' else 'Difference effect window − baseline, drift-adjusted, percentage points')
    t = {'de': ('Vorher-Nachher je Kanal',
                'rot: driftbereinigte Differenz mit 95-%-Bootstrap-Intervall über Ankertage · hohl: unbereinigt · blau: Sensitivitäts-Grundlinie 8.–29.9.\n'
                'grau: mindestens erkennbare Verschiebung (Planungswert: zehn Wirkungs-Ankertage, Drift als bekannt angenommen, 80 % Power), vor dem Ereignis berechnet'
                + ('\nocker, unterste Zeile: Kopfzahl der Erweiterung bis Ankertag 8.11., nicht vorregistriert, geht in die Entscheidung nicht ein' if EXT_ROW else '')),
         'en': ('Before and after by channel',
                'red: drift-adjusted difference with 95 % bootstrap interval over anchor days · hollow: unadjusted · blue: sensitivity baseline 8–29 Sep\n'
                'grey: minimum detectable shift (planning value: ten effect anchor days, drift treated as known, 80 % power), computed before the event'
                + ('\nochre, bottom row: headline of the extension to anchor day 8 Nov, not pre-registered, not used for the decision' if EXT_ROW else ''))}[lang]
    ft = SRC[lang] + (' · Anbieter-Mittel OpenAI + Gemini, 10.000 Ziehungen' if lang == 'de' else ' · provider mean OpenAI + Gemini, 10,000 draws')
    if EXT_ROW and (EXT.get('abzug') or {}).get('frozen_at_utc'):
        ft += (f" · Erweiterung: Abzug {utc_hm(EXT['abzug']['frozen_at_utc'], 'de')}" if lang == 'de' else f" · extension: snapshot {utc_hm(EXT['abzug']['frozen_at_utc'], 'en')}")
    S.title(fig, *t); S.footer(fig, ft)
    fig.subplots_adjust(top=0.70 if EXT_ROW else 0.74, bottom=0.15 if EXT_ROW else 0.17, left=0.27, right=0.84); S.save(fig, f'fig3_effects_{lang}', R)

# ------------------------------------------------------------------ Abb. 4: Claude beschreibend
cl = res['claude']
def _mname(m):
    import re as _re
    mm = _re.match(r'claude-(opus|sonnet|haiku)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$', m)
    return (mm.group(1).capitalize() + ' ' + mm.group(2) + ('.' + mm.group(3) if mm.group(3) else '')) if mm else m
def _fam_order(m): return next((i for i, f in enumerate(('opus', 'sonnet', 'haiku')) if f in m), 9)
# Tage-Versatz, damit gleiche Werte nicht übereinander liegen: klein und symmetrisch. Die Punkte vom 07.10.
# liegen damit zwischen der Trennlinie (06.10., 12 Uhr) und der Erscheinen-Linie (07.10., 12 Uhr).
OFF = {'total': -0.3, 'direct': -0.1, 'longtail': 0.1, 'discovery': 0.3}
SEP = xn('2026-10-07') - 0.5     # Trennlinie alte / neue Reihe: 06.10.2026, 12 Uhr
_mdays = {}
for _dd, _x in sorted(cl['days'].items()):
    for _m in (_x.get('by_model') or {}): _mdays.setdefault(_m, []).append(_dd)
def _fam(m): return next((f for f in ('opus', 'sonnet', 'haiku') if f in m), m)
_famn = Counter(_fam(m) for m in cl['model_labels_seen'])
def _mlab(m, lang):
    """Modellname; wechselt das Modell einer Stufe, mit den Messtagen (z. B. Haiku 4.5 (7.10.), Haiku 5.5 (9.10.–5.11.))."""
    s = _mname(m)
    if _famn[_fam(m)] > 1 and _mdays.get(m): s += f" ({drange(_mdays[m][0], _mdays[m][-1], lang)})"
    return s
for lang in ('de', 'en'):
    fig, ax = S.base(11.5, 5.3)
    xa, xb = dt.date(2026, 9, 6), X1
    ax.axvspan(xn(WIN['effect'][0]) - 0.5, xn(WIN['effect'][1]) + 0.5, color=S.SAND, alpha=0.13, lw=0, zorder=0)
    ax.axvline(xn(EVENT) - 0.5, color=S.WAX, lw=1.0)
    ax.text(xn(EVENT) - 0.2, 110, 'Erscheinen 8.10.' if lang == 'de' else 'Release 8 Oct', fontsize=8.4, color=S.WAX, va='top', fontweight='bold')
    style = {'total': (S.INK, 'o', 42), 'direct': (S.WAX, 's', 26), 'longtail': ('#b0763a', '^', 26), 'discovery': (S.BLUE, 'D', 22)}
    old = (cl.get('old_series') or {}).get('days') or {}
    have = False
    for c, (col, mk, sz) in style.items():
        o = OFF[c]
        # alte Reihe (feste aeltere Modelle, nur Ankertage): duenn gestrichelt, nicht vergleichbar
        op = [(dd, x['provider_mean'][c]) for dd, x in sorted(old.items()) if (x.get('provider_mean') or {}).get(c) is not None]
        if op:
            ax.plot([xn(a) + o for a, _ in op], [v for _, v in op], color=col, lw=0.9, alpha=0.45, ls=(0, (3, 2)), zorder=2, gid=f'f4_{c}_old_line')
            ax.scatter([xn(a) + o for a, _ in op], [v for _, v in op], s=sz * 0.45, color=col, marker=mk, alpha=0.45, lw=0, zorder=2, gid=f'f4_{c}_old')
        # neue Reihe: Linie = Anbieter Claude (Mittel der Modelle), kleine helle Punkte = einzelne Modelle
        pts = [(dd, x['provider_mean'][c]) for dd, x in sorted(cl['days'].items()) if (x.get('provider_mean') or {}).get(c) is not None]
        mp = [(dd, v[c]) for dd, x in sorted(cl['days'].items()) for v in (x.get('by_model') or {}).values() if v.get(c) is not None]
        if pts:
            have = True
            ax.scatter([xn(a) + o for a, _ in mp], [v for _, v in mp], s=sz * 0.35, color=col, marker=mk, zorder=2, lw=0, alpha=0.35, gid=f'f4_{c}_models')
            ax.scatter([xn(a) + o for a, _ in pts], [v for _, v in pts], s=sz, color=col, marker=mk, zorder=3, lw=0, label=CHN[lang][c], gid=f'f4_{c}_mean')
            ax.plot([xn(a) + o for a, _ in pts], [v for _, v in pts], color=col, lw=1.4, zorder=3, gid=f'f4_{c}_line')
    if not have:
        ax.text(xn('2026-10-22'), 50, ('Grundlinienmessung 7.10. ausstehend\nAnkertage ab 9.10.' if lang == 'de' else 'baseline measurement 7 Oct pending\nanchor days from 9 Oct'),
                fontsize=9.5, color=S.MUTE, ha='center', va='center', style='italic')
    else:
        ax.legend(frameon=False, fontsize=8.6, loc='lower right', bbox_to_anchor=(1.0, 1.01), ncol=4, borderaxespad=0)
    ax.axvline(SEP, color='#999', lw=0.6, ls=(0, (2, 2)), gid='f4_sep')
    ax.text(SEP - 1.1, 68, ('bis 6.10.: ältere Modelle\n(gestrichelt, nicht vergleichbar)' if lang == 'de' else 'until 6 Oct: older models\n(dashed, not comparable)'),
            fontsize=7.8, color=S.MUTE, ha='right', va='top', style='italic')
    ax.set_xlim(xn(xa), xn(xb)); ax.set_ylim(-10, 111); ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{int(v)} %'))
    ax.grid(axis='y', color=S.RULE, lw=0.4); ax.spines['left'].set_visible(False); ax.tick_params(axis='y', length=0)
    ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=[1, 8, 15, 22]))   # ohne 29.: sonst überlappen 29 Sep und 1 Oct
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: dlab(mdates.num2date(v).date(), lang)))
    neu =', '.join(_mlab(m, lang) for m in sorted(cl['model_labels_seen'], key=lambda m: (_fam_order(m), (_mdays.get(m) or [''])[0]))) or ('folgt' if lang == 'de' else 'to follow')
    alt = ', '.join(_mname(m) for m in sorted((cl.get('old_series') or {}).get('models', []), key=_fam_order))
    sh = num(max(abs(v) for v in OFF.values()), lang)
    t = {'de': ('Claude auf claude.ai, beschreibend',
                f'Ab 7.10. je das neueste Opus-, Sonnet- und Haiku-Modell (Websuche, Inkognito): {neu}\n'
                f'Linie = Mittel der Modelle (Anbieter Claude) · helle Punkte = einzelne Modelle · Kanäle um bis zu ±{sh} Tage versetzt gezeichnet\n'
                f'Bis 6.10. gestrichelt, nicht vergleichbar: {alt} · Grundlinie 7.10., danach Ankertage · keine Signifikanzaussage'),
         'en': ('Claude on claude.ai, descriptive',
                f'From 7 Oct the newest Opus, Sonnet and Haiku model each (web search, incognito): {neu}\n'
                f'line = mean of the models (provider Claude) · light points = individual models · channels drawn offset by up to ±{sh} days\n'
                f'Until 6 Oct dashed, not comparable: {alt} · baseline 7 Oct, then anchor days · no significance judgement')}[lang]
    S.title(fig, *t); S.footer(fig, SRC[lang])
    fig.subplots_adjust(top=0.71, bottom=0.11, left=0.07, right=0.97); S.save(fig, f'fig4_claude_{lang}', R)

# ------------------------------------------------------------------ Abb. 5: Trefferquote (Robustheit, Änderung 2 vom 07.10.2026)
HROWS = ['hit_total', 'hit_direct', 'hit_longtail', 'hit_discovery', 'hit_recommend_gr']
HN = {'de': {'hit_total': 'alle 16 Fragen', 'hit_direct': 'Direkt (D1–D3)', 'hit_longtail': 'Saga-Wissen (L1, L2)', 'hit_discovery': 'Empfehlung (10 Fragen)', 'hit_recommend_gr': 'davon GR1–GR6'},
      'en': {'hit_total': 'all 16 questions', 'hit_direct': 'Direct (D1–D3)', 'hit_longtail': 'Saga knowledge (L1, L2)', 'hit_discovery': 'Recommendation (10 questions)', 'hit_recommend_gr': 'of which GR1–GR6'}}
for lang in ('de', 'en'):
    fig, ax = S.base(11.5, 5.4)
    mde = res['baseline']['mde_pp_assuming_10_effect_days']
    lim = max([30] + [abs(x) for m in HROWS for lab in ('primary', 'sensitivity') for x in (res['effects'][lab][m]['ci95_detrended'] or [])])
    lim = float(np.ceil(lim / 10) * 10)
    for i, m in enumerate(HROWS):
        y = len(HROWS) - 1 - i
        bl = res['baseline']['baseline'][m]['provider_balanced_mean']
        if mde.get(m): ax.add_patch(plt.Rectangle((-mde[m], y - 0.32), 2 * mde[m], 0.64, color='#000', alpha=0.05, lw=0, zorder=0))
        if bl is not None and 100 - bl < lim:   # Decke: mehr als 100 % Trefferquote ist nicht möglich
            ax.plot([100 - bl] * 2, [y - 0.34, y + 0.34], color=S.INK, lw=1.4, zorder=2, gid=f'f5_{m}_ceiling')
            near = 100 - bl > lim * 0.85      # nahe am rechten Rand: Beschriftung links vom Strich, damit sie den Wertetext nicht berührt
            ax.text(100 - bl + (-1 if near else 1) * lim * 0.01, y + 0.3, ('Decke' if lang == 'de' else 'ceiling'), fontsize=7.8, color=S.INK, va='top',
                    ha='right' if near else 'left')
        ax.text(-lim - lim * 0.04, y, HN[lang][m] + (f"  ({num(bl, lang)} %)" if bl is not None else ''), ha='right', va='center', fontsize=10, color=S.INK,
                fontweight='bold' if m != 'hit_recommend_gr' else 'normal')
        e, s = res['effects']['primary'][m], res['effects']['sensitivity'][m]
        if e['detrended'] is None:
            ax.text(0, y, 'ausstehend' if lang == 'de' else 'pending', ha='center', va='center', fontsize=9, color=S.MUTE, style='italic',
                    bbox=dict(facecolor='white', edgecolor='none', pad=1.5)); continue
        effect_row(ax, e, y, S.WAX, lang, lim, f'f5_{m}', s=s)
    ax.axvline(0, color=S.INK, lw=0.8)
    ax.set_xlim(-lim, lim); ax.set_ylim(-0.7, len(HROWS) - 0.3); ax.set_yticks([]); ax.spines['left'].set_visible(False)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: num(v, lang, 0)))
    ax.set_xlabel('Differenz der Trefferquote Wirkungsfenster − Grundlinie, driftbereinigt, Prozentpunkte' if lang == 'de' else 'Difference in hit rate effect window − baseline, drift-adjusted, percentage points')
    rule = res['direct_effect_rule']['primary']
    rtxt = {'de': {None: 'ausstehend', 'berichtet': 'Effekt berichtet', 'nicht_belastbar': 'nicht belastbar', 'kein_effekt': 'kein Punkt-Effekt'},
            'en': {None: 'pending', 'berichtet': 'effect reported', 'nicht_belastbar': 'not robust', 'kein_effekt': 'no point effect'}}[lang][rule.get('verdict')]
    t = {'de': ('Trefferquote je Kanal (Robustheit)',
                'Trefferquote = Anteil der Antworten mit Bewertung über null · in Klammern: Grundlinie, Mittel beider Anbieter · rot: driftbereinigt mit 95-%-Intervall · hohl: unbereinigt · blau: Sensitivität\ngrau: mindestens erkennbare Verschiebung · Strich: Decke (100 % minus Grundlinie) · Direkt: nur Vorzeichenprüfung (Änderung 3), Stand: ' + rtxt),
         'en': ('Hit rate by channel (robustness)',
                'Hit rate = share of answers scored above zero · in brackets: baseline, mean of both providers · red: drift-adjusted with 95 % interval · hollow: unadjusted · blue: sensitivity\ngrey: minimum detectable shift · tick: ceiling (100 % minus baseline) · Direct: sign check only (amendment 3), state: ' + rtxt)}[lang]
    S.title(fig, *t); S.footer(fig, SRC[lang] + (' · Änderung 2 der Vorregistrierung vom 07.10.2026' if lang == 'de' else ' · amendment 2 of the pre-registration, 7 Oct 2026'))
    fig.subplots_adjust(top=0.74, bottom=0.17, left=0.29, right=0.84); S.save(fig, f'fig5_hitrate_{lang}', R)
