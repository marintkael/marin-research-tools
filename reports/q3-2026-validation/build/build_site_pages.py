#!/usr/bin/env python3
"""Validierungsbericht Q3/2026: Site-Seiten (DE+EN, Astro) aus REPORT_*.md. Muster wie Bericht 03 (build_site_pages.py):
gleicher Markdown-Konverter, Figuren flach unter public/research/figures/ mit Praefix q3-2026_, ScholarlyArticle-JSON-LD.
Schreibt nach site_staging/ (pages_de, pages_en, figures); kein Commit, kein Deploy."""
import os, re, html, shutil
from pathlib import Path
R = Path(__file__).resolve().parent.parent
OUT = R/'site_staging'   # Entwurf; Uebernahme ins Site-Repositorium erst nach Freigabe
PFX = 'q3-2026_'
SLUG = {'de': 'q3-2026-validierung', 'en': 'q3-2026-validation'}
FIGS = {'de': {1: ('fig5_anchors_de', 'Abb. 1 · Anker-Messflächen: registrierte und nachfolgende Wikidata-Items, Treffer des Knowledge Graph für Autor, Buch und Reihe.'), 2: ('fig2_retest_de', 'Abb. 2 · Wiederhol-Übereinstimmung je Frage und Anbieter: Anteil identischer Bewertung am nächsten Messtag.'), 3: ('fig4_alpha_de', 'Abb. 3 · Cronbachs α je Anbieter mit Bootstrap-95-%-Intervall, vorregistrierte Schwellen und Zahl der Fragen ohne Varianz.'), 4: ('fig1_coverage_de', 'Abb. 4 · Abdeckung je Anbieter. Ein Kästchen je Tag; vollständig, teilweise, nur Fehlerzeilen, Soll-Tag ohne Lauf. Schattierung: Ausfälle laut Lückenregister.'), 5: ('fig3_cusum_de', 'Abb. 5 · Tageswert je Anbieter mit Referenzmitteln und Alarmen der CUSUM-Neubezugs-Variante; E = Ereignis aus dem Lückenregister, M = Wechsel des Modell-Etiketts.')}, 'en': {1: ('fig5_anchors_en', 'Fig. 1 · Anchor surfaces: registered and successor Wikidata items, Knowledge Graph hits for author, book and series.'), 2: ('fig2_retest_en', 'Fig. 2 · Test-retest agreement by question and provider: share of identical score on the next measurement day.'), 3: ('fig4_alpha_en', "Fig. 3 · Cronbach's α by provider with bootstrap 95 % interval, pre-registered thresholds and number of questions without variance."), 4: ('fig1_coverage_en', 'Fig. 4 · Coverage by provider. One cell per day; complete, partial, error rows only, scheduled day without run. Shading: outages per gap register.'), 5: ('fig3_cusum_en', 'Fig. 5 · Daily value by provider with reference means and alarms of the rebasing CUSUM variant; E = event from the gap register, M = change of model label.')}}
EXT = "target='_blank' rel='noopener'"
def linkify(raw):
    p = html.escape(raw, quote=False)
    p = re.sub(r"(Abbildung|Figure) (\d)", lambda m: f"<a class='xref' href='#fig{m.group(2)}'>{m.group(1)} {m.group(2)}</a>", p)
    p = re.sub(r"(Tabelle|Table) (\d)", lambda m: f"<a class='xref' href='#tab{m.group(2)}'>{m.group(1)} {m.group(2)}</a>", p)
    p = re.sub(r"(Abschnitt|Section) (\d+)", lambda m: f"<a class='xref' href='#sec{m.group(2)}'>{m.group(1)} {m.group(2)}</a>", p)
    p = re.sub(r"(10\.5281/zenodo\.\d+)", lambda m: f"<a class='ext' href='https://doi.org/{m.group(1)}' {EXT}>{m.group(1)}</a>", p)
    p = re.sub(r"(?<![\w/])(github\.com/marintkael/marin-research-tools)(?![\w/-])", lambda m: f"<a class='ext' href='https://{m.group(1)}' {EXT}>{m.group(1)}</a>", p)
    return p
def cell(c):
    c = c.strip(); m = re.match(r"^(\d+) \(([\d.,]+ %)\)$", c)
    if m: return f"<span class='v'>{html.escape(m.group(1))}</span><span class='s'>{html.escape(m.group(2))}</span>"
    return html.escape(c, quote=False)
def body_html(md, lang):
    F = FIGS[lang]; out = []; rows = []
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
        if s.startswith('### '):
            mh = re.match(r"(\d+)\.\s*(.*)", s[4:])
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
META = {'de': dict(title='Validierungsbericht Q3 / 2026 · Marin T. Kael Research',
                   desc='Validierungsbericht Q3 / 2026: Prüfung der sechs Instrument-Hypothesen der Vorregistrierung Q0-INST am Datenstand 1. Oktober 2026. Drei nicht prüfbar, drei nicht bestätigt. Wiederhol-Übereinstimmung 86,6 bis 94,3 Prozent, Cronbachs α 0,41 bis 0,61, fünf unerklärte Abwärts-Alarme, Abdeckungsbilanz je Anbieter, Konsequenzen für Phase 2.',
                   h1='Validierungsbericht Q3 / 2026', sub='Wie verlässlich misst das Programm? Prüfung der sechs Instrument-Hypothesen aus der Vorregistrierung Q0-INST',
                   num='Validierungsbericht · Q3 / 2026 · Datenstand 1. Oktober 2026', lang='de-DE', read='11 Minuten Lesezeit',
                   headline='Validierungsbericht Q3 / 2026: Prüfung der Instrument-Hypothesen der Vorregistrierung Q0-INST',
                   alt='Validation Report Q3 / 2026: A test of the instrument hypotheses of pre-registration Q0-INST'),
        'en': dict(title='Validation Report Q3 / 2026 · Marin T. Kael Research',
                   desc="Validation Report Q3 / 2026: a test of the six instrument hypotheses of pre-registration Q0-INST on the data state of 1 October 2026. Three not testable, three not confirmed. Test-retest agreement 86.6 to 94.3 percent, Cronbach's α 0.41 to 0.61, five unexplained downward alarms, coverage by provider, consequences for phase 2.",
                   h1='Validation Report Q3 / 2026', sub='How reliably does the programme measure? A test of the six instrument hypotheses of pre-registration Q0-INST',
                   num='Validation report · Q3 / 2026 · data state 1 October 2026', lang='en', read='11 min read',
                   headline='Validation Report Q3 / 2026: A test of the instrument hypotheses of pre-registration Q0-INST',
                   alt='Validierungsbericht Q3 / 2026: Prüfung der Instrument-Hypothesen der Vorregistrierung Q0-INST')}
PUBDATE = os.environ.get('PUBDATE', '2026-10-15')
DATED = {'de': '15. Oktober 2026', 'en': '15 October 2026'}
CSS = (R/'build'/'wp_style.css').read_text(encoding='utf-8')
for lang in ('de', 'en'):
    md = (R/('REPORT_DE.md' if lang == 'de' else 'REPORT_EN.md')).read_text(encoding='utf-8'); m = META[lang]
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
  '@id': new URL('{path}', Astro.site).toString(),
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
  'publisher': {{ '@type': 'Organization', 'name': 'Marin T. Kael — KI-Zitations-Feldlabor', 'url': new URL('/research', Astro.site).toString() }},
  'license': 'https://creativecommons.org/licenses/by/4.0/',
  'isBasedOn': [
    {{ '@type': 'CreativeWork', 'name': 'Vor-Registrierung Q0-INST — Pre-Launch-Instrument-Validierung', 'identifier': 'doi:10.5281/zenodo.20125967', 'url': 'https://doi.org/10.5281/zenodo.20125967' }},
    {{ '@type': 'SoftwareSourceCode', 'name': 'marin-research-tools / pre_registrations', 'url': 'https://github.com/marintkael/marin-research-tools/tree/main/pre_registrations' }} ],
  'citation': [
    {{ '@type': 'CreativeWork', 'name': 'Methodology Note 01 v4.0', 'identifier': 'doi:10.5281/zenodo.20364173', 'url': 'https://doi.org/10.5281/zenodo.20364173' }},
    {{ '@type': 'CreativeWork', 'name': 'Bericht 03 · Gefunden, nicht empfohlen', 'identifier': 'doi:10.5281/zenodo.22015495', 'url': 'https://doi.org/10.5281/zenodo.22015495' }},
    {{ '@type': 'CreativeWork', 'name': 'Wikidata Identitäts-Snapshot T+0', 'identifier': 'doi:10.5281/zenodo.20126038', 'url': 'https://doi.org/10.5281/zenodo.20126038' }} ],
  'keywords': 'instrument validation, test-retest reliability, CUSUM, Cronbach alpha, pre-registration, LLM citation, answer engine, OpenAI Search, Gemini, Claude, Wikidata, Knowledge Graph',
}};
---

<Base title={{title}} description={{description}}>
  <Header />
  <main id="main-content" class="wp rq3">
    <div class="container">
      <article>
        <header class="wp-head">
          <p class="wp-num">{m['num']}</p>
          <h1>{m['h1']}</h1>
          <p class="wp-subtitle">{m['sub']}</p>
          <p class="wp-meta"><span>{{s.author}}</span> · <time datetime={{publicationDate}}>{DATED[lang]}</time> · <span>{m['read']}</span> · <a href="{alt_path}">{'English edition' if lang == 'de' else 'Deutsche Fassung'}</a></p>
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
  .rq3 figure.wp-figure{{margin:1.6rem 0 1.8rem}} .rq3 figure.wp-figure img{{width:100%;height:auto;border:1px solid #e4e4e4;display:block}}
  .rq3 figcaption{{font-size:.82rem;color:#6b6b6b;margin-top:.45rem;line-height:1.45}}
  .rq3 .tablewrap{{overflow-x:auto;margin:.6rem 0 1.4rem}} .rq3 table.wp-table{{font-size:.8rem}}
  .rq3 td .v{{font-weight:600;display:block;font-size:.95rem}} .rq3 td .s{{display:block;color:#6b6b6b;font-size:.74rem}}
  .rq3 .tabcap{{margin:1.2rem 0 .4rem;color:#444}} .rq3 a.xref{{color:inherit;text-decoration:none;border-bottom:1px dotted #999}}
  .rq3 a.ext{{color:#6E1010;text-decoration:none;border-bottom:1px solid rgba(110,16,16,.35)}}
</style>
"""
    dest = OUT/('pages_de' if lang == 'de' else 'pages_en'); dest.mkdir(parents=True, exist_ok=True)
    (dest/f"{SLUG[lang]}.astro").write_text(astro, encoding='utf-8'); print('astro:', dest.relative_to(R)/f"{SLUG[lang]}.astro")
fo = OUT/'figures'; fo.mkdir(parents=True, exist_ok=True)
for f in sorted((R/'figures').glob('fig*_*.png')): shutil.copy2(f, fo/f"{PFX}{f.name}")
print('figures:', len(list(fo.glob(PFX + '*.png'))))
