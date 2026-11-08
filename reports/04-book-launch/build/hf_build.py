#!/usr/bin/env python3
"""HF-Datensatz marintkael/ai-citation-fidelity auf den Datenstand von Bericht 04 (Stichtag Wirkungsfenster) bringen.

Zwei Schritte, getrennt:
  bauen   (Standard)  Dateien lokal nach hf_staging/<stichtag>/ schreiben, aktuellen HF-Stand laden,
                      DIFF.md + diff.json schreiben, A1-Prüfung (publish_gate.pruefe) ohne Abbruch protokollieren.
                      Kein schreibender Netzaufruf.
  --push              lädt den bereits gebauten Ordner hoch. NUR nach Freigabe des Betreibers
                      (HF_PUSH_FREIGABE=<JJJJ-MM-TT>), REPORT04_DOI gesetzt, publish_gate.gate fail-closed.

Dateien wie Release 2026-08-19 (gleiche Configs, gleiche Spalten; neu: model_version):
  data/citation_fidelity.parquet  alle ai_citation_results bis Stichtag
  data/claude_web.parquet         Claude auf claude.ai mit Websuche bis Stichtag
  data/questions.parquet          16 feste Fragen (unverändert)
  data/data_gaps.parquet          Lückenregister bis Stichtag (DE + EN)
  data/daily_channels.parquet     NICHT neu gebaut: Reihe hinter Abb. 1 von Bericht 03, bleibt auf HF unverändert

Aufruf:  venv/bin/python3 build/hf_build.py [--cutoff 2026-11-07T23:59:59Z] [--push]
Zugang:  wie fetch.py (MARIN_D1_CMD oder CF_ACCOUNT_ID + D1_DATABASE_ID + CF_API_TOKEN); HF_TOKEN nur für --push.
"""
import argparse, datetime as dt, hashlib, io, json, os, sys, urllib.request
from pathlib import Path
import pandas as pd

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / 'build'))
from fetch import d1, pull, parse_cutoff, iso_sql  # nur SELECT

REPO = 'marintkael/ai-citation-fidelity'
HF_RAW = f'https://huggingface.co/datasets/{REPO}/resolve/main/'
FILES = ['data/citation_fidelity.parquet', 'data/claude_web.parquet', 'data/questions.parquet', 'data/data_gaps.parquet']
Q03 = R.parent / '2026-08-found-not-recommended' / 'data' / 'questions.json'


def build(cutoff):
    sp, _ = iso_sql(cutoff)
    df = pd.DataFrame(pull(
        "SELECT run_id, asked_at, llm, question_id, question, category, score, status, answer_excerpt, model_version "
        f"FROM ai_citation_results WHERE datetime(asked_at) <= datetime('{sp}')", 'asked_at, llm, question_id'))
    dcw = pd.DataFrame(pull(
        "SELECT s.run_ts AS asked_at, r.model AS llm, r.question_id, r.question, r.category, r.score, r.status, "
        "substr(r.answer,1,500) AS answer_excerpt, r.has_web_search FROM claude_web_results r "
        f"JOIN claude_web_snapshots s ON s.id=r.snapshot_id WHERE datetime(s.run_ts) <= datetime('{sp}')",
        's.run_ts, r.model, r.question_id'))
    for f in (df, dcw):
        f['score'] = pd.to_numeric(f['score'], errors='coerce')
    q = pd.DataFrame(json.load(open(Q03)))[['question_id', 'category', 'q']].rename(columns={'q': 'question'})
    ch = {'Direct': 'direct', 'Research': 'research', 'LongTail': 'longtail', 'Genre': 'recommendation',
          'CompCluster': 'recommendation', 'GenreRecommend': 'recommendation'}
    q['channel'] = q['category'].map(ch)
    g = pd.DataFrame(pull("SELECT id, channel, gap_start, gap_end, reason, recorded_at, reason_en FROM data_gaps "
                          f"WHERE datetime(recorded_at) <= datetime('{sp}')", 'id'))
    return {'data/citation_fidelity.parquet': df, 'data/claude_web.parquet': dcw,
            'data/questions.parquet': q, 'data/data_gaps.parquet': g}


def load_hf(cache):
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for f in FILES:
        p = cache / Path(f).name
        if not p.exists():
            req = urllib.request.Request(HF_RAW + f, headers={'User-Agent': 'Mozilla/5.0'})
            p.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        out[f] = pd.read_parquet(p)
    return out


KEYS = {'data/citation_fidelity.parquet': ['asked_at', 'llm', 'question_id'],
        'data/claude_web.parquet': ['asked_at', 'llm', 'question_id'],
        'data/questions.parquet': ['question_id'], 'data/data_gaps.parquet': ['id']}
CMP = {'data/citation_fidelity.parquet': ['score', 'status'], 'data/claude_web.parquet': ['score', 'status', 'answer_excerpt'],
       'data/questions.parquet': ['question', 'category', 'channel'], 'data/data_gaps.parquet': ['reason', 'reason_en', 'gap_start', 'gap_end']}


def diff(new, old):
    rep = {}
    for f in FILES:
        n, o, k = new[f].copy(), old[f].copy(), KEYS[f]
        for x in (n, o):
            for c in k:
                x[c] = x[c].astype(str)
        m = o.merge(n, on=k, how='outer', suffixes=('_alt', '_neu'), indicator=True)
        e = {'zeilen_alt': len(o), 'zeilen_neu': len(n),
             'nur_alt': int((m['_merge'] == 'left_only').sum()), 'nur_neu': int((m['_merge'] == 'right_only').sum()),
             'spalten_neu': sorted(set(n.columns) - set(o.columns)), 'spalten_weg': sorted(set(o.columns) - set(n.columns)),
             'doppelte_schluessel_alt': int(o.duplicated(k).sum()), 'doppelte_schluessel_neu': int(n.duplicated(k).sum())}
        # Änderungen nur auf eindeutigen Schlüsseln zählen (doppelte Schlüssel ergäben ein Kreuzprodukt)
        mu = o.drop_duplicates(k, keep=False).merge(n.drop_duplicates(k, keep=False), on=k, suffixes=('_alt', '_neu'))
        geaendert, beispiele = {}, {}
        for c in CMP[f]:
            if c + '_alt' in mu and c + '_neu' in mu:
                a, b = mu[c + '_alt'], mu[c + '_neu']
                diffmask = ~((a == b) | (a.isna() & b.isna()))
                if c == 'answer_excerpt':   # reine Kürzung auf 500 Zeichen ist keine inhaltliche Änderung
                    kurz = diffmask & pd.Series([x.startswith(y) and len(y) == 500 for x, y in zip(a.fillna(''), b.fillna(''))], index=a.index)
                    e['answer_excerpt_nur_gekuerzt'] = int(kurz.sum())
                    diffmask = diffmask & ~kurz
                geaendert[c] = int(diffmask.sum())
                if c in ('score', 'status', 'answer_excerpt') and diffmask.any():
                    beispiele[c] = mu.loc[diffmask, k].astype(str).agg(' / '.join, axis=1).head(10).tolist()
        e['geaendert_je_spalte'] = geaendert
        e['geaendert_schluessel'] = beispiele
        if 'asked_at' in k:
            e['zeitraum_alt'] = [o['asked_at'].min(), o['asked_at'].max()]
            e['zeitraum_neu'] = [n['asked_at'].min(), n['asked_at'].max()]
            e['nur_alt_vor_2026_08_20'] = int(((m['_merge'] == 'left_only') & (m['asked_at'] < '2026-08-20')).sum())
            e['modelle_neu'] = sorted(set(n['llm']) - set(o['llm']))
        rep[f] = e
    return rep


def write_diff_md(rep, cutoff, out, gate_txt):
    L = [f'# HF-Datensatz {REPO}: Diff neuer Stand gegen veröffentlichten Stand (Release 2026-08-19)', '',
         f'Stichtag neuer Stand: {cutoff:%Y-%m-%d %H:%M:%S} UTC · gebaut {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC',
         'Quelle alt: öffentliche Dateien auf Hugging Face (main). Quelle neu: Messdatenbank, nur SELECT.', '',
         '| Datei | Zeilen alt | Zeilen neu | nur alt | nur neu | geändert (gleicher Schlüssel) | neue Spalten |', '|---|---:|---:|---:|---:|---|---|']
    for f, e in rep.items():
        ge = ', '.join(f'{c} {v}' for c, v in e['geaendert_je_spalte'].items())
        L.append(f"| {f} | {e['zeilen_alt']} | {e['zeilen_neu']} | {e['nur_alt']} | {e['nur_neu']} | {ge} | {', '.join(e['spalten_neu']) or '–'} |")
    L += ['', '## Hinweise je Datei', '']
    for f, e in rep.items():
        L.append(f'- **{f}**: ' + json.dumps({k: v for k, v in e.items() if k not in ('zeilen_alt', 'zeilen_neu')}, ensure_ascii=False, default=str))
    L += ['', 'Prüfen vor Freigabe: Zeilen „nur alt“ (Wegfall veröffentlichter Zeilen) müssen 0 sein oder im Lückenregister begründet; '
          'Änderungen bei gleichem Schlüssel (`geaendert_schluessel`) müssen je einer registrierten Umbewertung oder Redaktion entsprechen. '
          'Geänderte Antwortauszüge betreffen redigierte Stellen: Wortlaut vor dem Hochladen gegenlesen.',
          '`data/daily_channels.parquet` wird nicht neu gebaut und bleibt unverändert.', '', '## A1-Prüfung (publish_gate.pruefe, streng)', '', gate_txt, '']
    (out / 'DIFF.md').write_text('\n'.join(L), encoding='utf-8')


def card(frames, cutoff, doi):
    df, dcw = frames['data/citation_fidelity.parquet'], frames['data/claude_web.parquet']
    cw_models = ', '.join(sorted(set(dcw['llm'])))
    return f'''---
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

Scored measurements of whether web-grounded LLMs **find, correctly cite, or hallucinate** a single, brand-new author entity ("Marin T. Kael"), from the day the entity went online (2026-05-11). Pre-registered, n = 1, fixed catalogue of 16 questions. Since 2026-08-19 measured on anchor days every three days.

**Current release: Report 04 extract, cut-off {cutoff:%Y-%m-%d} (end of the effect window after the book release on 2026-10-08).** Previous release: Report 03 extract, 2026-08-19.

- **Report 04 (DOI):** https://doi.org/{doi}
- **Report Q3 2026 validation (DOI):** https://doi.org/10.5281/zenodo.23145378
- **Report 03 "Found, not recommended" (DOI):** https://doi.org/10.5281/zenodo.22015495
- **Methodology Note 01 (DOI):** https://doi.org/10.5281/zenodo.20170615
- **Live results page:** https://marin-t-kael.de/research/dashboard
- **Collection code (MIT):** https://github.com/marintkael/marin-research-tools

## Files

| config | file | rows | content |
|---|---|---|---|
| default | data/citation_fidelity.parquet | {len(df):,} | every scored answer from the pipeline: OpenAI Search, Gemini (Google web grounding) and the earlier control models. `llm` names the model, `model_version` (since 2026-10-09) the provider's version string; `status` is the rubric class; `score` ∈ {{−3, 0, 0.5, 1, 2, 3}}. |
| claude_web | data/claude_web.parquet | {len(dcw):,} | Claude with web search on claude.ai, measured through the web interface ({cw_models}). |
| questions | data/questions.parquet | {len(frames['data/questions.parquet'])} | the 16 fixed questions with category and channel. |
| data_gaps | data/data_gaps.parquet | {len(frames['data/data_gaps.parquet'])} | documented outages, method events and corrections, German and English (a gap is not a zero). |
| daily_channels | data/daily_channels.parquet | unchanged | series behind Figure 1 of Report 03 (to 2026-08-19); not extended. |

## Changes since the previous release

No previously published row was removed. Rows dated up to 2026-08-19 are unchanged except for documented re-scorings and redactions (described in `data_gaps`). Duplicate answer rows are kept as raw data; rates follow the de-duplication rule of 2026-09-04 (per run, model and question the row closest to the scheduled run time counts). Answer excerpts are now cut at 500 characters throughout.

## Scoring

−3 hallucination · 0 not found / disclaimed / collision · 0.5 name-only echo · 1 minimal match · 2 partial book knowledge · 3 full citation with source. Channel citation rate = Σ score ÷ (3 × n). Error rows carry `status = "error"` and must be excluded from rates.

## Citation

Kael, M. T. (2026). *AI Citation Fidelity, Marin T. Kael Research Programme* [Data set]. Hugging Face. https://huggingface.co/datasets/{REPO}
'''


def pq(frame):
    b = io.BytesIO(); frame.to_parquet(b, index=False, engine='pyarrow'); return b.getvalue()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cutoff', default='2026-11-07T23:59:59Z')
    ap.add_argument('--push', action='store_true')
    a = ap.parse_args()
    cutoff = parse_cutoff(a.cutoff)
    out = R / 'hf_staging' / cutoff.strftime('%Y-%m-%d')
    # A1-Prüfung (publish_gate): Ordner über die Umgebung, damit kein lokaler Pfad im veröffentlichten Code steht
    gate_dir = os.environ.get('MARIN_PUBLISH_GATE_DIR') or sys.exit('MARIN_PUBLISH_GATE_DIR fehlt: Ordner mit publish_gate.py setzen')
    sys.path.insert(0, os.path.expanduser(gate_dir))
    import publish_gate
    if not a.push:
        frames = build(cutoff)
        (out / 'data').mkdir(parents=True, exist_ok=True)
        sums = {}
        for f, fr in frames.items():
            b = pq(fr); (out / f).write_bytes(b); sums[f] = hashlib.sha256(b).hexdigest()
        doi = os.environ.get('REPORT04_DOI', '[[DOI]]')
        (out / 'README.md').write_text(card(frames, cutoff, doi), encoding='utf-8')
        rep = diff(frames, load_hf(R / 'hf_staging' / '_hf_release_2026-08-19'))
        b = publish_gate.pruefe('huggingface:%s (Vorpruefung)' % REPO, daten=[(f, (out / f).read_bytes()) for f in frames],
                                texte={'dataset_card': (out / 'README.md').read_text()})
        gate_txt = ('sauber' if b.sauber else 'Treffer: ' + json.dumps(b.als_protokoll(), ensure_ascii=False)) + f' · {b.geprueft} Gegenstände'
        write_diff_md(rep, cutoff, out, gate_txt)
        (out / 'diff.json').write_text(json.dumps({'cutoff': a.cutoff, 'sha256': sums, 'diff': rep, 'a1_sauber': b.sauber,
                                                  'doi_gesetzt': doi != '[[DOI]]'}, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
        print(json.dumps({'ordner': str(out), 'zeilen': {f: len(fr) for f, fr in frames.items()}, 'a1_sauber': b.sauber}, ensure_ascii=False))
        sys.exit(0 if b.sauber else 1)
    # --push: nur der bereits gebaute, geprüfte Ordner
    if not os.environ.get('HF_PUSH_FREIGABE'):
        sys.exit('HF-PUSH GESPERRT: erst nach Freigabe des Betreibers HF_PUSH_FREIGABE=<Datum> setzen.')
    meta = json.loads((out / 'diff.json').read_text())
    if not meta.get('doi_gesetzt'):
        sys.exit('Datensatzkarte ohne DOI: mit gesetztem REPORT04_DOI neu bauen.')
    for f, s in meta['sha256'].items():
        if hashlib.sha256((out / f).read_bytes()).hexdigest() != s:
            sys.exit(f'{f} weicht vom geprüften Bau ab – neu bauen.')
    card_txt = (out / 'README.md').read_text()
    publish_gate.gate('huggingface:%s' % REPO, daten=[(f, (out / f).read_bytes()) for f in meta['sha256']], texte={'dataset_card': card_txt})
    from huggingface_hub import HfApi
    tok = os.environ.get('HF_TOKEN') or sys.exit('HF_TOKEN fehlt')
    api = HfApi(token=tok)
    for f in meta['sha256']:
        api.upload_file(path_or_fileobj=str(out / f), path_in_repo=f, repo_id=REPO, repo_type='dataset',
                        commit_message=f'Report 04 extract {cutoff:%Y-%m-%d}: {f}')
        print('up', f)
    api.upload_file(path_or_fileobj=card_txt.encode(), path_in_repo='README.md', repo_id=REPO, repo_type='dataset',
                    commit_message=f'Report 04 extract {cutoff:%Y-%m-%d}: dataset card')
    print('DONE', f'https://huggingface.co/datasets/{REPO}')
