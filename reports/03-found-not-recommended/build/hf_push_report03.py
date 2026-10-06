#!/usr/bin/env python3
"""HF-Dataset marintkael/ai-citation-fidelity auf den Stand von Bericht 03 (2026-08-19) bringen.
Dateien: data/citation_fidelity.parquet (alle ai_citation_results inkl. Kontrollkanal, wie bisher, jetzt bis 19.08.)
         data/claude_web.parquet (Claude-Websuche-Messung, 3 Tiers)
         data/questions.parquet · data/data_gaps.parquet · data/daily_channels.parquet (aus results.json)
Aufruf: venv/bin/python3 hf_push_report03.py [--dry]"""
import json, io, os, re, sys, urllib.request
from pathlib import Path
import pandas as pd
ROOT=Path(os.environ.get('MARIN_ENV_DIR', '.')); ENV=(ROOT/'.env').read_text()
env=lambda k:(re.search(rf'^{k}=(.*)$',ENV,re.M) or [None,None])[1].strip().strip('"\'') if re.search(rf'^{k}=(.*)$',ENV,re.M) else None
CF=env('CLOUDFLARE_API_TOKEN_FULL'); HF=env('HF_TOKEN'); ACC=env('MEASUREMENT_DB_ACCOUNT_ID'); DB=env('MEASUREMENT_DB_ID')
REPO='marintkael/ai-citation-fidelity'; R=Path(__file__).resolve().parent.parent; DRY='--dry' in sys.argv
def d1(sql):
    req=urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{ACC}/d1/database/{DB}/query',data=json.dumps({'sql':sql}).encode(),headers={'Authorization':f'Bearer {CF}','Content-Type':'application/json'},method='POST')
    return json.load(urllib.request.urlopen(req,timeout=60))['result'][0]['results']
def pull(sql_base,order):
    rows,off=[],0
    while True:
        b=d1(f"{sql_base} ORDER BY {order} LIMIT 2000 OFFSET {off}"); rows+=b
        if len(b)<2000: break
        off+=2000
    return rows
print('1. ai_citation_results …'); res=pull("SELECT run_id, asked_at, llm, question_id, question, category, score, status, answer_excerpt FROM ai_citation_results","asked_at, llm, question_id")
df=pd.DataFrame(res); df['score']=pd.to_numeric(df['score'],errors='coerce'); print('   ',len(df),'Zeilen',df['asked_at'].min(),'→',df['asked_at'].max())
print('2. claude_web_results …'); cw=pull("SELECT s.run_ts AS asked_at, r.model AS llm, r.question_id, r.question, r.category, r.score, r.status, substr(r.answer,1,500) AS answer_excerpt, r.has_web_search FROM claude_web_results r JOIN claude_web_snapshots s ON s.id=r.snapshot_id","s.run_ts, r.model, r.question_id")
dcw=pd.DataFrame(cw); dcw['score']=pd.to_numeric(dcw['score'],errors='coerce'); print('   ',len(dcw),'Zeilen',dcw['asked_at'].min(),'→',dcw['asked_at'].max())
print('3. questions / data_gaps / daily_channels …')
q=pd.DataFrame(json.load(open(R/'data/questions.json')))[['question_id','category','q']].rename(columns={'q':'question'})
ch={'Direct':'direct','Research':'research','LongTail':'longtail','Genre':'recommendation','CompCluster':'recommendation','GenreRecommend':'recommendation'}
q['channel']=q['category'].map(ch)
g=pd.DataFrame(json.load(open(R/'data/data_gaps.json')))
res_json=json.load(open(R/'data/results.json')); daily=res_json['daily']; dn=res_json['daily_n']
dc=pd.DataFrame([{'date':d,'channel':c,'citation_rate_pct':v,'n_answers':dn[d][c]} for d,row in daily.items() for c,v in row.items()])
print('   questions',len(q),'| gaps',len(g),'| daily_channels',len(dc))
card=f'''---
license: cc-by-4.0
language: [en, de]
pretty_name: "AI Citation Fidelity, Marin T. Kael Research Programme"
size_categories: [10K<n<100K]
task_categories: [text-classification]
tags: [ai-citation, llm-evaluation, hallucination, retrieval-grounding, geo, answer-engine-optimization, knowledge-graph, single-subject, pre-registered, longitudinal]
configs:
  - config_name: default
    data_files: "data/citation_fidelity.parquet"
  - config_name: claude_web
    data_files: "data/claude_web.parquet"
  - config_name: questions
    data_files: "data/questions.parquet"
  - config_name: data_gaps
    data_files: "data/data_gaps.parquet"
  - config_name: daily_channels
    data_files: "data/daily_channels.parquet"
---

# AI Citation Fidelity, Marin T. Kael Research Programme

Daily-scored measurements of whether web-grounded LLMs **find, correctly cite, or hallucinate** a single, brand-new author entity ("Marin T. Kael"), from the day the entity went online (2026-05-11). Pre-registered, n = 1, fixed catalogue of 16 questions, frozen since June 2026.

**Current release: Report 03 extract, 2026-08-19 (T+2 to T+100).** Previous release (2026-06-15) covered T+2 to T+23.

- **Report 03 "Found, not recommended" (2026-08-19):** https://marin-t-kael.de/research  (publication pending; DOI follows)
- **Report 02 "Zero to Cited in Six Days" (DOI):** https://doi.org/10.5281/zenodo.20549021
- **Methodology Note 01 v4.0 (DOI):** https://doi.org/10.5281/zenodo.20364173
- **Pre-registration (DOI):** https://doi.org/10.5281/zenodo.20125967
- **Live dashboard:** https://marin-t-kael.de/research/dashboard · **Live JSON:** https://marin-research-pipeline.p96xckbr4c.workers.dev/api/latest and /api/timeseries
- **Collection code (MIT):** https://github.com/marintkael/marin-research-tools · **ORCID:** https://orcid.org/0009-0006-2105-8190

## Files

| config | file | rows | content |
|---|---|---|---|
| default | data/citation_fidelity.parquet | {len(df):,} | every scored answer from the Cloudflare pipeline: OpenAI Search, Gemini (Google web grounding) and the no-web control models (Claude w/o search, Llama 3–3.2, Mistral, Phi-2, GPT-4o-mini w/o search). `llm` names the model; `status` is the rubric class; `score` ∈ {{−3, 0, 0.5, 1, 2, 3}}. |
| claude_web | data/claude_web.parquet | {len(dcw):,} | Claude with web search on claude.ai (Haiku 4.5, Sonnet 4.6, Opus 4.7/4.8), measured through the web interface; documented gap 2026-07-05 to 2026-07-21. |
| questions | data/questions.parquet | {len(q)} | the 16 fixed questions with category and channel (direct / longtail / recommendation / research). |
| data_gaps | data/data_gaps.parquet | {len(g)} | documented measurement-channel outages and method events (a gap is not a zero). |
| daily_channels | data/daily_channels.parquet | {len(dc):,} | daily citation rate per channel pooled across OpenAI Search, Gemini and Claude web; the series behind Figure 1 of Report 03. |

## Scoring

−3 hallucination · 0 not found / disclaimed / collision · 0.5 name-only echo · 1 minimal match · 2 partial book knowledge · 3 full citation with source. Channel citation rate = Σ score ÷ (3 × n). Error rows (timeouts, exhausted quota) carry `status = "error"` and must be excluded from rates; since 2026-08-19 the pipeline's own aggregation excludes them.

## How to load

```python
from datasets import load_dataset
ds = load_dataset("marintkael/ai-citation-fidelity", "default")          # all scored answers
dc = load_dataset("marintkael/ai-citation-fidelity", "daily_channels")   # series behind Report 03, Fig. 1
```

## Citation

Kael, M. T. (2026). *AI Citation Fidelity, Marin T. Kael Research Programme* [Data set]. Hugging Face. https://huggingface.co/datasets/marintkael/ai-citation-fidelity
'''
if DRY:
    print('DRY: Card-Laenge',len(card),'| kein Upload'); sys.exit(0)
from huggingface_hub import HfApi
api=HfApi(token=HF)
def up(dframe,path):
    b=io.BytesIO(); dframe.to_parquet(b,index=False,engine='pyarrow'); b.seek(0)
    api.upload_file(path_or_fileobj=b,path_in_repo=path,repo_id=REPO,repo_type='dataset',commit_message=f'Report 03 extract 2026-08-19: {path}')
    print('   up',path,len(b.getvalue())//1024,'KB')
up(df,'data/citation_fidelity.parquet'); up(dcw,'data/claude_web.parquet'); up(q,'data/questions.parquet'); up(g,'data/data_gaps.parquet'); up(dc,'data/daily_channels.parquet')
api.upload_file(path_or_fileobj=card.encode(),path_in_repo='README.md',repo_id=REPO,repo_type='dataset',commit_message='Report 03 extract 2026-08-19: dataset card')
print('README up'); print('DONE', f'https://huggingface.co/datasets/{REPO}')
