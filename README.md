# marin-research-tools

> Open methodology tooling for the **Marin T. Kael Research Programme** —
> KI-Zitations-Feldlabor (AI Citation Behavior Lab).
>
> Public companion to **https://marin-t-kael.de/research**.

These are the small, opinionated scripts that sit between author practice
and publication for the German-language high-fantasy saga *Prägungen des
Reiches* (opening volume *Das vierte Feld*, scheduled for 22 September 2026).

The repository exists because the research programme observes — empirically
and openly — how language-model-based search systems, AI answer engines and
knowledge graphs ingest, understand and cite an author identity. The
programme operates in two phases:

- **Phase 1 (May 2026 → Q3 / 2027) — Measurement-instrument validation.**
  Eight measurement surfaces (Wikidata, Google Knowledge Graph, Bing
  Webmaster KI, Google Search Console, Google AI Overviews, Goodreads /
  Hardcover, Reddit, language-model browser probes) are sampled daily.
  Test-retest reliability, intra-set consistency, CUSUM drift-detection
  across model updates and coverage mapping per identity cluster are
  quantified. A public codebook (v0.x → v1.0) operationalises what counts
  as a 'correct citation'.

- **Phase 2 (from Q3 / 2027 onward) — Pre-registered action-effect studies**
  on the then-validated apparatus. Effect measures appropriate for an
  n-of-1 design (Interrupted Time Series, Bayesian Structural Time Series,
  hierarchical Bayes), not pre/post Cohen's d on single actions.

Everything in this repository is public so methodology reviewers can
reproduce the measurement.

## What is in this repository

- **`style_lint.py`** — a content-policy and style linter that runs over
  drafts before they leave the author's workstation. It is the gate that
  catches canon contradictions, persona drift and platform-rule violations
  (Reddit self-promotion CTAs, voice drift, spoiler leaks). Designed to be
  called both from the command line and as a Python library.
- **`reddit_comment_drafter.py`** — a *drafter*, not a poster. It reads
  public Reddit data, produces draft comments via a language model and
  emits them into a Markdown review file. The Reddit Data API is not used
  to submit content. Every draft is reviewed and posted manually by a
  human in Reddit's normal web UI.
- **`policies/`** — documentation and example of the operator-private
  pattern layer. The framework supports loading additional patterns from a
  local file referenced via the `STYLE_LINT_PRIVATE_RULES` environment
  variable; this is where the operator-specific pseudonym firewall and
  internal-system-leak patterns live in actual deployments. They are not
  included in this public repository because the patterns themselves would
  defeat the purpose of having them.
- **`docs/`** — the public research framework (four Phase-1 investigation
  lines) and the responsible-build commitments that govern this tooling.

## What is *not* in this repository

- No pseudonym-firewall patterns (operator-specific, loaded from a private
  `.env`).
- No internal system or vendor names (operator-specific, loaded from a
  private `.env`).
- No authentication credentials.
- No production paths or operator-specific runtime layout.
- No automation that posts, comments, votes or DMs on the author's behalf.

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

## Usage

```bash
# Lint a draft string
python3 style_lint.py --text "Marin T. Kael's debut..." --surface reddit

# Lint a file
python3 style_lint.py --file path/to/draft.md --strict

# As a library
from style_lint import check
result = check(comment_text, surface="reddit")
if result["blocked"]:
    print("CANNOT POST"); print(result["violations"])
```

The Reddit drafter expects a small JSON file describing recent
high-engagement threads about comparable authors. The ingestion script
that produces this file is straightforward (public `.json` endpoint on
Reddit) and is left as an exercise rather than included here, to keep the
surface small and reviewable.

## Operator commitments

The full public commitment list is in
[`docs/responsible-build-policy.md`](docs/responsible-build-policy.md).
Summary:

- One human, one account (`u/marintkael`). No alts, ever.
- No automated posting, commenting, voting, replies or DMs.
- Manual submission via the normal Reddit web UI is hard-required.
- Daily public-write volume across all platforms combined: 2–3 maximum.
- Daily read volume: under 1,000 GET, well below rate limits.
- User-Agent string: `marin-t-kael:research-tooling:v0.1 (by /u/marintkael)`.
- 429 / 503 responses → exponential backoff. All rate-limit headers respected.
- No scraping of personal user data. No DM-content access. No
  aggregate-and-resell. No ad targeting. No LLM-training-data export.
- Public failure log: every draft blocked by the linter is logged with its
  reason and summarised in the quarterly research write-ups on
  https://marin-t-kael.de/research, so the policy boundary is auditable
  from the outside.

## Security and secret hygiene

Two automated layers run against every commit and every release tag:

- **Pre-commit** — install with `pip install pre-commit && pre-commit install`.
  Runs [gitleaks](https://github.com/gitleaks/gitleaks) with the custom
  `.gitleaks.toml` config in this repo (secret-scan rules for Zenodo
  tokens, GitHub PATs, Wikidata OAuth tokens, OpenAI API keys, Anthropic
  API keys, IndexNow keys, generic token-assignments, and PEM private
  keys), plus standard file-hygiene hooks (trailing whitespace,
  large-file detection, private-key detection, merge-conflict markers).
- **Pre-tag** — the operator runs a three-layer scan before any tag is
  pushed: an A1-firewall layer (style_lint with the operator-private
  rules), the gitleaks scan, and a tree-hygiene check that fails on any
  `.env`, `.token`, `.secret`, `.pem`, `.key` file in the tree. Only when
  all three layers pass does the tag get created and pushed.

The operator-private layer (real-name firewall, internal-system-name
patterns) is loaded at runtime from a file referenced via the
`STYLE_LINT_PRIVATE_RULES` environment variable. That file is never
committed — the patterns themselves are the strings the rules are meant
to suppress.

## Release process

This repository uses a two-tier release process:

- **`v0.1` (current) — Setup release.** Published manually to Zenodo on
  11 May 2026 as part of the Phase-1 nullpoint publication set
  (Methodology Note 01, Pre-Registration Q0, Codebook v0.1,
  marin-research-tools v0.1, Wikidata snapshot T+0). DOI:
  [10.5281/zenodo.20126017](https://doi.org/10.5281/zenodo.20126017).
  Treated as bootstrap — no Concept-DOI parent, single Version-DOI only.
- **`v0.2` onwards — GitHub → Zenodo integration.** Every Git tag pushed
  to this repository automatically triggers a Zenodo deposit through the
  Zenodo OAuth integration. Each new tag receives a fresh Version-DOI in
  a dedicated Concept-DOI family that starts at `v0.2`. The first such
  release is forthcoming.

When citing the *current* state of the tooling, use the v0.1 Version-DOI
above. When citing a *specific later version*, use the Version-DOI from
that release's Zenodo record. When citing the tooling *in general
without commitment to a version*, use the Concept-DOI of the v0.2-onwards
family (will be issued automatically by Zenodo with the first integrated
release).

## Cite this

If you use these tools in a published replication or methods comparison,
please cite the corresponding DOI release on Zenodo. The current Phase-1
release set:

- **Methodology Note 01** — Baseline-Messung: Autor-Identität im
  Zitations-Verhalten von Sprachmodellen. DOI:
  [10.5281/zenodo.20125934](https://doi.org/10.5281/zenodo.20125934)
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
