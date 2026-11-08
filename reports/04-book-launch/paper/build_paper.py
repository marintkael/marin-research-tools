#!/usr/bin/env python3
"""Bericht 04 (Buchstart und KI-Zitation) als Paper im Programm-Standard (Layout wie „Zero to Cited“, Zenodo 20549021):
article 11pt, Letter, 1 in, Latin Modern, zentrierter Titelblock, Abstract, nummerierte Abschnitte.
Zwei eigenständige Fassungen DE und EN aus REPORT_DE.md / REPORT_EN.md. Abbildungen = figures/*.png.

Aufruf:  REPORT04_DOI=10.5281/zenodo.<n> build_paper.py [de] [en]
         build_paper.py --probe [de] [en]
Ohne gültige REPORT04_DOI bricht der Bau ab. --probe erlaubt einen Probebau ohne DOI: der Platzhalter
10.5281/zenodo.XXXXXXXX bleibt im Titelblock und im Zitiervorschlag stehen; ein Probe-PDF ist nicht zur Veröffentlichung.
Seit 08.11.2026: Modellkennungen werden nicht umbrochen (\\mbox), die PDF-Metadaten werden
nach dem Satz auf Titel und Autor bereinigt (pypdf) und mit pdfinfo und pdftotext geprüft; jede Prüfung bricht bei
einem Fehler ab. Seit 08.11.2026 abends: Eigennamen und Kürzel aus NO_HYPH werden nicht getrennt (\\hyphenation in
template.tex aus derselben Liste); der Bau bricht ab, wenn eine Zeile des PDF-Texts innerhalb eines dieser Namen endet."""
import argparse, os, re, shutil, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent; P = R / "paper"
sys.path.insert(0, str(R / "build")); from figmeta import FIGS as _FIGS

AUTHOR = "Marin T. Kael"
DOI_PLACEHOLDER = "10.5281/zenodo.XXXXXXXX"
DOI_RE = re.compile(r"10\.5281/zenodo\.\d+")
ap = argparse.ArgumentParser(description="Bericht 04: Paper DE und EN bauen")
ap.add_argument("langs", nargs="*", help="de und/oder en (Standard: beide)")
ap.add_argument("--probe", action="store_true", help="Probebau ohne DOI (Platzhalter bleibt stehen, nicht zur Veröffentlichung)")
ARGS = ap.parse_args()
LANGS = ARGS.langs or ["de", "en"]
if any(l not in ("de", "en") for l in LANGS): sys.exit(f"ABBRUCH: unbekannte Sprache in {LANGS}; erlaubt sind de und en")
_doi = os.environ.get("REPORT04_DOI", "").strip()
if _doi:
    if not DOI_RE.fullmatch(_doi):
        sys.exit(f"ABBRUCH: REPORT04_DOI={_doi!r} hat nicht die Form 10.5281/zenodo.<Ziffern>")
    DOI = _doi
elif ARGS.probe:
    DOI = DOI_PLACEHOLDER
    print(f"PROBE: REPORT04_DOI nicht gesetzt, Platzhalter {DOI_PLACEHOLDER} bleibt stehen; nicht zur Veröffentlichung.")
else:
    sys.exit("ABBRUCH: REPORT04_DOI ist nicht gesetzt (README Schritt 4: DOI reservieren, dann "
             "REPORT04_DOI=10.5281/zenodo.<n>). Probebau ohne DOI nur mit --probe.")
FINAL = DOI != DOI_PLACEHOLDER

FIG = {l: {k: (v[0], re.sub(r"^(Abb\.|Fig\.) \d · ", "", v[1])) for k, v in d.items()} for l, d in _FIGS.items()}
META = {"de": dict(lang="german", tablename="Tabelle", figurename="Abbildung", datestr="November 2026",
                   affiliation="Unabhängiger Forscher -- KI-Zitations-Feldlabor", abs_h="### Zusammenfassung",
                   ref=r"(Abbildung|Abb\.) (\d)", out="Bericht-04-Buchstart_DE"),
        "en": dict(lang="english", tablename="Table", figurename="Figure", datestr="November 2026",
                   affiliation="Independent researcher -- AI Citation Field Lab", abs_h="### Summary",
                   ref=r"(Figure|Fig\.) (\d)", out="Report-04-Book-Launch_EN")}

# Modellkennungen (claude-haiku-5-5, gpt-…, gemini-…) dürfen nicht am Bindestrich umbrechen: sonst entsteht beim
# Kopieren aus dem PDF eine falsche Kennung (claude-haiku-5- / 5 -> claude-haiku-55). Nur Kennungen mit Ziffer.
MODEL_RE = re.compile(r"(?<![\w\\-])(?:claude|gpt|gemini|chatgpt|o[1-9])-[A-Za-z0-9](?:[A-Za-z0-9.\-]*[A-Za-z0-9])?")
_SKIP = re.compile(r"\\(?:url|href|includegraphics(?:\[[^\]]*\])?)\{[^{}]*\}")   # URL- und Dateiargumente unberührt

# Eigennamen und Kürzel ohne Trennung: beim Kopieren aus dem PDF entstünden sonst zerrissene Namen („Ope-/nAI“, „Ge-/mini“,
# „CU-/SUM“). Die Liste füllt \hyphenation{…} in template.tex; split_names() prüft den fertigen PDF-Text.
NO_HYPH = ("CUSUM", "OpenAI", "Gemini", "Claude", "Sonnet", "Opus", "Haiku", "Google", "Pauline", "Kael", "Marin",
           "Zenodo", "ORCID", "GitHub")
# Monatsnamen bleiben trennbar (ganz gesperrt erzwangen sie weit gesperrte Zeilen); über den Seitenumbruch verhindert
# \brokenpenalty jede Trennung.
_LINE_END = re.compile(r"([^\W\d_]+)[-­‐]$")
_LINE_START = re.compile(r"[^\W\d_]+")

def split_names(txt):
    """Zeilenpaare, deren Trennstrich mitten in einem Namen aus NO_HYPH steht (Bruchstück vor und nach dem Strich ergeben
    genau den Namen). Ein echter Bindestrich nach dem vollständigen Namen („Gemini-/Antwort“) zählt nicht."""
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    hits = []
    for a, b in zip(lines, lines[1:]):
        ma, mb = _LINE_END.search(a), _LINE_START.match(b)
        if ma and mb and ma.group(1) + mb.group(0) in NO_HYPH:
            hits.append(f"{ma.group(1)}-/{mb.group(0)}")
    return hits

def model_ids(text):
    return sorted({m for m in MODEL_RE.findall(text) if re.search(r"\d", m)})

def protect_ids(t):
    def wrap(s):
        return MODEL_RE.sub(lambda q: "\\mbox{%s}" % q.group(0) if re.search(r"\d", q.group(0)) else q.group(0), s)
    out, pos = [], 0
    for mo in _SKIP.finditer(t):
        out.append(wrap(t[pos:mo.start()])); out.append(mo.group(0)); pos = mo.end()
    out.append(wrap(t[pos:]))
    return "".join(out)

# 08.11.2026: geschützte Leerzeichen (~) zwischen Tag und Monat, Verweiswort und Nummer, Zahl und Prozent-Einheit, damit
# der Satz dort nicht umbricht (pdftotext-Prüfung „8. / November“, „Abschnitt / 7“). URL- und Dateiargumente unberührt.
_MON_DE = "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
_MON_EN = "January|February|March|April|May|June|July|August|September|October|November|December"
_TIES = [re.compile(r"(?<![\w.,])(\d{1,2}\.) (?=(?:%s)\b)" % _MON_DE),
         re.compile(r"(?<![\w.,])(\d{1,2}) (?=(?:%s)\b)" % _MON_EN),
         re.compile(r"\b(Abschnitt|Abschnitten|Abschnitte|Tabelle|Abbildung|Eintrag|Einträge|Einträgen|Fassung|Änderung|Änderungen|"
                    r"Section|section|sections|Table|table|Figure|figure|entry|entries|version|amendment|amendments) (?=\d)"),
         # Zahl und folgendes Wort zusammen („13~Ankertage“, „10.000~Ziehungen“, „157~der“), Uhrzeit und Zeitzone
         re.compile(r"(?<![\w.,])(\d[\d.,]*) (?=(?:Ankertage|Ankertagen|Wirkungstage|Wirkungstagen|Tage|Tagen|Ziehungen|Startwerte|Startwerten|"
                    r"Läufe|Antworten|Fragen|Prozentpunkte|Punkte|Punkten|Modelle|Messungen|Zeilen|der \d|anchor|days|draws|seeds|answers|"
                    r"questions|points|percentage|models|measurements|rows|of the \d)\b)"),
         re.compile(r"(\d{1,2}:\d{2}) (?=UTC)"),
         # Bereiche: „GR1~bis~GR6“, „D1~to~D3“, „bis~6,96“
         re.compile(r"\b((?:GR|D|L|C|G|R)\d) (?=(?:bis|to) )"),
         re.compile(r"\b(bis|to) (?=(?:GR|D|L|C|G|R)\d\b)"),
         # Zahlenintervalle „(−3,59~bis~6,68)“: nur Dezimalzahlen, damit Datumsbereiche umbrechen können
         re.compile(r"(\d) (?=(?:bis|to) [−-]?\d+[.,]\d)"),
         re.compile(r"(?<=\d )(bis|to) (?=[−-]?\d+[.,]\d)"),
         # „Abschnitte 1~und~6“, „percentage~points“
         re.compile(r"(\d) (?=(?:und|and) \d)"),
         re.compile(r"(?<=\d )(und|and) (?=\d)"),
         re.compile(r"\b(percentage) (?=points?\b)"),
         re.compile(r"(\d) (?=Prozent|percent)"),
         # Monat und Jahr bleiben zusammen („7. November / 2026“ auf Seite 1, Hinweis des Autors 08.11.2026)
         re.compile(r"\b((?:%s|%s)) (?=\d{4}\b)" % (_MON_DE, _MON_EN))]

def ties(t):
    def sub(s):
        for rx in _TIES: s = rx.sub(lambda q: q.group(1) + "~", s)
        return s
    out, pos = [], 0
    for mo in _SKIP.finditer(t):
        out.append(sub(t[pos:mo.start()])); out.append(mo.group(0)); pos = mo.end()
    out.append(sub(t[pos:]))
    return "".join(out)

_LAST2 = re.compile(r"([^\s\\{}~]) ([^\s\\{}~]+)(?=\n[ \t]*\n|\n\\item|\n\\end\{(?:itemize|enumerate)\}|\s*$)")

def last_two(t):
    """Letzte zwei Wörter eines Absatzes mit geschütztem Leerzeichen koppeln (nur reine Wörter, keine Befehle)."""
    return _LAST2.sub(lambda q: q.group(1) + "~\\mbox{" + q.group(2) + "}", t)   # letztes Wort zudem ungetrennt

def tex(md, extra=()):
    return subprocess.run(["pandoc", "-f", "markdown-auto_identifiers", "-t", "latex", "--wrap=preserve", *extra],
                          input=md, capture_output=True, text=True, check=True).stdout

def clean_metadata(pdf, title):
    """Metadaten nur Titel und Autor: Info-Wörterbuch ohne weitere Felder, kein XMP-Datenstrom (xdvipdfmx setzt Producer und CreationDate)."""
    from pypdf import PdfReader, PdfWriter
    rd = PdfReader(pdf)
    got = (rd.metadata or {}).get("/Title"), (rd.metadata or {}).get("/Author")
    if got != (title, AUTHOR): sys.exit(f"ABBRUCH: {pdf.name}: Titel/Autor im PDF {got} weichen ab von {(title, AUTHOR)}")
    wr = PdfWriter(clone_from=rd)
    wr.metadata = {"/Title": title, "/Author": AUTHOR}
    if "/Metadata" in wr._root_object: del wr._root_object["/Metadata"]
    tmp = pdf.with_name(pdf.name + ".tmp")
    with open(tmp, "wb") as fh: wr.write(fh)
    os.replace(tmp, pdf)
    keys = set((PdfReader(pdf).metadata or {}).keys())
    if keys != {"/Title", "/Author"}: sys.exit(f"ABBRUCH: {pdf.name}: Metadaten nach Bereinigung {sorted(keys)}")

def check_pdf(pdf, md, tex_src):
    """Abnahme-Prüfungen am fertigen PDF: pdfinfo, Modellkennungen im Text, Platzhalter, Pfade."""
    errs, notes = [], []
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
        fields = dict(l.split(":", 1) for l in info.splitlines() if ":" in l)
        extra = [k for k in ("Creator", "Producer", "CreationDate", "ModDate", "Subject", "Keywords", "Trapped") if k in fields]
        if extra: errs.append(f"pdfinfo zeigt weitere Metadaten: {extra}")
        if fields.get("Metadata Stream", "").strip() != "no": errs.append("pdfinfo: XMP-Datenstrom vorhanden")
        if fields.get("Title", "").strip() == "" or fields.get("Author", "").strip() != AUTHOR: errs.append("pdfinfo: Titel oder Autor fehlt")
    else:
        notes.append("pdfinfo nicht gefunden, Metadaten nur mit pypdf geprüft")
    if shutil.which("pdftotext"):
        txt = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        broken = [i for i in model_ids(md) if i not in txt]
        if broken: errs.append(f"Modellkennungen im PDF-Text nicht vollständig: {broken}")
        notes.append(f"Modellkennungen vollständig im PDF-Text: {len(model_ids(md)) - len(broken)}/{len(model_ids(md))}")
        raw = subprocess.run(["pdftotext", "-raw", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
        cut = split_names(raw) or split_names(txt)   # -raw zeigt die Zeilenenden, der Lesemodus führt Trennungen teils zusammen
        if cut: errs.append(f"Namen am Zeilenende getrennt ({len(cut)}x): {sorted(set(cut))}")
        notes.append(f"Namen ohne Trennung ({len(NO_HYPH)} geschützt): {len(cut)} getrennte Stellen")
        left = sorted(set(re.findall(r"\[\[[^\]]*\]\]", txt)))
        if left: errs.append(f"Platzhalter im PDF-Text: {left}")
        if "XXXXXXXX" in txt:
            (notes if not FINAL else errs).append("DOI-Platzhalter XXXXXXXX im PDF-Text" + (" (Probebau)" if not FINAL else ""))
        if re.search(r"/(Users|private|home)/|file://", txt): errs.append("lokaler Pfad im PDF-Text")
    else:
        errs.append("pdftotext nicht gefunden, Modellkennungen und Platzhalter nicht prüfbar")
    if re.search(r"/(Users|private|home)/|file://", tex_src): errs.append("lokaler Pfad in der .tex-Datei")
    return errs, notes

def build(lang):
    m = META[lang]; src = (R / f"REPORT_{lang.upper()}.md").read_text(encoding="utf-8").replace("[[DOI]]", DOI.split("zenodo.")[-1])
    left = sorted(set(re.findall(r"\[\[(?!FIG\d\]\])[^\]]*\]\]", src)))
    if left: sys.exit(f"ABBRUCH: REPORT_{lang.upper()}.md enthält offene Marken {left}")
    lines = src.splitlines()
    title = lines[0].lstrip("# ").strip(); subtitle = lines[2].lstrip("# ").strip()
    a = src.index(m["abs_h"]) + len(m["abs_h"]); b = src.index("\n---", a)
    abstract = src[a:b].strip(); body = src[b + 4:].strip()
    # Abschnitte: "### 1. Titel" -> "# Titel" (LaTeX nummeriert selbst)
    body = re.sub(r"^### \d+\.\s+", "# ", body, flags=re.M)
    body = re.sub(r"^#### ", "## ", body, flags=re.M)
    # Abbildungen an den Markern [[FIGn]], Nummer fest wie im Text; Abbildungsverzeichnis-Zeile entfällt
    body = re.sub(r"\n---\n+\*(Abbildungen|Figures):.*?\*\s*$", "\n", body, flags=re.S)
    def fig(mo):
        n = int(mo.group(1)); f, cap = FIG[lang][n]
        return ("```{=latex}\n\\begin{figure}[htbp]\\centering\\includegraphics[width=\\linewidth]{../figures/%s.png}\n"
                "\\caption*{\\textbf{%s %d:} %s}\\end{figure}\n```" % (f, m["figurename"], n, cap.replace("%", "\\%")))
    def esc(t):
        t = t.strip()
        for a, b in (("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#"), ("$", "\\$")):
            t = t.replace(a, b)
        t = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", t); t = re.sub(r"`([^`]+)`", r"\\texttt{\1}", t)
        return t
    def wrap(h, w=13):
        words, lines, cur = h.split(), [], ""
        for x in words:
            if cur and len(cur) + 1 + len(x) > w: lines.append(cur); cur = x
            else: cur = (cur + " " + x).strip()
        lines.append(cur); return "\\makecell[lb]{" + "\\\\".join(esc(l) for l in lines) + "}"
    def keep_last(c):
        """Schluss einer Beschriftung zusammenhalten (sonst „Be-/richt.“ allein in der Schlusszeile, 08.11.2026)."""
        # die letzten beiden Wörter zusammen und das letzte ungetrennt: Schlusszeile nie nur ein Wort
        return re.sub(r"(\S+)\s+(\S+)\s*$", lambda q: "%s~\\mbox{%s}" % (q.group(1), q.group(2)), c)
    def table(mo):
        num, cap, block = mo.group(2), mo.group(3), mo.group(4)
        rows = [[c for c in r.strip().strip("|").split("|")] for r in block.strip().splitlines()]
        head, body_rows = rows[0], [r for r in rows[2:]]
        ncol = len(head); maxlen = [max(len(r[i].strip()) for r in body_rows) for i in range(ncol)]
        short = [ml <= 20 for ml in maxlen]
        spec = "".join("l" if sh else ">{\\raggedright\\arraybackslash}X" for sh in short)
        if all(short): spec = "".join("l" for _ in short)
        size = "\\footnotesize\\setlength{\\tabcolsep}{4pt}" if ncol >= 6 else "\\small"
        # Tabelle 7 (Abweichungen vom Plan): drei Textspalten; mit \\small und gleich breiten Spalten zu hoch für die Seite
        # (xelatex: Float too large, letzte Zeile fehlte im PDF). Kleiner gesetzt, Spalten gewichtet (Summe = Zahl der X-Spalten).
        WEIGHTS = {'7': (1.0, 0.7, 1.3)}
        if num in WEIGHTS:
            w = WEIGHTS[num]
            if sum(1 for sh in short if not sh) != len(w) or abs(sum(w) - len(w)) > 1e-9: sys.exit(f"ABBRUCH: Spaltengewichte Tabelle {num} passen nicht")
            it = iter(w)
            spec = "".join("l" if sh else ">{\\raggedright\\arraybackslash\\hsize=%.1f\\hsize}X" % next(it) for sh in short)
            size = "\\footnotesize"
        hdr = " & ".join((wrap(h) if len(h.strip()) > 13 else "\\makecell[lb]{" + esc(h) + "}") if short[i] else esc(h) for i, h in enumerate(head))
        def keep(c):
            c = esc(c)
            c = re.sub(r"\([^()]{1,24}\)", lambda q: "\\mbox{%s}" % q.group(0), c)
            c = re.sub(r"[−-]?\d+(?:[.,]\d+)? (?:Pp|pp|%|\\%)", lambda q: "\\mbox{%s}" % q.group(0), c)
            return c
        lines = [" & ".join(("\\mbox{%s}" % esc(c)) if short[i] else keep(c) for i, c in enumerate(r)) + " \\\\" for r in body_rows]
        env = "tabularx}{\\linewidth" if not all(short) else "tabular"
        endenv = "tabularx" if not all(short) else "tabular"
        return ("```{=latex}\n\\begin{table}[htbp]\\centering%s\n\\caption*{\\normalsize\\textbf{%s %s:} %s}\n"
                "\\begin{%s}{%s}\\toprule\n%s \\\\\\midrule\n%s\n\\bottomrule\\end{%s}\\end{table}\n```"
                % (size, m["tablename"], num, keep_last(esc(cap)), env, spec, hdr, "\n".join(lines), endenv))
    body = re.sub(r"^\*(Tabelle|Table) (\d) · (.+?)\*\s*\n\s*\n((?:\|.*\n?)+)", table, body, flags=re.M)
    def tcap(mo):
        return "```{=latex}\n\\begin{center}\\small\\textbf{%s %s:} %s\\end{center}\\vspace{-6pt}\n```" % (m["tablename"], mo.group(2), mo.group(3).replace("%", "\\%"))
    body = re.sub(r"^\*(Tabelle|Table) (\d) · (.+?)\*$", tcap, body, flags=re.M)
    out = [re.sub(r"^\[\[FIG(\d)\]\]$", fig, body, flags=re.M)]
    body_tex = ties(protect_ids(tex("\n\n".join(out))))
    # Tabellen: Beschriftung "Tabelle N · ..." Absatz direkt vor der Tabelle bleibt als Text; Schrift kleiner
    body_tex = body_tex.replace("\\begin{longtable}", "{\\small\\begin{longtable}").replace("\\end{longtable}", "\\end{longtable}}")
    # Letzte zwei Wörter jedes Absatzes und Listenpunkts zusammen: Schlusszeile nie nur ein Wort („beschreibend.“)
    body_tex = last_two(body_tex)
    # Ligatur über die Wortfuge aufbrechen (auf|fiel); Repositoriums-Adresse nur an „/“ umbrechen
    body_tex = body_tex.replace("auffiel", "auf\\/fiel")
    body_tex = re.sub(r"(?<![{/])github\.com/marintkael/marin-research-tools",
                      lambda q: "github.com/\\allowbreak{}marintkael/\\allowbreak{}marin-\\allowbreak{}research-\\allowbreak{}tools", body_tex)
    # Absatz mit der Adresse großzügiger umbrechen (lange ungetrennte Teile, sonst zu breite Zeile)
    parts = re.split(r"(\n[ \t]*\n)", body_tex)
    parts = [x for x in parts]   # 08.11.2026 nachts: kein \\sloppy mehr (gab weit gesperrte Zeilen); Umbruch nach „/“ und „-“
    body_tex = "".join(parts)
    # Zitierhinweis im Flattersatz (sonst stark gesperrte Zeilen)
    body_tex, k = re.subn(r"(\\section\{(?:Zitierhinweis|How to cite)\}[^\n]*\n)", lambda q: q.group(1) + "{\\raggedright\n", body_tex)
    if k != 1: sys.exit("ABBRUCH: Zitierhinweis nicht eindeutig gefunden")
    body_tex = body_tex.rstrip() + "\n\\par}\n"
    # EN Seite 4: Der dreizeilige Absatz „Only the anchor days …“ darf nicht geteilt werden (keine einzelne Zeile oben/unten)
    # und ließ unten 2,5 Zeilen frei. Eine Zeile mehr Satzspiegel auf dieser Seite holt ihn ganz herauf (08.11.2026).
    if m["out"].endswith("_EN"):
        body_tex, k = re.subn(r"(\n)(Only the anchor days of the three-day grid)", lambda q: q.group(1) + "\\enlargethispage{\\baselineskip}" + q.group(2), body_tex)
        if k != 1: sys.exit("ABBRUCH: Anker „Only the anchor days“ nicht gefunden")
    # Überschrift nie allein oder mit nur wenigen Zeilen am Seitenende: vor jeder Überschrift Platz für 6 Zeilen verlangen
    body_tex = re.sub(r"\\(?:sub)*section\*?\{", lambda q: "\\Needspace{6\\baselineskip}" + q.group(0), body_tex)
    # Tabelle 7 ist fast seitenhoch und passt nicht unter den Text von Abschnitt 8. Mit der Float-Sperre vor Abschnitt 9
    # bliebe die Seite mit Abschnitt 8 zu zwei Dritteln leer. Vor „Grenzen“ und „Reproduzierbarkeit“ (EN entsprechend) deshalb
    # ohne Sperre: der Text läuft weiter, Tabelle 7 steht auf der Folgeseite.
    body_tex, k = re.subn(r"(\\Needspace\{6\\baselineskip\}\\section\{(?:Grenzen|Limitations|Reproduzierbarkeit|Reproducibility)\})",
                          lambda q: "\\let\\FBsave\\FloatBarrier\\let\\FloatBarrier\\relax" + q.group(1) + "\\let\\FloatBarrier\\FBsave{}", body_tex)
    if k != 2: sys.exit("ABBRUCH: Abschnitte Grenzen/Reproduzierbarkeit nicht eindeutig gefunden")
    t = (P / "template.tex").read_text(encoding="utf-8")
    if "\\hyphenation{$nohyph$}" not in t: sys.exit("ABBRUCH: template.tex ohne \\hyphenation{$nohyph$} (Namen ohne Trennung)")
    for k, v in dict(m, nohyph=" ".join(NO_HYPH), title=title, subtitle=ties(subtitle), abstract=last_two(ties(protect_ids(tex(abstract)))), body=body_tex, doi=DOI).items():
        t = t.replace(f"${k}$", v)
    texf = P / f"{m['out']}.tex"; texf.write_text(t, encoding="utf-8")
    for _ in range(2):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", texf.name], cwd=P, capture_output=True, text=True)
        if r.returncode: print(r.stdout[-2500:]); sys.exit(1)
    log = (P / f"{m['out']}.log").read_text(errors="ignore")
    if "Float too large" in log: sys.exit(f"ABBRUCH: {m['out']}: Gleitobjekt zu groß für die Seite (Float too large), Inhalt würde abgeschnitten")
    miss = re.findall(r"Missing character: There is no (.) ", log)
    over = [float(x) for x in re.findall(r"Overfull \\hbox \(([\d.]+)pt too wide\)", log)]
    for ext in (".aux", ".log", ".out"): (P / f"{m['out']}{ext}").unlink(missing_ok=True)   # Hilfsdateien tragen lokale Pfade
    pdf = P / f"{m['out']}.pdf"
    clean_metadata(pdf, title)
    errs, notes = check_pdf(pdf, src, t)
    print(lang, "ok" if not errs else "FEHLER", "| fehlende Glyphen:", sorted(set(miss)),
          "| zu breite Zeilen:", f"{len(over)} (max. {max(over):.1f} pt)" if over else 0,
          "| DOI:", DOI if FINAL else "Platzhalter (Probe)", "|", "; ".join(notes))
    if errs: sys.exit("ABBRUCH " + lang + ": " + "; ".join(errs))

for l in LANGS: build(l)
