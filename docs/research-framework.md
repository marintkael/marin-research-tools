# Research framework

> A public companion to **https://marin-t-kael.de/research**.

This document describes the four observation fields of the research project
that surrounds *Prägungen des Reiches* (opening volume *Das vierte Feld*,
scheduled for 2026-09-22). Quarterly findings are published on the research
page; this file gives a stable reference to what those findings observe and
why.

The framework is honest about its constraints: the operator is a single
author, the n-of-1 is real, the findings are observations rather than
controlled experiments. The value is in the documentation discipline and the
public auditability, not in statistical power.

## Field 1 — Knowledge graph synchronisation

*Question.* How do structured statements about a literary work propagate
through public knowledge graphs, search engines and AI training corpora over
time?

*What is observed.* The route from a canonical statement (e.g. a Wikidata
entity, a structured-data block on the author website) to the answer
surface (a search engine knowledge panel, a chat assistant) is rarely
direct. There is latency. There is loss. Sometimes there is drift —
intermediate systems summarise away an important fact. The project tracks
which canonical sources are read, in which order, with what fidelity, and
how long it takes for a corrected fact to reach the answer layer.

*Why it matters.* Authors increasingly compete in answer surfaces before
they compete in physical bookstores. Understanding how a canon-statement
about one's own work survives the trip from origin to reader-facing answer
is part of the craft.

## Field 2 — AI citation fidelity

*Question.* When language models are asked directly about the work, what do
they know, what do they hallucinate, and what self-corrects over months?

*What is observed.* A small daily measurement: a fixed set of factual
questions about the work is put to a rotating set of language model
endpoints. The answers are scored against the public canon (title, author,
publication date, protagonist name, central premise). Hallucination
patterns, factual drift and self-correction over time are recorded.

*Why it matters.* Author-public-fact accuracy in AI assistants is becoming
the primary discoverability layer for new readers. Documenting what works
and what does not is useful both for the operator's own publication
strategy and for other authors operating in the same surface.

## Field 3 — Reader-community participation

*Question.* Can an author with AI-assisted preparation contribute
substantively to genre conversations without degrading the discourse?

*What is observed.* Each contribution that the operator submits to a
community surface (Reddit, Hardcover, Goodreads) carries metadata:
preparation pipeline, whether the draft was AI-assisted, whether it passed
the public linter, how it was received (score, replies, follow-ups,
reports). The findings page summarises block-rates, acceptance rates and
qualitative reader reactions per community.

*Why it matters.* The hardest question in AI-augmented authorship is not
"can it be done", it is "can it be done without making the discourse
worse". The framework treats this as a question to be answered with data,
not assumed.

## Field 4 — Voice consistency under tooling

*Question.* When outbound communication runs through pipelines, how is
voice held stable, and which drift patterns recur?

*What is observed.* Every outbound draft is scored against a published
style sheet that defines the author voice (the same style sheet used by the
linter in this repository). Drift patterns are categorised and counted over
time. Where drift recurs, the style sheet itself is updated and the change
is recorded.

*Why it matters.* The single most common failure mode of AI-assisted
authorship is voice degradation: drafts converge on a model's house style
instead of the author's. The framework treats voice as something that has
to be actively defended, measured and rebuilt — not just hoped for.

## Cadence

- **Quarterly write-ups** on the research page.
- **Public failure log** updated whenever the linter blocks a draft.
- **Style-sheet changelog** updated whenever a drift pattern earns a
  permanent rule.
