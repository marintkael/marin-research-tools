# marin-research-tools

> Open methodology tooling for the **Marin T. Kael Research Programme** —
> KI-Zitations-Feldlabor (AI Citation Behavior Lab).
>
> Public companion to **https://marin-t-kael.de/research**.

These are the small, opinionated scripts that support the research programme
around the German-language high-fantasy saga *Prägungen des Reiches*
(opening volume *Das vierte Feld*, scheduled for 22 September 2026).

The repository exists because the research programme observes — empirically
and openly — how language-model-based search systems, AI answer engines and
knowledge graphs ingest, understand and cite an author identity.

## Reproduce in GitHub Codespaces

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/marintkael/marin-research-tools)

Click the badge for a ready-to-use Python 3.11 dev container with
`lm-eval[api]==0.4.12` (the locked harness version) and required Python
packages pre-installed. After the container starts, add your LLM provider
API keys under *Settings → Codespaces → Secrets* (`OPENAI_API_KEY`,
`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`) and run:

```bash
cd research-harness
python run_eval.py --model claude_web_importer   # single model
python run_all_models.py                          # full 5-LLM sweep
```

No local Python install, no version drift. GitHub's free tier covers
60 container-hours per month per account — enough for several full
methodology reproductions.

Container definition: [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json).

## Active 3-phase design (v2.4)

As of Methodology Note 01 v2.4 (14 May 2026) the programme runs an explicit
three-phase design:

- **Phase 1 (May → Sep 2026)** — active pre-launch interventions Q0–Q6 on
  identity surfaces (Wikidata co-occurrence, Zenodo DOI cadence,
  Common-Crawl optimisation, Reddit karma building, Cross-LLM Trust Graph),
  running in parallel with daily measurement-instrument validation across
  eleven surfaces. Test-retest reliability, intra-set consistency,
  CUSUM drift-detection across model updates and coverage mapping per
  identity cluster are quantified. A public codebook (v0.x → v1.0)
  operationalises what counts as a 'correct citation'.

- **Phase 2 (Sep 2026 → Q3 / 2027)** — post-launch effect detection. The
  book launch on **22 September 2026** is treated as the central deliberate
  intervention; aggregated effect measurement across all eleven surfaces
  is run against the pre-launch baseline. Holdout periods are scheduled
  wherever methodologically tenable.

- **Phase 3 (from Q3 / 2027)** — long-term controlled experiments on the
  then-validated apparatus. Effect measures appropriate for an n-of-1
  design (Interrupted Time Series, Bayesian Structural Time Series,
  hierarchical Bayes), not pre/post Cohen's d on single actions.

Everything in this repository is public so methodology reviewers can
reproduce the measurement.

## Active Pre-Registrations Q0–Q6

Seven independent, formally pre-registered probes run in temporal parallel
across Phase 1. Full YAML specifications live under
[`pre_registrations/`](pre_registrations/); the table below is a compact
overview.

| ID | Hypothesis | Intervention | Surface | Status |
|----|-----------|--------------|---------|--------|
| **Q0** | Wikidata statements reach the Google Knowledge Graph within ≤14 days | Wikidata curation (Q139720807 + Q139720798) | Google KG Search API · KG score | active (latency ≈ 40 h observed T+0 → T+2) |
| **Q1** | P136 genre statements increase co-occurrence in the LLM cluster | Wikidata co-occurrence engineering (6–8 P-statements) | Cross-LLM Trust Graph · CompCluster score | registered (execution Q3 / 2026) |
| **Q2** | Inclusion in CC-MAIN-2026-21 (May snapshot) increases LLM citation score in the next model cycle | Common-Crawl optimisation (`/llms.txt`, `/ai.txt`, `/about.txt` + backlinks) | Cross-LLM Trust Graph from Q4 / 2026 (LLM re-training lag) | active (files deployed T+2) |
| **Q3** | Source-attribution profile per LLM drifts < 1 trust point over 90 days (stability anchor for ITS) | Cross-LLM Trust Graph tracking (12 patterns × 9 LLMs) | source-attribution score per LLM | active (live from T+3 after cron 04:00 UTC) |
| **Q4** | Reddit comment karma > 200 in 6 subreddits over 90 days increases mention-cluster visibility | Reddit karma building (1× substantive comment / sub / week) | Reddit mention-cluster · public log | active (running in r/Fantasy since T+0; 7 more subs from T+3) |
| **Q5** | Zenodo DOI cadence (1 MN / quarter) triggers Wikipedia notability threshold crossing | Zenodo DOI salvo (MN-01 v1.x + v2.x, MN-02 Q3, MN-03 Q4) | Wikipedia article-existence probe (CC-MAIN coverage) | registered (MN-01 v2.0 live T+2; MN-02 ca. 2026-07-15) |
| **Q6** | Consistent reader-activity on Hardcover produces a reader-authenticity signal that strengthens cross-linking to Goodreads and the LLM trust cluster 'reading community' | Reader-account activity volume on Hardcover (reviews, mark-as-read, want-to-read). Activity volume is the variable; attributes of individual reviews (rating, length, voice) are outside the research design. | Hardcover snapshot pipeline · books_read · reviews_written · cross-LLM trust graph cluster 'reading community' | active (since T+3, low-volume sustained) — **new in v2.3, refactored in v0.3** |

Q0–Q6 are formally independent but run in temporal parallel — inter-Q
confounds are explicitly named in each quarterly report.

## What is in this repository

- **`style_lint.py`** — a manuscript style-consistency linter for
  *Prägungen des Reiches*. It catches canon contradictions (protagonist
  name, world-mechanic definition), umlaut-encoding drift in German text,
  and the saga title spelling. Designed to be called both from the
  command line and as a Python library.
- **`source_attribution_parser.py`** — Python port of the Cross-LLM Trust
  Graph source-attribution parser. Twelve source patterns
  (Wikipedia / Wikidata / ORCID / Zenodo / Goodreads / Amazon / official
  site / GitHub / press / Reddit / inference / no-source) with trust
  weights from +2 (verifiable primary) through 0 (neutral) to -1
  (hallucination risk). Feeds the source × LLM heatmap underlying
  pre-registration Q3.
- **`migrations/0003_ai_citation_sources.sql`** — SQLite/D1 table for the
  Cross-LLM Trust Graph snapshots used by Q3.
- **`pre_registrations/`** — seven YAML files Q0.yaml … Q6.yaml. The full
  pre-registration appendix to each quarterly report.
- **`docs/`** — the public research framework (four Phase-1 investigation
  lines).

## What is *not* in this repository

- No automation that posts, comments, votes or DMs on the author's behalf.
- No authentication credentials.
- No production paths or private runtime layout.

## Why this exists

The genre fiction publishing market is being reshaped by AI search systems,
knowledge graphs and answer engines. Most claims about how author
visibility works there are anecdotal. This programme takes the opposite
stance: measure the surfaces empirically, validate the measurement
apparatus before claiming effects, publish methods + raw data + failure
logs openly, and let other author identities replicate the protocol.

The four Phase-1 investigation lines documented at
[marin-t-kael.de/research](https://marin-t-kael.de/research):

1. **Citation inventory** — what does each measurement surface currently
   show of the defined author identity, mapped as coverage per
   identity cluster (person / work / genre / world-mechanic).
2. **Measurement-instrument validation** — how reliable is each surface
   under test-retest, what is its drift characteristic across model
   updates, which surfaces are redundant?
3. **Codebook iteration** — public versions of the annotation schema
   (v0.x → v1.0) with documented edge-cases and inter-rater agreement
   from Q4 / 2026.
4. **Open materials** — methods, code, raw data, failure logs all openly
   licensed.

## Live materials

- **Methodology Note 01 v2.2 (current)** — full Phase-1 baseline write-up:
  https://marin-t-kael.de/research/01-baseline-methodology
- **Programme index** — https://marin-t-kael.de/research
- **Wikidata author entity** — https://www.wikidata.org/entity/Q139720807
- **ORCID** — https://orcid.org/0009-0006-2105-8190

## Usage

```bash
# Lint a manuscript string
python3 style_lint.py --text "Marin T. Kael's debut..."

# Lint a file
python3 style_lint.py --file path/to/text.md --strict

# Parse source-attribution from a single LLM answer
echo "According to Wikipedia and ORCID..." | \
  python3 source_attribution_parser.py --llm openai --question D1

# As a library
from style_lint import check
result = check(text)
if result["blocked"]:
    print("BLOCKED"); print(result["violations"])

from source_attribution_parser import parse_sources
rows = parse_sources(answer_text, llm_id="claude", question_id="D2")
```

## Author-account commitments

Public commitments that govern the author identity behind this programme:

- One human, one account (`u/marintkael`). No alts, ever.
- No automated posting, commenting, voting or DM-sending on the author's
  behalf. Every public write goes through the platform's normal web UI.
- Daily public-write volume across all platforms combined: 2–3 maximum.
- Daily read volume: under 1,000 GET, well below rate limits.
- User-Agent string for any read-only API access:
  `marin-t-kael:research-tooling:v0.2 (by /u/marintkael)`.
- 429 / 503 responses → exponential backoff. All rate-limit headers respected.
- No scraping of personal user data. No DM-content access. No
  aggregate-and-resell. No ad targeting. No LLM-training-data export.

## Security and secret hygiene

An automated layer runs against every commit:

- **Pre-commit** — install with `pip install pre-commit && pre-commit install`.
  Runs [gitleaks](https://github.com/gitleaks/gitleaks) with the custom
  `.gitleaks.toml` config in this repo (secret-scan rules for Zenodo
  tokens, GitHub PATs, Wikidata OAuth tokens, OpenAI API keys, Anthropic
  API keys, IndexNow keys, generic token-assignments, and PEM private
  keys), plus standard file-hygiene hooks (trailing whitespace,
  large-file detection, private-key detection, merge-conflict markers).

## Release process

This repository uses a two-tier release process:

- **`v0.1` (setup release).** Published manually to Zenodo on
  11 May 2026 as part of the Phase-1 nullpoint publication set
  (Methodology Note 01, Pre-Registration Q0, Codebook v0.1,
  marin-research-tools v0.1, Wikidata snapshot T+0). DOI:
  [10.5281/zenodo.20126017](https://doi.org/10.5281/zenodo.20126017).
  Treated as bootstrap — no Concept-DOI parent, single Version-DOI only.
- **`v0.2` onwards — GitHub → Zenodo integration.** Every Git tag pushed
  to this repository automatically triggers a Zenodo deposit through the
  Zenodo OAuth integration. Each new tag receives a fresh Version-DOI in
  a dedicated Concept-DOI family that starts at `v0.2`.

When citing the *current* state of the tooling, use the v0.2 Version-DOI
from this release. When citing a *specific later version*, use the
Version-DOI from that release's Zenodo record. When citing the tooling
*in general without commitment to a version*, use the Concept-DOI of the
v0.2-onwards family.

## Cite this

If you use these tools in a published replication or methods comparison,
please cite the corresponding DOI release on Zenodo. The current Phase-1
release set:

- **Methodology Note 01 v2.2 (current)** — Baseline-Messung: Autor-Identität
  im Zitations-Verhalten von Sprachmodellen. Active three-phase design,
  SSRN-style working paper, DE + EN, 13 May 2026.
  - Version-DOI: [10.5281/zenodo.20170615](https://doi.org/10.5281/zenodo.20170615)
  - Concept-DOI: [10.5281/zenodo.20125933](https://doi.org/10.5281/zenodo.20125933)
- **Methodology Note 01 — version history.** v2.1 (12 May 2026, Cross-LLM
  Trust Graph hard-coded), v2.0 (12 May 2026, active 3-phase design
  introduced), v1.x (10–11 May 2026, two-phase setup release). All
  historical Version-DOIs resolve from the Concept-DOI above.
- **Vor-Registrierung Q0** — Pre-Launch-Instrument-Validierung. DOI:
  [10.5281/zenodo.20125967](https://doi.org/10.5281/zenodo.20125967)
- **Codebuch v0.1** — Annotations-Schema. DOI:
  [10.5281/zenodo.20125976](https://doi.org/10.5281/zenodo.20125976)
- **marin-research-tools v0.1** — this repository (setup release). DOI:
  [10.5281/zenodo.20126017](https://doi.org/10.5281/zenodo.20126017)
- **Wikidata Identitäts-Snapshot T+0** — Nullpoint dataset. DOI:
  [10.5281/zenodo.20126038](https://doi.org/10.5281/zenodo.20126038)

## License

MIT — see [`LICENSE`](LICENSE).

## Contact

Research enquiries: research@marin-t-kael.de
Project page: https://marin-t-kael.de/research
