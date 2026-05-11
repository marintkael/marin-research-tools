# Research framework

> A public companion to **https://marin-t-kael.de/research**.

This document describes the four Phase-1 investigation lines of the Marin
T. Kael Research Programme — KI-Zitations-Feldlabor (AI Citation Behavior
Lab) — which surrounds *Prägungen des Reiches* (opening volume *Das vierte
Feld*, scheduled for 22 September 2026). The programme is an open field
laboratory observing how language-model-based search systems, AI answer
engines and knowledge graphs ingest, understand and cite an author
identity.

The framework is honest about its constraints: the observed unit is a
single author identity, the design is n-of-1, the findings are observations
rather than controlled experiments. The value is in the documentation
discipline and the public auditability, not in statistical generalisation.

## Two phases

**Phase 1 (May 2026 → Q3 / 2027) — Measurement-instrument validation.**
Eight measurement surfaces are sampled daily, and their measurement
properties (test-retest reliability, intra-set consistency, CUSUM drift
across model updates, coverage per identity cluster) are quantified. A
public codebook (v0.x → v1.0) operationalises what counts as a 'correct
citation'.

**Phase 2 (from Q3 / 2027 onward) — Pre-registered action-effect studies**
on the then-validated apparatus. Effect measures appropriate for an n-of-1
design (Interrupted Time Series, Bayesian Structural Time Series,
hierarchical Bayes), not pre/post Cohen's d on single actions.

## Line 1 — Citation inventory

*Question.* What does each measurement surface currently show of the
defined author identity, per identity cluster (person, work, genre,
world-mechanic)?

*What is observed.* Eight surfaces are sampled daily — Wikidata, Google
Knowledge Graph, Bing Webmaster KI, Google Search Console, Google AI
Overviews, Goodreads / Hardcover, Reddit, and language-model browser
probes (Gemini, ChatGPT). For each surface × query-set × day, hit-rate H
= correct citations / queries is recorded.

In Phase 1 this is descriptive only — no effect interpretation.

## Line 2 — Measurement-instrument validation

*Question.* How reliable is each surface, what is its drift characteristic
under model updates, which surfaces are redundant?

*What is observed.* Test-retest correlation r over 24-hour repeat probes,
Cronbach's alpha intra-query-set, CUSUM control charts on hit-rate against
rolling baseline (alarm threshold h = 5), model-version snapshots logged
separately. Thresholds for Phase-2 admission: r >= 0.9 for API-based
surfaces; r >= 0.7 for language-model browser probes (with multi-snapshot
median aggregation).

## Line 3 — Codebook iteration

*Question.* What operationalisation of 'correct citation' is robust against
edge cases, surface differences and language-model style drift?

*What is observed.* Versioned annotation schema (v0.x → v1.0) with
documented edge-cases. From Q4 / 2026, inter-rater agreement (Cohen's
kappa) with external annotators is collected; threshold kappa >= 0.7 per
dimension is the condition for v1.0 release and Phase-2 admission.

## Line 4 — Open materials

*Question.* Are all findings externally auditable and reproducible for
other author identities?

*What is observed.* Methods notes, pre-registrations, measurement code,
raw data, quarterly reports, failure logs and codebook versions are all
released openly, with DOIs from Q3 / 2026 onward. Quarterly replication
archives contain frozen version pins via `environment.yml`, user-agent
strings and endpoint snapshots.

## Cadence

- **Quarterly validation reports** (Mid October, January, April; tolerance
  ±2 weeks) on the research page and on Zenodo with DOI.
- **Public failure log** updated whenever the linter blocks a draft.
- **Codebook changelog** updated whenever inter-rater results require a
  schema revision.

## Cite this framework

If you use this framework in a methods comparison or replication,
please cite:

- **Methodology Note 01** — DOI:
  [10.5281/zenodo.20125934](https://doi.org/10.5281/zenodo.20125934)
- **Vor-Registrierung Q0** — DOI:
  [10.5281/zenodo.20125967](https://doi.org/10.5281/zenodo.20125967)
- **Codebuch v0.1** — DOI:
  [10.5281/zenodo.20125976](https://doi.org/10.5281/zenodo.20125976)
