#!/usr/bin/env python3
"""Bericht 04 (Buchstart): Site-Seiten (DE+EN, Astro) aus REPORT_*.md. Muster wie Bericht 03 (build_site_pages.py):
gleicher Markdown-Konverter, Figuren flach unter public/research/figures/ mit Praefix r04-2026_, ScholarlyArticle-JSON-LD.
Schreibt nach site_staging/ (pages_de, pages_en, figures); kein Commit, kein Deploy.

Aufruf:  PUBDATE=JJJJ-MM-TT REPORT04_DOI=10.5281/zenodo.<n> build_site_pages.py
         build_site_pages.py --probe
Kopfangaben seit 08.11.2026 ohne feste Platzhalter:
  Kernaussage (description)  aus data/results.json: effects.primary.total und hypothesis_order
  Datenstand                 aus data/results.json: freeze.post.effect_freeze.frozen_at_utc (wie im Bericht)
  Fassung der Vorregistrierung aus data/results.json: preregistration.version
  Lesezeit                   aus der Wortzahl von REPORT_*.md (WPM Wörter je Minute)
  Erscheinungsdatum          aus PUBDATE (Umgebung oder --pubdate)
  DOI                        aus REPORT04_DOI (Umgebung oder --doi)
Ohne DOI oder PUBDATE bricht der Bau ab. --probe erlaubt einen Probebau: ohne DOI bleibt [[DOI]] im Zitiervorschlag
stehen, ohne PUBDATE gilt das heutige Datum. Andere offene Marken, lokale Pfade oder ein Bericht, der nicht zu
results.json passt, brechen den Bau immer ab (im Probebau: Abgleich mit results.json nur als WARNUNG)."""
import argparse, html, json, os, re, shutil, sys
from datetime import date
from pathlib import Path
R = Path(__file__).resolve().parent.parent
OUT = R/'site_staging'   # Entwurf; Uebernahme ins Site-Repositorium erst nach Freigabe
PFX = 'r04-2026_'
SLUG = {'de': '04-buchstart-ki-zitation', 'en': '04-book-launch-ai-citation'}
sys.path.insert(0, str(Path(__file__).parent)); from figmeta import FIGS
EXT = "target='_blank' rel='noopener'"
WPM = 240   # Lesezeit: Wörter je Minute (Mittel der Angaben bei Bericht 03 und Q3 / 2026)
DOI_RE = re.compile(r"10\.5281/zenodo\.\d+")
MON_DE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
MON_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

ap = argparse.ArgumentParser(description='Bericht 04: Site-Seiten DE und EN nach site_staging/')
ap.add_argument('--probe', action='store_true', help='Probebau: ohne DOI bleibt [[DOI]] stehen, ohne PUBDATE gilt das heutige Datum')
ap.add_argument('--pubdate', default=os.environ.get('PUBDATE', ''), help='Erscheinungsdatum JJJJ-MM-TT (sonst Umgebung PUBDATE)')
ap.add_argument('--doi', default=os.environ.get('REPORT04_DOI', ''), help='DOI 10.5281/zenodo.<n> (sonst Umgebung REPORT04_DOI)')
ARGS = ap.parse_args()
def stop(msg): sys.exit('ABBRUCH: ' + msg)
def warn_or_stop(msg):
    if ARGS.probe: print('WARNUNG (Probe): ' + msg)
    else: stop(msg)

DOI = ARGS.doi.strip()
if DOI and not DOI_RE.fullmatch(DOI): stop(f'DOI {DOI!r} hat nicht die Form 10.5281/zenodo.<Ziffern>')
if not DOI:
    if ARGS.probe: print('PROBE: keine DOI gesetzt, [[DOI]] bleibt im Zitiervorschlag stehen; nicht zur Veröffentlichung.')
    else: stop('REPORT04_DOI (oder --doi) ist nicht gesetzt (README Schritt 4). Probebau ohne DOI nur mit --probe.')
if ARGS.pubdate.strip():
    try: PUB = date.fromisoformat(ARGS.pubdate.strip())
    except ValueError: stop(f'PUBDATE {ARGS.pubdate!r} ist kein Datum der Form JJJJ-MM-TT')
elif ARGS.probe:
    PUB = date.today(); print(f'PROBE: PUBDATE nicht gesetzt, Erscheinungsdatum = heute ({PUB.isoformat()}).')
else:
    stop('PUBDATE (oder --pubdate) ist nicht gesetzt (README Schritt 6). Probebau nur mit --probe.')
PUBDATE = PUB.isoformat()

# ---------------------------------------------------------------- Kopfangaben aus results.json
D = json.loads((R/'data'/'results.json').read_text(encoding='utf-8'))
if D.get('phase') != 'beobachtung_laufend': stop(f"results.json phase = {D.get('phase')!r}, erwartet beobachtung_laufend")
TOT = D['effects']['primary']['total']; HO = D['hypothesis_order']
if TOT.get('status') != 'abgeschlossen' or HO.get('status') != 'abgeschlossen': stop('Hauptanalyse in results.json nicht abgeschlossen')
FZD = date.fromisoformat(D['freeze']['post']['effect_freeze']['frozen_at_utc'][:10])
if PUB < FZD: stop(f'Erscheinungsdatum {PUBDATE} liegt vor dem Datenstand {FZD.isoformat()}')
PRV = re.fullmatch(r'v(\d+\.\d+) · (\d{4}-\d{2}-\d{2})', D['preregistration']['version'])
if not PRV: stop(f"preregistration.version {D['preregistration']['version']!r} nicht lesbar")
PRV_N, PRV_D = PRV.group(1), date.fromisoformat(PRV.group(2))

def num(x, lang, nd=2, sign=False):   # wie build/fill_texts.py
    s = f'{abs(x):,.{nd}f}'
    if lang == 'de': s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    if x < 0 and round(abs(x), nd) != 0: s = '−' + s
    elif sign and round(x, nd) != 0: s = '+' + s
    return s
def dlong(d, lang):
    return f'{d.day}. {MON_DE[d.month-1]} {d.year}' if lang == 'de' else f'{d.day} {MON_EN[d.month-1]} {d.year}'

def kernaussage(lang):
    """Ein Satz: driftbereinigte Kopfzahl mit Intervall, Entscheidung über die Nullhypothese, Reihenfolge-Hypothese.
    Formuliert nur für den eingetretenen Fall (Intervall enthält die Null); jeder andere Fall bricht ab und braucht
    eine neue, geprüfte Formulierung."""
    if TOT['ci_excludes_zero']: stop('Kopfzahl-Intervall schließt die Null aus: Kernaussage neu formulieren')
    est = num(TOT['detrended'], lang, sign=True); lo, hi = (num(v, lang) for v in TOT['ci95_detrended'])
    supported = HO['verdict'] == 'direkt_frueher'   # Erfolgskriterium: Direkt-Alarm vor Empfehlung oder ohne Empfehlungs-Alarm
    if HO['verdict'] not in ('keine_abweichung', 'direkt_frueher', 'gleichzeitig', 'empfehlung_frueher'): stop(f"hypothesis_order.verdict {HO['verdict']!r} unbekannt")
    if lang == 'de':
        anchor = f'{est} Prozentpunkte (95-%-Intervall {lo} bis {hi})'
        s = (f'Die driftbereinigte Differenz der Kopfzahl zur Grundlinie beträgt {anchor}; die Nullhypothese wird nicht verworfen, '
             + ('die Reihenfolge-Hypothese wird gestützt.' if supported else 'die Reihenfolge-Hypothese erhält keine Stütze.'))
    else:
        anchor = f'{est} percentage points (95 % interval {lo} to {hi})'
        s = (f'The drift-adjusted difference of the headline to the baseline is {anchor}; the null hypothesis is not rejected and '
             + ('the order hypothesis is supported.' if supported else 'the order hypothesis receives no support.'))
    return s, anchor

def lesezeit(md, lang):
    txt = '\n'.join(l for l in md.splitlines() if not re.fullmatch(r'\s*(\|[\s:|-]*\||\[\[FIG\d\]\]|---)\s*', l))
    words = len(re.findall(r'\w+(?:[-–.,’\']\w+)*', txt))
    mins = max(1, round(words / WPM))
    return (f'{mins} Minuten Lesezeit' if lang == 'de' else f'{mins} min read'), words

def linkify(raw):
    p = html.escape(raw, quote=False)
    p = re.sub(r"(Abbildung|Figure) (\d)", lambda m: f"<a class='xref' href='#fig{m.group(2)}'>{m.group(1)} {m.group(2)}</a>", p)
    p = re.sub(r"(Tabelle|Table) (\d)", lambda m: f"<a class='xref' href='#tab{m.group(2)}'>{m.group(1)} {m.group(2)}</a>", p)
    p = re.sub(r"\b(Abschnitt|[Ss]ection) (\d+)", lambda m: f"<a class='xref' href='#sec{m.group(2)}'>{m.group(1)} {m.group(2)}</a>", p)
    p = re.sub(r"(10\.5281/zenodo\.\d+)", lambda m: f"<a class='ext' href='https://doi.org/{m.group(1)}' {EXT}>{m.group(1)}</a>", p)
    p = re.sub(r"(?<![\w/])(github\.com/marintkael/marin-research-tools)(?![\w/-])", lambda m: f"<a class='ext' href='https://{m.group(1)}' {EXT}>{m.group(1)}</a>", p)
    return p
def cell(c):
    c = c.strip(); m = re.match(r"^(\d+) \(([\d.,]+ %)\)$", c)
    if m: return f"<span class='v'>{html.escape(m.group(1))}</span><span class='s'>{html.escape(m.group(2))}</span>"
    return html.escape(c, quote=False)
def body_html(md, lang):
    F = FIGS[lang]; out = []; rows = []; sec = [None, 0]   # aktueller Abschnitt, Zähler der Unterabschnitte
    def flush():
        nonlocal rows
        if not rows: return
        hdr = rows[0]; body = rows[2:]
        h = "<div class='tablewrap'><table class='wp-table'><thead><tr>" + "".join(f"<th>{html.escape(c.strip(), quote=False)}</th>" for c in hdr.strip('|').split('|')) + "</tr></thead><tbody>"
        for r in body:
            cs = r.strip('|').split('|'); h += "<tr>" + f"<td>{html.escape(cs[0].strip(), quote=False)}</td>" + "".join(f"<td>{cell(c)}</td>" for c in cs[1:]) + "</tr>"
        out.append(h + "</tbody></table></div>"); rows = []
    for line in md.splitlines():
        if line.startswith('|'): rows.append(line); continue
        if rows: flush()
        s = line.strip()
        if not s or s.startswith('# ') or s.startswith('## '): continue
        if s == '---': out.append('<hr/>'); continue
        if s.startswith('#### '):   # Unterabschnitt (08.11.2026: Erweiterung in Abschnitt 7), nummeriert wie im Paper (7.1)
            if sec[0] is None: stop(f'Unterabschnitt ohne nummerierten Abschnitt: {s}')
            sec[1] += 1; sid = f'{sec[0]}.{sec[1]}'
            out.append(f"<h3 id='sec{sec[0]}-{sec[1]}'>{sid} {html.escape(s[5:], quote=False)}</h3>"); continue
        if s.startswith('#') and not s.startswith('### '): stop(f'nicht unterstützte Überschrift: {s[:60]}')
        if s.startswith('### '):
            mh = re.match(r"(\d+)\.\s*(.*)", s[4:])
            sec[0], sec[1] = (mh.group(1) if mh else None), 0
            if mh: out.append(f"</section><section id='sec{mh.group(1)}'><p class='section-num'>{mh.group(1)}</p><h2>{html.escape(mh.group(2), quote=False)}</h2>")
            else: out.append(f"</section><section class='wp-abstract'><h2>{html.escape(s[4:], quote=False)}</h2>")
            continue
        if s.startswith('*') and s.endswith('*'):
            if s.startswith('*Marin T. Kael'): continue
            mt = re.match(r"\*(Tabelle|Table) (\d)", s); tid = f" id='tab{mt.group(2)}'" if mt else ''
            out.append(f"<p class='wp-meta tabcap'{tid}>{linkify(s.strip('*'))}</p>"); continue
        m = re.fullmatch(r"\[\[FIG(\d)\]\]", s)
        if m:
            n = int(m.group(1)); name, cap = F[n]
            out.append(f"<figure id='fig{n}' class='wp-figure'><img src='/research/figures/{PFX}{name}.png' alt='{html.escape(cap)}' loading='lazy'/><figcaption>{html.escape(cap, quote=False)}</figcaption></figure>"); continue
        out.append(f"<p>{linkify(s)}</p>")
    if rows: flush()
    return "\n".join(out).replace('</section>', '', 1) + '</section>'
META = {'de': dict(title='Bericht 04 · Buchstart und KI-Zitation · Marin T. Kael Research',
                   desc='Bericht 04: Vorher-Nachher-Auswertung der Vorregistrierung Q7 zum Erscheinen von »Das vierte Feld« am 8. Oktober 2026. {kern}',
                   h1='Bericht 04 · Buchstart und KI-Zitation', sub='Verändert das Erscheinen von »Das vierte Feld« das Zitationsverhalten von KI-Antwortmaschinen?',
                   num='Forschungsbericht · 04 · Datenstand {datenstand}', lang='de-DE',
                   headline='Bericht 04: Buchstart und KI-Zitation, Vorher-Nachher-Auswertung der Vorregistrierung Q7',
                   alt='Report 04: Book launch and AI citation, before-after analysis of pre-registration Q7',
                   prereg='Vorregistrierung Q7 – Buch-Erscheinen (Fassung {n}, {d:%d.%m.%Y})'),
        'en': dict(title='Report 04 · Book Launch and AI Citation · Marin T. Kael Research',
                   desc='Report 04: before-after analysis of pre-registration Q7 on the release of “Das vierte Feld” on 8 October 2026. {kern}',
                   h1='Report 04 · Book Launch and AI Citation', sub='Does the release of “Das vierte Feld” change how AI answer engines cite its author?',
                   num='Research report · 04 · data state {datenstand}', lang='en',
                   headline='Report 04: Book launch and AI citation, before-after analysis of pre-registration Q7',
                   alt='Bericht 04: Buchstart und KI-Zitation, Vorher-Nachher-Auswertung der Vorregistrierung Q7',
                   prereg='Pre-registration Q7 – book release (version {n}, {dl})')}
CSS = (R/'build'/'wp_style.css').read_text(encoding='utf-8')
for lang in ('de', 'en'):
    md = (R/('REPORT_DE.md' if lang == 'de' else 'REPORT_EN.md')).read_text(encoding='utf-8'); m = dict(META[lang])
    kern, anchor = kernaussage(lang); datenstand = dlong(FZD, lang); read, words = lesezeit(md, lang)
    # Abgleich Bericht <-> results.json: Kopfzahl-Satz der Zusammenfassung und Datenstand müssen im Bericht stehen
    if anchor not in md: warn_or_stop(f'REPORT_{lang.upper()}.md enthält die Kopfzahl aus results.json nicht ({anchor}); fill_texts.py ausführen')
    stand = ('Datenstand ' if lang == 'de' else 'data state ') + datenstand
    if stand not in md: warn_or_stop(f'REPORT_{lang.upper()}.md nennt nicht „{stand}“')
    m['desc'] = m['desc'].format(kern=kern); m['num'] = m['num'].format(datenstand=datenstand); m['read'] = read
    m['prereg'] = m['prereg'].format(n=PRV_N, d=PRV_D, dl=dlong(PRV_D, 'en'))
    dated = dlong(PUB, lang)
    if DOI: md = md.replace('[[DOI]]', DOI.split('zenodo.')[-1])
    doi_ld = (f"  'sameAs': 'https://doi.org/{DOI}',\n  'identifier': 'doi:{DOI}',\n") if DOI else ''
    path = ('/research/berichte/' if lang == 'de' else '/en/research/reports/') + SLUG[lang]
    alt_path = ('/en/research/reports/' + SLUG['en']) if lang == 'de' else ('/research/berichte/' + SLUG['de'])
    up = '../../../' if lang == 'de' else '../../../../'
    astro = f"""---
import Base from '{up}layouts/Base.astro';
import Header from '{up}components/Header.astro';
import Footer from '{up}components/Footer.astro';
import {{ siteConfig as s }} from '{up}config/site';

const title = `{m['title']}`;
const description = `{m['desc']}`;
const publicationDate = '{PUBDATE}';

const articleSchema = {{
  '@context': 'https://schema.org',
  '@type': 'ScholarlyArticle',
{doi_ld}  '@id': new URL('{path}', Astro.site).toString(),
  'headline': '{m['headline']}',
  'alternativeHeadline': '{m['alt']}',
  'description': description,
  'inLanguage': '{m['lang']}',
  'datePublished': publicationDate,
  'dateModified': publicationDate,
  'author': {{ '@type': 'Person', 'name': s.author, 'sameAs': 'https://www.wikidata.org/entity/Q140004504',
    'identifier': [
      {{ '@type': 'PropertyValue', 'propertyID': 'ORCID', 'value': '0009-0006-2105-8190', 'url': 'https://orcid.org/0009-0006-2105-8190' }},
      {{ '@type': 'PropertyValue', 'propertyID': 'Wikidata', 'value': 'Q140004504' }} ] }},
  'publisher': {{ '@type': 'Organization', 'name': 'Marin T. Kael – KI-Zitations-Feldlabor', 'url': new URL('/research', Astro.site).toString() }},
  'license': 'https://creativecommons.org/licenses/by/4.0/',
  'isBasedOn': [
    {{ '@type': 'CreativeWork', 'name': '{m['prereg']}', 'url': 'https://github.com/marintkael/marin-research-tools/blob/main/pre_registrations/Q7_book_release.yaml' }},
    {{ '@type': 'SoftwareSourceCode', 'name': 'marin-research-tools / pre_registrations', 'url': 'https://github.com/marintkael/marin-research-tools/tree/main/pre_registrations' }} ],
  'citation': [
    {{ '@type': 'CreativeWork', 'name': 'Methodology Note 01 v4.0', 'identifier': 'doi:10.5281/zenodo.20364173', 'url': 'https://doi.org/10.5281/zenodo.20364173' }},
    {{ '@type': 'CreativeWork', 'name': 'Bericht 03 · Gefunden, nicht empfohlen', 'identifier': 'doi:10.5281/zenodo.22015495', 'url': 'https://doi.org/10.5281/zenodo.22015495' }},
    {{ '@type': 'CreativeWork', 'name': 'Validierungsbericht Q3 / 2026', 'identifier': 'doi:10.5281/zenodo.23145378', 'url': 'https://doi.org/10.5281/zenodo.23145378' }} ],
  'keywords': 'pre-registration, before-after analysis, CUSUM, drift, bootstrap, book release, LLM citation, answer engine, OpenAI Search, Gemini, Claude',
}};
---

<Base title={{title}} description={{description}}>
  <Header />
  <main id="main-content" class="wp r04">
    <div class="container">
      <article>
        <header class="wp-head">
          <p class="wp-num">{m['num']}</p>
          <h1>{m['h1']}</h1>
          <p class="wp-subtitle">{m['sub']}</p>
          <p class="wp-meta"><span>{{s.author}}</span> · <time datetime={{publicationDate}}>{dated}</time> · <span>{m['read']}</span> · <a href="{alt_path}">{'English edition' if lang == 'de' else 'Deutsche Fassung'}</a></p>
        </header>
{body_html(md, lang)}
      </article>
    </div>
  </main>
  <Footer />
  <link rel="alternate" hreflang="{'en' if lang == 'de' else 'de'}" href={{new URL('{alt_path}', Astro.site).toString()}} />
  <script type="application/ld+json" set:html={{JSON.stringify(articleSchema)}} />
</Base>

<style>
{CSS}
  .r04 figure.wp-figure{{margin:1.6rem 0 1.8rem}} .r04 figure.wp-figure img{{width:100%;height:auto;border:1px solid #e4e4e4;display:block}}
  .r04 figcaption{{font-size:.82rem;color:#6b6b6b;margin-top:.45rem;line-height:1.45}}
  .r04 .tablewrap{{overflow-x:auto;margin:.6rem 0 1.4rem}} .r04 table.wp-table{{font-size:.8rem}}
  .r04 td .v{{font-weight:600;display:block;font-size:.95rem}} .r04 td .s{{display:block;color:#6b6b6b;font-size:.74rem}}
  .r04 .tabcap{{margin:1.2rem 0 .4rem;color:#444}} .r04 a.xref{{color:inherit;text-decoration:none;border-bottom:1px dotted #999}}
  .r04 a.ext{{color:#6E1010;text-decoration:none;border-bottom:1px solid rgba(110,16,16,.35)}}
</style>
"""
    # Abnahme: nur [[DOI]] darf offen bleiben, und nur ohne DOI; keine lokalen Pfade
    left = sorted(set(re.findall(r'\[\[[^\]]*\]\]', astro)))
    if [x for x in left if x != '[[DOI]]'] or (DOI and left): stop(f'offene Marken in der {lang.upper()}-Seite: {left}')
    if 'XXXXXXXX' in astro: stop(f'DOI-Platzhalter XXXXXXXX in der {lang.upper()}-Seite')
    if re.search(r'/(Users|private|home)/|file://', astro): stop(f'lokaler Pfad in der {lang.upper()}-Seite')
    dest = OUT/('pages_de' if lang == 'de' else 'pages_en'); dest.mkdir(parents=True, exist_ok=True)
    (dest/f"{SLUG[lang]}.astro").write_text(astro, encoding='utf-8')
    print('astro:', dest.relative_to(R)/f"{SLUG[lang]}.astro", '|', m['num'], '|', dated, '|', read, f'({words} Wörter)',
          '| DOI:', DOI or 'offen ([[DOI]])', '| offene Marken:', left or 'keine')
fo = OUT/'figures'; fo.mkdir(parents=True, exist_ok=True)
for f in sorted((R/'figures').glob('fig*_*.png')): shutil.copy2(f, fo/f"{PFX}{f.name}")
print('figures:', len(list(fo.glob(PFX + '*.png'))))
