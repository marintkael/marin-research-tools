import re,html,base64,shutil,glob,os
from pathlib import Path
R=Path(__file__).resolve().parent.parent
D=Path(os.environ.get("REPORT03_OUT_DIR", str(R / "out")))
CSS=open(R/"build"/"report.css",encoding="utf-8").read()
FIGS={"de":{1:("fig1_channels_de","Abb. 1 · Drei Frage-Kanäle über 99 Messtage. Rot: Direkt-Kanal mit logistischer Anpassung (Obergrenze 72,5 %, Wendepunkt T+37). Blau: Saga-Wissen. Grau: Empfehlung. Schattierung: dokumentierte Datenlücken."),2:("fig2_phases_de","Abb. 2 · Zitationsrate je Kanal und Phase, gepoolt über drei Anbieter; Konfidenzintervalle in Tabelle 1."),3:("fig3_providers_de","Abb. 3 · Direkt-Kanal je Anbieter, Wochenmittel; graues Band = Spannweite zwischen den Anbietern in derselben Woche."),4:("fig4_discovery_de","Abb. 4 · Empfehlungen nach Frage. 40 Nennungen in 6.729 Antworten ohne Nennung des Autors; 25 davon auf die Frage nach dem Sub-Genre „Edikt-Fantasy“."),5:("fig5_echo_de","Abb. 5 · Kontrollkanal. Zehn Modelle ohne Web-Zugriff, 6.416 Antworten ohne Nennung des Autors, keine ungefragte Nennung.")},
      "en":{1:("fig1_channels_en","Fig. 1 · Three question channels across 99 measurement days. Red: Direct channel with logistic fit (ceiling 72.5 %, inflection T+37). Blue: Saga knowledge. Grey: Recommendation. Shading: documented data gaps."),2:("fig2_phases_en","Fig. 2 · Citation rate per channel and phase, pooled across three providers; confidence intervals in Table 1."),3:("fig3_providers_en","Fig. 3 · Direct channel by provider, weekly mean; grey band = spread between providers in the same week."),4:("fig4_discovery_en","Fig. 4 · Recommendations by question. 40 mentions in 6,729 answers that do not name the author; 25 of them on the question about the sub-genre “edict fantasy”."),5:("fig5_echo_en","Fig. 5 · Control channel. Ten models without web access, 6,416 answers that do not name the author, no unprompted mention.")}}

DOI_EXTRA={"10.5281/zenodo.20125967":"Vorregistrierung","10.5281/zenodo.20171439":"Codebuch"}
def linkify(raw,lang):
    """Alle Verweisklassen klickbar: Abbildung/Tabelle/Abschnitt (Anker), DOI (doi.org), Domains (https), Dokumente (Zenodo)."""
    p=html.escape(raw)
    ext="target='_blank' rel='noopener'"
    # Abbildungen / Tabellen
    p=re.sub(r"(Abbildung|Figure) (\d)",lambda m:f"<a class='xref' href='#fig{m.group(2)}'>{m.group(1)} {m.group(2)}</a>",p)
    p=re.sub(r"(Tabelle|Table) (\d)",lambda m:f"<a class='xref' href='#tab{m.group(2)}'>{m.group(1)} {m.group(2)}</a>",p)
    # Abschnitte: "Abschnitt 6", "Abschnitte 3 bis 5", "Section 6", "Sections 3 to 5"
    p=re.sub(r"(Abschnitte|Sections) (\d+) (bis|to) (\d+)",lambda m:f"<a class='xref' href='#sec{m.group(2)}'>{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}</a>",p)
    p=re.sub(r"(Abschnitt|Section) (\d+)",lambda m:f"<a class='xref' href='#sec{m.group(2)}'>{m.group(1)} {m.group(2)}</a>",p)
    # DOIs (mit oder ohne 'DOI '/'doi:' davor)
    p=re.sub(r"(10\.5281/zenodo\.\d+)",lambda m:f"<a class='ext' href='https://doi.org/{m.group(1)}' {ext}>{m.group(1)}</a>",p)
    # Domains / Pfade
    p=re.sub(r"(?<![\w/])(marin-t-kael\.de/research/dashboard|marin-t-kael\.de/research|github\.com/marintkael/marin-research-tools)(?![\w/-])",lambda m:f"<a class='ext' href='https://{m.group(1)}' {ext}>{m.group(1)}</a>",p)
    # Dokumente ohne DOI im Satz: Vorregistrierung / Pre-registration -> Zenodo
    p=re.sub(r"(Vorregistrierung vom 11\. Mai|pre-registration of 11 May)",lambda m:f"<a class='ext' href='https://doi.org/10.5281/zenodo.20125967' {ext}>{m.group(1)}</a>",p)
    p=re.sub(r"„Zero to Cited in Six Days“|“Zero to Cited in Six Days”",lambda m:f"<a class='ext' href='https://doi.org/10.5281/zenodo.20549021' {ext}>{m.group(0)}</a>",p)
    # Dashboard-Nennung ohne Pfad
    return p

def cell(c):
    c=c.strip()
    m=re.match(r"^(−?-?[\d.,]+ %) \((.+)\)$",c) or re.match(r"^(−?-?[\d.,]+ %) · (.+)$",c)
    if m: return f"<span class='v'>{html.escape(m.group(1))}</span><span class='s'>{html.escape(m.group(2))}</span>"
    return html.escape(c)
def md2html(md,lang,embed):
    F=FIGS[lang]; placed=set(); out=[]; rows=[]
    def src(name):
        return ("data:image/png;base64,"+base64.b64encode((R/"figures"/f"{name}.png").read_bytes()).decode()) if embed else f"figures/{name}.png"
    def flush():
        nonlocal rows
        if not rows: return
        hdr=rows[0]; body=rows[2:] if len(rows)>1 and set(rows[1].replace("|","").strip())<=set("-: ") else rows[1:]
        h="<div class='tablewrap'><table><thead><tr>"+"".join(f"<th>{html.escape(c.strip())}</th>" for c in hdr.strip("|").split("|"))+"</tr></thead><tbody>"
        for r in body:
            cells=r.strip("|").split("|"); h+="<tr>"+f"<td>{html.escape(cells[0].strip())}</td>"+"".join(f"<td>{cell(c)}</td>" for c in cells[1:])+"</tr>"
        out.append(h+"</tbody></table></div>"); rows=[]
    for line in md.splitlines():
        if line.startswith("|"): rows.append(line); continue
        if rows: flush()
        s=line.strip()
        if not s: continue
        if s=="---": out.append("<hr/>"); continue
        if s.startswith("# "): out.append(f"<h1>{html.escape(s[2:])}</h1>"); continue
        if s.startswith("## "): out.append(f"<p class='deck'>{html.escape(s[3:])}</p>"); continue
        if s.startswith("### "):
            mh=re.match(r"(\d+)\.",s[4:]); hid=f" id='sec{mh.group(1)}'" if mh else ""
            out.append(f"<h2{hid}>{html.escape(s[4:])}</h2>"); continue
        if s.startswith("*") and s.endswith("*"):
            mt=re.match(r"\*(Tabelle|Table) (\d)",s)
            tid=f" id='tab{mt.group(2)}'" if mt else ""
            out.append(f"<p class='meta tabcap'{tid}>{linkify(s.strip('*'),lang)}</p>"); continue
        m=re.fullmatch(r"\[\[FIG(\d)\]\]",s)
        if m:
            n=int(m.group(1)); name,cap=F[n]; out.append(f"<figure id='fig{n}'><img src='{src(name)}' alt='{html.escape(cap)}'/><figcaption>{html.escape(cap)}</figcaption></figure>"); continue
        out.append(f"<p>{linkify(s,lang)}</p>")
    if rows: flush()
    return "\n".join(out)
for lang,fn,label,title,full in (("de","REPORT_DE.md","Forschungsbericht 03 · Entwurf zur Freigabe","Gefunden, nicht empfohlen","Bericht-03_Gefunden-nicht-empfohlen_DE_vollstaendig.html"),("en","REPORT_EN.md","Research Report 03 · draft for approval","Found, not recommended","Bericht-03_Found-not-recommended_EN_vollstaendig.html")):
    md=(R/fn).read_text(encoding="utf-8")
    for embed,outname in ((False,f"report_{lang}.html"),(True,full)):
        doc=f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{title}</title>{CSS}</head><body><div class='wrap'><div class='badge'>{label}</div>{md2html(md,lang,embed)}</div></body></html>"
        (R/outname).write_text(doc,encoding="utf-8"); (D/outname).write_text(doc,encoding="utf-8")
for f in glob.glob(str(R/"figures"/"fig*")): shutil.copy2(f,D/"figures")
for f in glob.glob(str(R/"build"/"*.py"))+glob.glob(str(R/"build"/"*.css")): shutil.copy2(f,D/"build")
print("HTML (4 Dateien) + Figuren + Build nach REPORT03_OUT_DIR kopiert")
