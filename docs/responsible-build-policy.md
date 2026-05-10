# Responsible-build policy

> Public commitments that govern how this tooling is used.
>
> Cross-reference: **https://marin-t-kael.de/research**.

This document is binding for the operator (`u/marintkael`). It restates the
commitments made in the application for API access and in the README, in one
place, so they can be linked and quoted directly.

## Identity

- One human, one Reddit account: `u/marintkael`.
- No alternate accounts, ever, for any purpose related to this tooling or
  the underlying author work.
- Contact: `research@marin-t-kael.de`.

## What the tooling does and does not do

### Does

- Reads public Reddit data (top / hot / new of subreddits the operator is
  already a participating member of).
- Produces local Markdown drafts of candidate comments for the operator to
  review.
- Runs every draft through the public style-and-policy linter in this
  repository before the operator sees it as a candidate.
- Logs every drafting decision (clean, warning, blocked) for audit.

### Does not

- Does **not** submit posts.
- Does **not** submit comments.
- Does **not** vote (upvote or downvote).
- Does **not** send direct messages.
- Does **not** send mod-mail.
- Does **not** scrape personal user profiles.
- Does **not** read or store direct-message content.
- Does **not** aggregate user data for resale, training-data export or ad
  targeting.

## Throughput

- **Daily write volume** across all platforms combined: at most 2–3 human
  contributions.
- **Daily read volume**: under 1,000 GET requests, well below any rate
  ceiling that Reddit publishes or implies.
- All rate-limit response headers are respected.
- 429 / 503 responses trigger exponential backoff.

## Technical hygiene

- **User-Agent** string follows Reddit's recommended format:
  `marin-t-kael:research-tooling:v0.1 (by /u/marintkael)`.
- **Auth scope** is the minimum required for read access.
- **No credential reuse** across machines or environments.

## Transparency

- The style-and-policy linter (`style_lint.py` in this repository) is
  public and auditable.
- Every draft that the linter blocks is logged with the reason; the public
  log is part of the research write-ups.
- Quarterly findings are published on
  [marin-t-kael.de/research](https://marin-t-kael.de/research): success
  rate, block reasons, drift patterns, anything unexpected.
- Style-sheet changes are recorded in a public changelog.

## Phase model

The drafter explicitly tracks a karma-and-age phase for the operator's
account and refuses to elevate its own phase. The phase governs whether
self-mentions are allowed at all and how often.

- **Phase 1** (warmup): no self-mentions, no own-work references, no links.
- **Phase 2** (established): light indirect mentions only when the thread
  topic genuinely calls for it. One self-mention per thread maximum, never
  a direct site link.
- **Phase 3** (post-launch): direct mentions permitted in
  topic-appropriate threads, still honouring the 9:1 spirit overall.

## Future scope

Any expansion of scope beyond the functions described in this document and
in the API access application — for example translation drafting for
international threads, AMA-preparation tooling, deeper sentiment analysis
for the quarterly write-ups — will be requested via a fresh Reddit Data API
application that describes the change. The current setup is deliberately
narrow.

## Failure mode

If the operator is asked to stand down the tooling by Reddit (formally or
informally), the operator will:

1. Disable read traffic from this account.
2. Publish the reason for the stand-down on the research page.
3. Treat the standing instruction as binding until the matter is resolved
   in writing.

The same applies for any other community surface the project participates
in.
