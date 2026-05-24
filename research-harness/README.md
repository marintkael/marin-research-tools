# Marin Research Harness · lm-evaluation-harness Migration

**Status:** Migration v4.0 (2026-05-23) · Locked Methodology · Replicable

Replicate-friendly Citation-Treue-Forschung für Marin T. Kael — basiert auf **EleutherAI lm-evaluation-harness v0.4.12** (industry-standard LLM evaluation framework).

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "lm-eval[api]==0.4.12"

# Run a single LLM
python run_eval.py --model claude_web_importer --model_args model_tier=sonnet

# Run all 5 LLMs + build snapshot
python run_all_models.py

# Push snapshot to D1 (requires MARIN_RESEARCH_TRIGGER_TOKEN)
python push_snapshot_to_d1.py --snapshot results/snapshot_LATEST.json
```

## Architecture

```
marin_tasks/
  ├── marin_research_v1.yaml       Task config (locked v4.0)
  ├── utils.py                      Score-funktionen (MARIN_SPECIFIC, NEGATIVE_HALLU)
  └── questions.jsonl               16 fragen × 6 Kategorien

marin_models/
  ├── openai_search.py              gpt-4o(-mini)-search-preview with 429-retry-backoff
  ├── gemini_grounded.py            Gemini 2.5-flash + Google-Search-Grounding
  └── claude_web_importer.py        Importer for /tmp/marin_sweep/*.json (manual sweeps)

run_eval.py                         Single-model wrapper
run_all_models.py                   Full 5-LLM sweep
push_snapshot_to_d1.py              D1-Push (compatible with /__push_claude_web)
.github/workflows/marin-eval-daily.yml   Daily CI cron (04:30 UTC)
```

## Methodology

- **Pre-Registration DOI:** `10.5281/zenodo.20125967` (v1)
- **Methodology Note 01 v4.0:** `10.5281/zenodo.20308495` (Amendment T-122)
- **Task Version:** `marin_research_v1` (frozen — breaking changes = new task version `v2`)
- **Score-Scale:** -3 (hallucinated) .. 0 (not found) .. +3 (full citation)

### Question-Suite (16, locked)

| Category | N | Examples |
|---|---|---|
| Direct | 3 | D1 "Wer ist Marin T. Kael?", D2 "Was ist Das vierte Feld", D3 "Wann erscheint" |
| Genre | 2 | G1 "Fantasy-Debüts 2026", G2 "High-Fantasy-Autoren DE" |
| LongTail | 2 | L1 "Stadt Varin", L2 "Edikt-Magie" |
| CompCluster | 2 | C1 "Robin Hobb DE", C2 "Robert Jackson Bennett Fans" |
| Research | 1 | R1 "Marin Research Programme" |
| GenreRecommend | 6 | GR1-GR6 marin-blind genre placements |

### Models

| LLM | Provider | Web-Search | Adapter |
|---|---|---|---|
| gpt-4o-mini-search-preview | OpenAI | ✓ Bing | `openai_search_preview` (custom) |
| gpt-4o-search-preview (Flagship) | OpenAI | ✓ Bing | `openai_search_preview` (custom) |
| gemini-2.5-flash | Gemini | ✓ Google grounding | `gemini_grounded` (custom) |
| claude-sonnet-4.6 (web) | Anthropic | ✓ via claude.ai | `claude_web_importer` (manual sweep) |
| claude-opus-4.7 (web) | Anthropic | ✓ via claude.ai | `claude_web_importer` (manual sweep) |

**Note:** Anthropic API doesn't expose claude.ai's grounded web-search. Sweeps are performed manually against the claude.ai web interface (16 questions × 2 model-tiers = 32 calls per cycle), saved to `/tmp/marin_sweep/{QID}_{TIER}.json`. The `claude_web_importer` reads these snapshots back into the harness pipeline.

## Change-Discipline (locked)

- **Patch (v4.0.x):** Bug-Fixes ohne Methodology-Impact. No Amendment-DOI.
- **Minor (v4.1):** Additive Änderungen. New Amendment-DOI to Zenodo, task stays `marin_research_v1`.
- **Major (v5.0):** Breaking changes (new questions, score-algorithm-shift). New task version `marin_research_v2`, full Pre-Reg-Amendment.

All score-relevant constants (`MARIN_SPECIFIC`, `KEY_FACTS`, `NEGATIVE_HALLU`) are locked in `marin_tasks/utils.py` Top-Section. Changes there require Methodology-Note-Amendment.

## CI / Cron

GitHub Actions runs daily 04:30 UTC (`.github/workflows/marin-eval-daily.yml`):
1. Install lm-eval-harness
2. Run all API-LLMs (OpenAI mini + Flagship, Gemini grounded)
3. Push snapshot to Cloudflare D1 via worker `/__push_claude_web`
4. Upload artifact for 90 days

Claude-web (Sonnet + Opus) runs separately as a manual web-sweep, pushed via the same script.

## Replication

```bash
git clone https://github.com/marintkael/marin-research-tools
cd marin-research-tools/research-harness
python -m venv .venv && source .venv/bin/activate
pip install "lm-eval[api]==0.4.12"
# Set OPENAI_API_KEY, GEMINI_API_KEY in env
python run_all_models.py --skip claude_sonnet_4_6_web,claude_opus_4_7_web
# Results in results/snapshot_LATEST.json — identical methodology to Marin's official runs
```

## Provenance

- Migration date: 2026-05-23
- Replaced: in-Worker JavaScript score-algorithm (v3.0.3) with the lm-evaluation-harness Python implementation
- Score-parity verified: 27/27 historical datapoints match the legacy v3.0 scoring 1:1
