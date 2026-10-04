# Validation Report Q3 / 2026 · Validierungsbericht Q3 / 2026

DOI: [10.5281/zenodo.23145378](https://doi.org/10.5281/zenodo.23145378) (two standalone papers, DE and EN)

- English: https://marin-t-kael.de/en/research/reports/q3-2026-validation
- Deutsch: https://marin-t-kael.de/research/berichte/q3-2026-validierung
- Pre-registration Q0-INST: [10.5281/zenodo.20125967](https://doi.org/10.5281/zenodo.20125967) · sub-studies Q0-KG to Q6: [`pre_registrations/`](../../pre_registrations)

## English

**What this is.** Analysis code, figure builds, paper build and frozen results for the Q3 / 2026 validation report of the
Marin T. Kael research programme. The report tests the six instrument hypotheses of pre-registration Q0-INST against the
frozen data state of 1 October 2026 (window 11 May to 30 September 2026). None is confirmed: three cannot be tested
because the planned data collection did not take place, three are not confirmed.

Headline numbers (all from `data/results.json`): next-day score agreement 86.6 % (OpenAI Search), 87.1 % (Gemini),
94.3 % (Claude, claude.ai with web search); Cronbach's α 0.407 to 0.61 across 16 questions; five downward CUSUM alarms
under the rebasing variant, none explained by a documented event; the Wikidata items registered as anchors were deleted
during the window; the Google Knowledge Graph finds the author on 140 of 141 days and the book on none of 139.

**Contents**

| Path | Purpose |
|---|---|
| `data/results.json` | single source of every number in text, tables and figures |
| `data/event_codes.json` | gap-register entries 1 to 25, coded by level effect (used for the alarm check) |
| `data/wikidata_snapshots.json`, `data/kg_snapshots.json` | daily anchor-surface snapshots (Wikidata, Google Knowledge Graph) |
| `data/bing_daily.json`, `data/gsc_daily.json` | daily aggregates of the Bing index query and Search Console |
| `data/preregs.json` | header fields and SHA-256 of the pre-registration files Q0-Q6 as frozen on 4 October 2026 |
| `data/freeze.json` | freeze time and row counts of the raw extract of 1 October 2026 |
| `build/fetch.py` | pulls the raw rows from the measurement database (credentials from the environment) |
| `build/fetch_preregs.py` | freezes the pre-registration files of this repository |
| `build/analyze.py` | raw rows to `data/results.json` |
| `build/figures.py`, `build/figstyle.py` | Figures 1 to 5, DE and EN, PNG and SVG |
| `build/build_site_pages.py` | report pages (also holds the figure captions used by the paper build) |
| `paper/build_paper.py`, `paper/template.tex` | Markdown to LaTeX paper (pandoc + xelatex), DE and EN |
| `REPORT_DE.md`, `REPORT_EN.md` | report text as published |
| `figures/` | figures as published |

**Reproduce.** The figures and both papers rebuild from the files in this folder:

```bash
python3 build/figures.py        # figures/fig1..5_{de,en}.png/.svg from data/
python3 paper/build_paper.py    # paper/*.pdf (needs pandoc and xelatex)
```

`analyze.py` additionally needs the raw answer rows (`web_rows.json`, `claude_web_rows.json`, `runs.json`,
`data_gaps.json`, `freeze_extra.json`). They are not in this folder: they carry internal run identifiers and query
metadata of the measurement setup. The frozen extract of 1 and 4 October 2026 will be released through the
Hugging Face dataset [marintkael/ai-citation-fidelity](https://huggingface.co/datasets/marintkael/ai-citation-fidelity)
as part of the replication archive announced in Section 11 of the report. Until then `results.json` is the reference.

Requires Python 3.10 or later with matplotlib and numpy; figure titles use the Newsreader font if
`figures/_fonts/newsreader-latin.ttf` is present and fall back to a serif otherwise.

## Deutsch

**Was das ist.** Auswertungscode, Figurenbau, Paper-Bau und eingefrorene Ergebnisse des Validierungsberichts Q3 / 2026
des Forschungsprogramms Marin T. Kael. Der Bericht prüft die sechs Instrument-Hypothesen der Vorregistrierung Q0-INST
gegen den Datenstand vom 1. Oktober 2026 (Fenster 11. Mai bis 30. September 2026). Keine ist bestätigt: drei sind nicht
prüfbar, weil die vorgesehenen Erhebungen nicht stattgefunden haben, drei sind nicht bestätigt.

Kernzahlen (alle aus `data/results.json`): Übereinstimmung am Folgetag 86,6 % (OpenAI Search), 87,1 % (Gemini),
94,3 % (Claude, claude.ai mit Websuche); Cronbachs α 0,407 bis 0,61 über 16 Fragen; fünf Abwärts-Alarme der
CUSUM-Karte mit Neubezug, keiner durch ein dokumentiertes Ereignis erklärt; die als Anker registrierten Wikidata-Items
wurden im Fenster gelöscht; der Google Knowledge Graph findet den Autor an 140 von 141 Tagen, das Buch an keinem von 139.

**Nachbauen.** Abbildungen und beide Paper lassen sich aus diesem Ordner neu erzeugen (Befehle oben).
`analyze.py` braucht zusätzlich die Antwortzeilen der Messdatenbank. Sie liegen nicht hier, weil sie interne
Lauf-Kennungen und Abfrage-Metadaten der Messumgebung enthalten. Der eingefrorene Abzug vom 1. und 4. Oktober 2026
erscheint mit dem Replikationsarchiv (Abschnitt 11 des Berichts) über den Hugging-Face-Datensatz
[marintkael/ai-citation-fidelity](https://huggingface.co/datasets/marintkael/ai-citation-fidelity). Bis dahin ist
`results.json` die Referenz.

`build/fetch.py` liest Zugangsdaten und Kennungen der Datenbank aus Umgebungsvariablen
(`MEASUREMENT_DB_API_TOKEN`, `MEASUREMENT_DB_ACCOUNT_ID`, `MEASUREMENT_DB_ID`); im Code steht keine davon.

## Citation · Zitierhinweis

Kael, M. T. (2026). *Validation Report Q3 / 2026: A test of the instrument hypotheses of pre-registration Q0-INST,
measurement window 11 May to 30 September 2026.* Marin T. Kael Research Programme. https://doi.org/10.5281/zenodo.23145378

Kael, M. T. (2026). *Validierungsbericht Q3 / 2026: Prüfung der Instrument-Hypothesen der Vorregistrierung Q0-INST,
Messfenster 11. Mai bis 30. September 2026.* Marin T. Kael Research Programme. https://doi.org/10.5281/zenodo.23145378

Code: MIT (see repository `LICENSE`). Data and figures: CC BY 4.0.
