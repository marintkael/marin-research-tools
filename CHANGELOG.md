# Changelog

All notable changes to this repository are documented in this file. Each
release is permanently archived on Zenodo and gets its own DOI.

## v0.5 — 2026-05-24

### Changed (scope tightening)
- `style_lint.py` — scope tightened to a manuscript style-consistency
  linter for *Prägungen des Reiches*. The public release now focuses
  exclusively on canon-contradiction detection (protagonist name,
  world-mechanic definition), umlaut-encoding drift in German text, and
  the saga title spelling. The platform-specific helper logic that lived
  alongside the canon rules has been factored out of the public release
  because it is not what external methodology reviewers replicate and the
  scope was confusing.
- `README.md` — section on what the repository contains updated to reflect
  the tightened scope; usage examples simplified accordingly.

### Removed
- `docs/responsible-build-policy.md` and the `policies/` directory —
  superseded. The author-account commitments survive as a section in
  `README.md`; the rest belonged to internal authoring practice rather
  than to the public methodology and has been moved out of the public
  repository.

## v0.4.5 — 2026-05-24

### Changed
- `research-harness/push_snapshot_to_d1.py` — guard added: if the snapshot
  has 0 result rows (because every LLM upstream failed during the run, e.g.
  a shared OpenAI rate-limit hit + a transient Gemini 503), the push step
  is now a no-op (`exit 0` with a clear log message). Previously the worker
  returned HTTP 500 on empty payloads, which surfaced as a CI red even
  though the harness itself ran fine. Eliminates spurious red runs on days
  where upstream APIs are temporarily unreachable. The next scheduled run
  retries cleanly.

## v0.4.4 — 2026-05-24

### Changed
- `.github/workflows/marin-eval-daily.yml` — moved from
  `research-harness/.github/workflows/` to the repository root, which is
  where GitHub Actions actually looks for workflow files. The previous
  location was silently ignored: 0 scheduled runs since v0.4. After this
  move the workflow registers and runs at the configured 04:30 UTC cron
  (plus on-demand via `workflow_dispatch`).

## v0.4.3 — 2026-05-24

### Changed
- `research-harness/marin_tasks/marin_research_v1.yaml` — `methodology_doi`
  pointer updated from the v3.0 Methodology Note (`10.5281/zenodo.20308495`,
  now retained as `methodology_doi_prev`) to the new v4.0 Methodology Note
  (`10.5281/zenodo.20364173`). Added `software_doi` (`10.5281/zenodo.20364157`)
  for v0.4.2 cross-reference. Pure pointer update — no methodology change.
- `research-harness/METHODOLOGY_NOTE_v4.0.md` — header now lists the v4.0
  Amendment DOI and the v0.4.2 software DOI.
- `research-harness/README.md` — Methodology section updated to reference
  the v4.0 Methodology Note DOI as the current Amendment and the v0.4.2
  software DOI for the implementation.

### Note on v0.4.2

v0.4.2 (DOI 10.5281/zenodo.20364157) carries an internal YAML pointer to
the v3.0 Methodology Note because the v4.0 Note DOI did not yet exist at
its publication moment. That snapshot is historically correct and remains
permanently citable; v0.4.3+ point to the v4.0 Note DOI.

## v0.4.2 — 2026-05-24

### Changed
- `style_lint.py` — module docstring clarified. Behaviour, rules,
  and patterns are unchanged.

### Zenodo
- Published as DOI `10.5281/zenodo.20364157` (new version of the v0.4
  concept; supersedes `10.5281/zenodo.20360519`).

## v0.4.1 — 2026-05-24

### Changed (housekeeping)
- `research-harness/README.md`, `research-harness/METHODOLOGY_NOTE_v4.0.md`,
  `research-harness/marin_models/claude_web_importer.py`,
  `research-harness/.github/workflows/marin-eval-daily.yml` — descriptive
  text simplified to remove internal toolchain names that are not part of
  the public methodology. Behaviour is unchanged; the harness still reads
  the same `/tmp/marin_sweep/{QID}_{TIER}.json` files for the claude_web
  importer.
- `research-harness/run_all_models.py`,
  `research-harness/push_snapshot_to_d1.py` — `.env` loader generalised
  to search `cwd / file-dir / file-parent-dir / ~/.marin-research/` plus
  an optional `MARIN_ENV_FILE` env-var. Previously a single hardcoded
  developer-machine path was the first candidate; the new layout works
  unchanged on any researcher's machine.

### Note for v0.4

v0.4 (DOI 10.5281/zenodo.20360519) is the same toolchain and produces
the same scores; v0.4.1 only cleans up presentation. Cite v0.4.1 for any
new replication work.

## v0.4 — 2026-05-23

### Added (infrastructure migration)
- `research-harness/` — full migration of the operational score-algorithm
  from in-Worker JavaScript (v3.0.3) to a standalone Python package on
  top of [EleutherAI lm-evaluation-harness v0.4.12](https://github.com/EleutherAI/lm-evaluation-harness).
- `research-harness/marin_tasks/marin_research_v1.yaml` — task config
  (locked), 16 anchor questions × 6 categories, score scale -3..+3.
- `research-harness/marin_tasks/utils.py` — score functions
  (`MARIN_SPECIFIC`, `KEY_FACTS`, `NEGATIVE_HALLU` patterns) ported 1:1
  from the legacy worker code. 27/27 historical datapoints match
  byte-identical between legacy v3.0 and v4.0 scoring.
- `research-harness/marin_models/` — three custom adapters:
  `openai_search_preview` (with 3-retry exponential backoff for the
  account-level rate-limit), `gemini_grounded` (Google-Search-Tool), and
  `claude_web_importer` (replays manual claude.ai web-sweep JSONs).
- `research-harness/.github/workflows/marin-eval-daily.yml` — daily CI
  cron at 04:30 UTC, runs API LLMs and pushes a snapshot to D1.
- `research-harness/METHODOLOGY_NOTE_v4.0.md` — Amendment to the
  Pre-Registration DOI 10.5281/zenodo.20125967 documenting the
  infrastructure migration and the change-discipline (patch / minor /
  major) protocol going forward.

### Why this matters

v3.0 was tied to the operational Cloudflare Workers stack — score
changes required a deploy, reproducibility required runtime access to
the worker. v4.0 makes the methodology a standalone Python artifact
that any external researcher can replicate on their laptop in under
five minutes.

## v0.3 — 2026-05-17

### Removed (design refactor)
- An auxiliary helper script has been removed from the public release
  because the underlying research design has been refactored:
  **activity volume is the variable; attributes of individual public-write
  events (rating distribution, length, voice, tone) are author-form and
  outside the research design.** See Methodology Note 01 v3.0 (DOI
  10.5281/zenodo.20262362) §4.1 Q4 and Q6 for the current operationalisation.

### Changed
- `pre_registrations/Q6_hardcover_reader_activity.yaml` — refactored
  `intervention.operational_form` to describe activity volume only.
  Removed enumerated attributes (rating distribution, review length,
  praise+criticism mix) which under v0.2 design were enumerated as part
  of the operational form. Under v3.0 design these are author-form,
  not research design.
- `pre_registrations/Q6_hardcover_reader_activity.yaml` — title from
  "Hardcover Reader-Activity-Engineering" to "Hardcover
  Reader-Activity-Volume" to make the focus on volume explicit.
- `pre_registrations/Q6_hardcover_reader_activity.yaml` —
  `methodology_note_doi` updated to v3.0 (10.5281/zenodo.20262362).
- `README.md` — Q6 row in the pre-registrations table refactored;
  usage examples generalised accordingly.

### Deprecation note for v0.2

v0.2 (DOI 10.5281/zenodo.20189714) remains permanently citable and
preserves the design at that version of the programme. v0.2's
operationalisation and Q6 attribute-enumeration is **superseded**
by v0.3. Anyone citing v0.2 should also cite v0.3 for the current
design.

## v0.2 — 2026-05-14

- Added pre-registrations Q0–Q5 + Q6 (later).
- Added `source_attribution_parser.py`.
- DOI: 10.5281/zenodo.20189714.

## v0.1 — 2026-05-11

- Initial repository snapshot.
- DOI: 10.5281/zenodo.20126017.
