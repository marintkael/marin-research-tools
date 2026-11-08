# Report 04 · Book Launch and AI Citation · Bericht 04 · Buchstart und KI-Zitation

DOI: [10.5281/zenodo.24063460](https://doi.org/10.5281/zenodo.24063460) (two standalone papers, DE and EN)

- English: https://marin-t-kael.de/en/research/reports/04-book-launch-ai-citation
- Deutsch: https://marin-t-kael.de/research/berichte/04-buchstart-ki-zitation
- Pre-registration Q7 (version 1.4 of 15 October 2026, with dated notes of 8 November 2026): [`pre_registrations/Q7_book_release.yaml`](../../pre_registrations/Q7_book_release.yaml)
- Data set: [huggingface.co/datasets/marintkael/ai-citation-fidelity](https://huggingface.co/datasets/marintkael/ai-citation-fidelity)

## English

**What this is.** Analysis code, frozen data pulls, figure builds, paper build and results for Report 04 of the
Marin T. Kael research programme. The report tests the pre-registered hypothesis that the retail availability of the
first volume on 8 October 2026 changes how AI answer engines with web search cite the author, earlier in the Direct
channel than in the Recommendation channel. Primary panel: OpenAI with web search and Gemini with Google web search on
the anchor days of the three-day grid; baseline 8 September to 7 October, effect window 8 October to 7 November 2026.

Headline numbers (all from `data/results.json`): drift-adjusted difference of the headline +1.38 percentage points
(95 % bootstrap interval −3.59 to 6.68); the null hypothesis is not rejected and the order hypothesis receives no
support. Unadjusted +3.38 (0.05 to 6.93); whether this interval excludes zero depends on the random seed
(`data/results_startwerte.json`). The non-pre-registered extension to anchor day 8 November gives +2.32 (−2.74 to 7.95);
the decision rests on the pre-registered main analysis alone. The delayed-effect observation runs until 6 January 2027.

**Contents**

| Path | Purpose |
|---|---|
| `data/baseline_freeze/` | frozen baseline pull, cut-off 2026-10-07 23:59:59 UTC (incl. dated corrections and supplements) |
| `data/effect_freeze/` | frozen pull at the end of the effect window, cut-off 2026-11-07 23:59:59 UTC |
| `data/extension_freeze_0811/` | pull for the non-pre-registered extension, cut-off 2026-11-08 23:59:59 UTC |
| `data/current/` | running pull of 5 November 2026 (contributes no rows to the analysed windows) |
| `data/results.json` | main analysis: single source of every number in text, tables and figures |
| `data/results_*.json` | sensitivity analyses (scoring rules of 2 November, empty answers, without amendment 4), extension, seed check |
| `data/scorer_nachtrag_2026-11-02.json`, `data/leere_antworten.json` | dated rescoring entries and empty answers per day |
| `build/fetch.py`, `build/freeze_baseline.py` | pull and freeze raw rows from the measurement database (credentials from the environment) |
| `build/analyze.py` | frozen pulls to `data/results.json`; flags for each sensitivity run and the extension |
| `build/startwert_pruefung.py` | additional seed check of the headline bootstrap interval (not pre-registered) |
| `build/figures.py`, `build/figmeta.py`, `build/figstyle.py` | Figures 1 to 5, DE and EN, PNG and SVG |
| `build/fill_texts.py` | fills every number in the report text from the result files |
| `build/build_site_pages.py` | report pages for the website |
| `build/hf_build.py` | Hugging Face data set build and diff against the published state |
| `paper/build_paper.py`, `paper/template.tex` | Markdown to LaTeX paper (pandoc + xelatex), DE and EN, with the PDFs as published |
| `REPORT_DE.md`, `REPORT_EN.md` | report text as published |
| `figures/` | figures as published |

**Reproduce.** `python3 build/analyze.py` reads only the frozen folders and rewrites `data/results.json` and the
variant files (numpy; about four minutes). Figures need matplotlib and the Newsreader font (SIL Open Font License),
the paper needs pandoc and xelatex. The bootstrap uses the fixed seed 20261007.

## Deutsch

**Was das ist.** Auswertungscode, eingefrorene Abzüge, Abbildungs- und Paper-Bau sowie Ergebnisse von Bericht 04 des
Marin T. Kael Forschungsprogramms. Der Bericht prüft die vorregistrierte Hypothese, dass die Handelsverfügbarkeit des
ersten Bandes am 8. Oktober 2026 die Zitation des Autors durch KI-Antwortmaschinen mit Websuche verändert, im
Direkt-Kanal früher als im Empfehlungs-Kanal. Driftbereinigt beträgt die Differenz der Kopfzahl +1,38 Prozentpunkte
(95-%-Intervall −3,59 bis 6,68); die Nullhypothese wird nicht verworfen, die Reihenfolge-Hypothese erhält keine Stütze.
Die nicht vorregistrierte Erweiterung bis zum Ankertag 8. November ergibt +2,32 (−2,74 bis 7,95). Die Beobachtung
verzögerter Wirkung läuft bis zum 6. Januar 2027 und wird als Nachtrag berichtet. Inhalt und Nachbau wie oben.

Code: MIT (see repository `LICENSE`). Data, figures and texts: CC BY 4.0. Author: Marin T. Kael (ORCID 0009-0006-2105-8190).
