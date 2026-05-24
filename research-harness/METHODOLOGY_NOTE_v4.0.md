# Marin T. Kael Citation-Fidelity Research Programme · Methodology Note 01 v4.0

**Amendment to Pre-Registration DOI:** [10.5281/zenodo.20125967](https://doi.org/10.5281/zenodo.20125967)
**Previous Methodology Version:** v3.0 (DOI [10.5281/zenodo.20308495](https://doi.org/10.5281/zenodo.20308495))
**This Amendment:** v4.0 (locked 2026-05-23)

## What changed in v4.0

v4.0 is an **infrastructure migration**, not a methodological reformulation. The score-algorithm, question-set, and aggregation logic are byte-identical to v3.0 (verified: 27/27 historical datapoints match 1:1 between v3.0 worker-JS and v4.0 Python implementation).

**What changed:**
- Mess-Instrument: in-Worker JavaScript score-functions → standalone Python package on top of [EleutherAI lm-evaluation-harness v0.4.12](https://github.com/EleutherAI/lm-evaluation-harness)
- Reproducibility: pinned tooling versions, public GitHub repo, replicable on any researcher's laptop in <5 minutes
- Change-Discipline: methodology-relevant constants now locked in single Python file with explicit versioning protocol (see § Change-Discipline below)

**What did NOT change:**
- 16 anchor questions across 6 categories (Direct/Genre/LongTail/CompCluster/Research/GenreRecommend)
- Score scale -3..+3 with semantic anchors (hallucinated → not_found → minimal/partial/full_citation)
- MARIN_SPECIFIC anchor (Marin T. Kael must appear in answer for non-zero non-negative score)
- NEGATIVE_HALLU patterns (Mokka Müller / Pauline Kael / Maritime Research Institute / etc.)
- 5 model coverage (OpenAI mini-search-preview + flagship-search-preview, Gemini 2.5-flash-grounded, Claude Sonnet 4.6 / Opus 4.7 via claude.ai web-search)
- Aggregation: provider-mean (sum-of-scores ÷ answers-per-provider)

## Why this matters for replication

v3.0 was tied to the operational Cloudflare Workers stack — score-algorithm changes required deploy, reproducibility required runtime access to Cloudflare. v4.0 makes the methodology a **standalone Python artifact** that any external researcher can replicate:

```bash
git clone https://github.com/marintkael/marin-research-tools
cd marin-research-tools/research-harness
pip install "lm-eval[api]==0.4.12"
python run_all_models.py --skip claude_sonnet_4_6_web,claude_opus_4_7_web  # API LLMs only
```

This gives external replication-bidders identical scores as the operational pipeline.

## Architecture

```
Anchor Questions (locked, 16)         Score Functions (locked)
       ↓                                       ↓
       └──────→ lm-evaluation-harness 0.4.12 ←──────┘
                        ↓
               Custom Model Adapters
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
   OpenAI Search   Gemini Grounded  Claude Web Importer
   (with 429-retry) (with UA-fix)    (replays JSON snapshots)
                        ↓
                 Snapshot (JSON)
                        ↓
          Push to Cloudflare D1 (existing /__push_claude_web)
                        ↓
                Dashboard rendering
```

## Change Discipline

- **Patch (v4.0.x):** Tool-bug-fixes without methodological impact. No Amendment-DOI required.
- **Minor (v4.1, v4.2, ...):** Additive changes (new NEGATIVE_HALLU pattern, new model adapter). Methodology-Note-Amendment Zenodo-DOI required; task version stays `marin_research_v1`.
- **Major (v5.0):** Breaking changes (new question, score-formula change, anchor redefinition). Requires new task version `marin_research_v2`, full Pre-Registration-Amendment, all post-v4 data treated as separate cohort.

Locked constants live in `marin_tasks/utils.py` top section. Editing them requires Methodology-Note-Amendment. Code-review-discipline ensures no silent changes.

## Limitations

1. **OpenAI search-preview rate-limits:** account-level ~5 req/min hard limit. Daily-cron-runs work; ad-hoc re-runs trigger 429s. Custom adapter implements 3-retry exponential backoff.
2. **Claude API doesn't expose claude.ai web-search:** Anthropic's `web_search` API tool ≠ claude.ai's grounded chat. We use manual web-sweeps against claude.ai (16 questions × 2 model-tiers per cycle) and import the resulting JSON snapshots through the `claude_web_importer` adapter. Not 100% automated by design — the manual sweep is part of the protocol.
3. **Gemini 2.5-flash grounding:** Google-Search-Tool may return inconsistent results across runs (search-result-ordering variance). Multi-day averaging mitigates this.

## Reproducibility checklist

- [x] Pinned harness version (`lm-eval==0.4.12`)
- [x] Pinned Python version (3.11)
- [x] Locked question-suite (questions.jsonl, 16 frozen)
- [x] Locked scoring logic (utils.py top-section)
- [x] Public GitHub repo with all source
- [x] CI on GitHub Actions (daily 04:30 UTC)
- [x] Snapshot artifacts retained 90 days per run
- [x] Push-to-D1 schema documented (`/__push_claude_web` endpoint)

## Files released with this Amendment

```
research-harness/
  ├── README.md                       Architecture + Quick-Start
  ├── METHODOLOGY_NOTE_v4.0.md        This document
  ├── marin_tasks/
  │   ├── marin_research_v1.yaml      Task config (frozen)
  │   ├── utils.py                     Score functions (locked)
  │   └── questions.jsonl              16 anchor questions
  ├── marin_models/
  │   ├── openai_search.py            OpenAI search-preview adapter
  │   ├── gemini_grounded.py          Gemini-grounded adapter
  │   └── claude_web_importer.py      claude.ai JSON-replay adapter
  ├── run_eval.py                     Single-model runner
  ├── run_all_models.py               Full-sweep runner
  ├── push_snapshot_to_d1.py          D1-push wrapper
  └── .github/workflows/
      └── marin-eval-daily.yml        CI cron
```

## Author

Marin T. Kael (pseudonym, German fantasy author)
Site: https://marin-t-kael.de
Research-Dashboard: https://marin-t-kael.de/research

## Acknowledgments

- EleutherAI for the lm-evaluation-harness framework
- Cloudflare for the Workers/D1/AI-Gateway stack
