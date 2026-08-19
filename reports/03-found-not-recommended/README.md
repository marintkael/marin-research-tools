# Report 03 · Found, not recommended (2026-08-19)

Reproducible analysis and figures for **Report 03** of the Marin T. Kael research programme
(*Gefunden, nicht empfohlen / Found, not recommended*, measurement days T+2 to T+100, 13 May – 19 August 2026).

- Report (DE/EN): https://marin-t-kael.de/research (publication pending; DOI follows)
- Raw data (frozen extract 2026-08-19, Parquet): https://huggingface.co/datasets/marintkael/ai-citation-fidelity
  · `default` all scored pipeline answers (24,882 rows incl. no-web control models)
  · `claude_web` Claude web-search measurement (3,279 rows)
  · `questions` · `data_gaps` · `daily_channels`
- Live measurement: https://marin-t-kael.de/research/dashboard · JSON https://marin-research-pipeline.p96xckbr4c.workers.dev/api/latest

## Reproduce

```bash
# 1) fetch the frozen raw rows into data/ (from the HF dataset) — or use the results.json included here
python3 - <<'PY'
from datasets import load_dataset; import json
ds=load_dataset("marintkael/ai-citation-fidelity","default")["train"].to_pandas()
prim=ds[ds.llm.isin(["openai_search","gemini"]) & (ds.status!="error")]
prim=prim.assign(d=prim.asked_at.str[:10])[["d","llm","category","question_id","score","status"]]
json.dump(prim.to_dict("records"),open("data/primary_rows.json","w"))
cw=load_dataset("marintkael/ai-citation-fidelity","claude_web")["train"].to_pandas()
cw=cw.assign(d=cw.asked_at.str[:10])[["d","llm","category","question_id","score","status"]].rename(columns={"llm":"model"})
json.dump(cw.to_dict("records"),open("data/claude_rows.json","w"))
nw=ds[~ds.llm.isin(["openai_search","gemini","openai_search_full","openai_search_legacy","openai_gpt52_web","openai_gpt54_web"]) & (ds.status!="error")].copy()
nw["marin_in_answer"]=nw.answer_excerpt.fillna("").str.contains("Kael|vierte Feld|Varin").astype(int)
nw=nw.assign(d=nw.asked_at.str[:10])[["d","llm","category","score","status","marin_in_answer"]]
json.dump(nw.to_dict("records"),open("data/noweb_rows.json","w"))
PY
# 2) analysis -> data/results.json ; 3) figures ; 4) typeset HTML
python3 build/analyze.py && python3 build/fig1_channels.py && python3 build/fig2to5.py && python3 build/build_html.py
```

`data/results.json` (included) is the single source for every number in the report's text, tables and figures.
Requires Python ≥3.10 with matplotlib, scipy, numpy, pandas, pyarrow, fontTools; figure titles use the Newsreader
font (`figures/_fonts/`, converted from the site's woff2) and fall back to a serif if absent.
