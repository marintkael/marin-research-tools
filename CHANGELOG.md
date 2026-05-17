# Changelog

All notable changes to this repository are documented in this file. Each
release is permanently archived on Zenodo and gets its own DOI.

## v0.3 — 2026-05-17

### Removed (design refactor)
- `reddit_comment_drafter.py` — the draft-generator for Reddit comments.
  Removed because the underlying research design has been refactored:
  **activity volume is the variable; attributes of individual outbound
  pieces (rating distribution, length, voice, tone) are operator-form and
  outside the research design.** See Methodology Note 01 v3.0 (DOI
  10.5281/zenodo.20262362) §4.1 Q4 and Q6 for the current operationalisation.

### Changed
- `pre_registrations/Q6_hardcover_reader_activity.yaml` — refactored
  `intervention.operational_form` to describe activity volume only.
  Removed enumerated attributes (rating distribution, review length,
  praise+criticism mix) which under v0.2 design were enumerated as part
  of the operational form. Under v3.0 design these are operator-form,
  not research design.
- `pre_registrations/Q6_hardcover_reader_activity.yaml` — title from
  "Hardcover Reader-Activity-Engineering" to "Hardcover
  Reader-Activity-Volume" to make the focus on volume explicit.
- `pre_registrations/Q6_hardcover_reader_activity.yaml` —
  `methodology_note_doi` updated to v3.0 (10.5281/zenodo.20262362).
- `README.md` — Q6 row in the pre-registrations table refactored;
  `reddit_comment_drafter.py` references removed; usage examples
  generalised from "Reddit draft" to outbound material.

### Deprecation note for v0.2

v0.2 (DOI 10.5281/zenodo.20189714) remains permanently citable and
preserves the design at that version of the programme. v0.2's
operationalisation of reddit comment writing and Q6 attribute-enumeration
is **superseded** by v0.3. Anyone citing v0.2 should also cite v0.3 for
the current design.

## v0.2 — 2026-05-14

- Added pre-registrations Q0–Q5 + Q6 (later).
- Added `source_attribution_parser.py`.
- DOI: 10.5281/zenodo.20189714.

## v0.1 — 2026-05-11

- Initial repository snapshot.
- DOI: 10.5281/zenodo.20126017.
