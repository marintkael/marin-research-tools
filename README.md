# marin-research-tools

> Pre-publication tooling for an AI-augmented author practice.
>
> Public companion to the research project at
> **https://marin-t-kael.de/research**.

These are the small, opinionated scripts that sit between drafting and
publication for the German-language high-fantasy saga *Prägungen des Reiches*
(opening volume *Das vierte Feld*, scheduled for 2026-09-22).

The repository exists because the author intends to use AI-assisted tooling
openly and document the practice, instead of hiding it. Everything here is
public so reviewers, readers and platform operators can audit the boundary
between author work and tooling.

## What is in this repository

- **`style_lint.py`** — a content-policy and style linter that runs over
  drafts before they leave the author's workstation. It is the gate that
  catches canon contradictions, persona drift and platform-rule violations
  (Reddit self-promotion CTAs, AI-voice patterns, spoiler leaks). Designed to
  be called both from the command line and as a Python library.
- **`reddit_comment_drafter.py`** — a *drafter*, not a poster. It reads
  public Reddit data, produces draft comments via a language model and
  emits them into a Markdown review file. The Reddit Data API is not used to
  submit content. Every draft is reviewed and posted manually by a human in
  Reddit's normal web UI.
- **`policies/`** — documentation and example of the operator-private
  pattern layer. The framework supports loading additional patterns from a
  local file referenced via the `STYLE_LINT_PRIVATE_RULES` environment
  variable; this is where the operator-specific real-name firewall and
  internal-system-leak patterns live in actual deployments. They are not
  included in this public repository because the patterns themselves would
  defeat the purpose of having them.
- **`docs/`** — the public research framework (four observation fields) and
  the responsible-build commitments that govern this tooling.

## What is *not* in this repository

- No real-name firewall patterns (operator-specific, loaded from a private
  `.env`).
- No internal system or vendor names (operator-specific, loaded from a
  private `.env`).
- No authentication credentials.
- No production paths or operator-specific runtime layout.
- No automation that posts, comments, votes or DMs on the author's behalf.

## Why exist?

The genre fiction publishing market is in the early phase of AI-assisted
authorship becoming common. Most of that practice today is hidden. This
project takes the opposite stance: the tooling is named, scoped and
audit-able, and the operator publishes quarterly findings on what worked,
what was blocked, and what drifted.

Four observation fields, all documented at
[marin-t-kael.de/research](https://marin-t-kael.de/research):

1. **Knowledge graph synchronisation** — how structured statements about a
   literary work propagate through Wikidata, knowledge graphs and AI
   training corpora.
2. **AI citation fidelity** — when language models are asked directly about
   the work, what do they know, what do they hallucinate, what self-corrects
   over months.
3. **Reader-community participation** — can an author with AI-assisted
   preparation contribute substantively to genre conversations without
   degrading the discourse?
4. **Voice consistency under tooling** — when outbound communication runs
   through pipelines, how is voice held stable; which drift patterns recur?

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
high-engagement threads about comparable authors. The ingestion script that
produces this file is straightforward (public `.json` endpoint on Reddit)
and is left as an exercise rather than included here, to keep the surface
small and reviewable.

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
- 429/503 responses → exponential backoff. All rate-limit headers respected.
- No scraping of personal user data. No DM-content access. No
  aggregate-and-resell. No ad targeting. No LLM-training-data export.
- Public failure log: every draft blocked by the linter is logged with its
  reason and summarised in the quarterly research write-ups on
  https://marin-t-kael.de/research, so the policy boundary is auditable
  from the outside.

## License

MIT — see [`LICENSE`](LICENSE).

## Contact

Research enquiries: research@marin-t-kael.de
Project page: https://marin-t-kael.de/research
