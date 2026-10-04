#!/usr/bin/env python3
"""Validierungsbericht Q3/2026 als Paper im Programm-Standard (Layout wie „Zero to Cited“, Zenodo 20549021):
article 11pt, Letter, 1 in, Latin Modern, zentrierter Titelblock, Abstract, nummerierte Abschnitte.
Zwei eigenständige Fassungen DE und EN aus REPORT_DE.md / REPORT_EN.md. Abbildungen = figures/*.png."""
import re, subprocess, sys, json
from pathlib import Path
R = Path(__file__).resolve().parent.parent; P = R / "paper"
import importlib.util as _u
_sp=_u.spec_from_file_location("sp", str(R / "build" / "build_site_pages.py"))
def _figs():
    src=(R / "build" / "build_site_pages.py").read_text(encoding="utf-8"); i=src.index("FIGS = {"); j=src.index("}}", i)+2
    return eval(src[i+7:j])
FIG = {l: {k: (v[0], re.sub(r"^(Abb\.|Fig\.) \d · ", "", v[1])) for k, v in d.items()} for l, d in _figs().items()}
META = {"de": dict(lang="german", tablename="Tabelle", figurename="Abbildung", datestr="Oktober 2026",
                   affiliation="Unabhängiger Forscher -- KI-Zitations-Feldlabor", abs_h="### Zusammenfassung",
                   ref=r"(Abbildung|Abb\.) (\d)", out="Validierungsbericht-Q3-2026_DE"),
        "en": dict(lang="english", tablename="Table", figurename="Figure", datestr="October 2026",
                   affiliation="Independent researcher -- AI Citation Field Lab", abs_h="### Summary",
                   ref=r"(Figure|Fig\.) (\d)", out="Validation-Report-Q3-2026_EN")}

def tex(md, extra=()):
    return subprocess.run(["pandoc", "-f", "markdown-auto_identifiers", "-t", "latex", "--wrap=preserve", *extra],
                          input=md, capture_output=True, text=True, check=True).stdout

def build(lang):
    m = META[lang]; src = (R / f"REPORT_{lang.upper()}.md").read_text(encoding="utf-8")
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
    def table(mo):
        num, cap, block = mo.group(2), mo.group(3), mo.group(4)
        rows = [[c for c in r.strip().strip("|").split("|")] for r in block.strip().splitlines()]
        head, body_rows = rows[0], [r for r in rows[2:]]
        ncol = len(head); maxlen = [max(len(r[i].strip()) for r in body_rows) for i in range(ncol)]
        short = [ml <= 20 for ml in maxlen]
        spec = "".join("l" if sh else ">{\\raggedright\\arraybackslash}X" for sh in short)
        if all(short): spec = "".join("l" for _ in short)
        size = "\\footnotesize\\setlength{\\tabcolsep}{4pt}" if ncol >= 6 else "\\small"
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
                % (size, m["tablename"], num, esc(cap), env, spec, hdr, "\n".join(lines), endenv))
    body = re.sub(r"^\*(Tabelle|Table) (\d) · (.+?)\*\s*\n\s*\n((?:\|.*\n?)+)", table, body, flags=re.M)
    def tcap(mo):
        return "```{=latex}\n\\begin{center}\\small\\textbf{%s %s:} %s\\end{center}\\vspace{-6pt}\n```" % (m["tablename"], mo.group(2), mo.group(3).replace("%", "\\%"))
    body = re.sub(r"^\*(Tabelle|Table) (\d) · (.+?)\*$", tcap, body, flags=re.M)
    out = [re.sub(r"^\[\[FIG(\d)\]\]$", fig, body, flags=re.M)]
    body_tex = tex("\n\n".join(out))
    # Tabellen: Beschriftung "Tabelle N · ..." Absatz direkt vor der Tabelle bleibt als Text; Schrift kleiner
    body_tex = body_tex.replace("\\begin{longtable}", "{\\small\\begin{longtable}").replace("\\end{longtable}", "\\end{longtable}}")
    t = (P / "template.tex").read_text(encoding="utf-8")
    for k, v in dict(m, title=title, subtitle=subtitle, abstract=tex(abstract), body=body_tex).items():
        t = t.replace(f"${k}$", v)
    texf = P / f"{m['out']}.tex"; texf.write_text(t, encoding="utf-8")
    for _ in range(2):
        r = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", texf.name], cwd=P, capture_output=True, text=True)
        if r.returncode: print(r.stdout[-2500:]); sys.exit(1)
    miss = re.findall(r"Missing character: There is no (.) ", (P / f"{m['out']}.log").read_text(errors="ignore"))
    print(lang, "ok", "fehlende Glyphen:", sorted(set(miss)))

for l in sys.argv[1:] or ["de", "en"]: build(l)
