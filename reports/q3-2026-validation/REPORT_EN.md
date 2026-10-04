# Validation Report Q3 / 2026

## How reliably does the programme measure? A test of the six instrument hypotheses of pre-registration Q0-INST, measurement window 11 May to 30 September 2026

*Marin T. Kael · Validation Report Q3 / 2026 · data state 1 October 2026*

### Summary

This report tests the six instrument hypotheses of pre-registration Q0-INST of 11 May 2026 against the frozen data state of 1 October 2026. None is confirmed. Three cannot be tested because the planned data collection did not take place; three are not confirmed.

The same question receives the same score on the next measurement day in 86.6 percent of pairs for OpenAI Search, 87.1 for Gemini and 94.3 percent for Claude (claude.ai with web search). Without the questions whose score never changes, the figures are 78.6, 70.6 and 85.0 percent. The correlation of two single measurements one day apart is 0.746, 0.612 and 0.811. The question set does not form a single scale: Cronbach's α ranges from 0.407 (Gemini, 95 percent interval 0.279 to 0.5) to 0.61 (Claude, 0.562 to 0.651), and depending on the provider 6 to 10 of the 16 questions have no variance.

Against the May reference the CUSUM chart raises only upward alarms (19, 30 and 44). With the reference reset after each alarm, five downward alarms appear (OpenAI 27 August and 30 September, Gemini 14 August, Claude 17 August and 19 September); none is explained by a documented event.

The Wikidata items named as anchors in Q0-INST were deleted during the window. The Google Knowledge Graph finds the author on 140 of 141 days and the book on none of 139. Gemini measured 102 of 113 scheduled days completely, OpenAI 53 of 113, Claude 55 of 106; for Claude 17 days are missing without a register entry. Three sub-studies (Q0-KG, Q3, Q4) have passed their pre-registered end of data collection and are still marked "active".

---

### 1. Research question and pre-registration

The programme studies when and how AI answer engines find and cite a new author. The first phase tests the measurement instruments; effect statements follow in the second phase, starting with the release of the first volume on 8 October 2026.

Pre-registration Q0-INST (DOI 10.5281/zenodo.20125967, version 1.0; listed as "Q0" until October 2026) fixes an observation window from 11 May to 22 September 2026 and six hypotheses: test-retest reliability of the API surfaces (INST-01), the gain from multiple snapshots for language-model probes (INST-02), detection of model updates by CUSUM (INST-03), internal consistency (INST-04), stability of Wikidata as an anchor (INST-05) and agreement of Wikidata and the Knowledge Graph (INST-06). The thresholds are listed in Table 1. Deviations from the plan are permitted if reported openly; they are set out in Sections 4 and 10.

### 2. Data and measurement window

The basis is an extract of the measurement database of 1 October 2026 for the window 11 May to 30 September 2026: 11,532 answer rows from OpenAI Search and Gemini and 4,047 answer rows from the Claude model tiers Haiku, Sonnet and Opus on claude.ai with web search. Snapshots of the anchor surfaces (Wikidata, Knowledge Graph, Bing, Search Console) up to 30 September were frozen separately on 4 October.

Each provider answers the same 16 questions: three name the author or the work (Direct), two name terms from the work (Saga knowledge), one the research programme, ten neither author nor work. Scoring is rule-based from minus three to plus three. Measurement was daily until 18 August and every third day from 19 August (15 anchor days up to 30 September). Measurements on in-between days (OpenAI 21, Gemini 27, Claude 6) enter the analysis but do not count as scheduled days.

Exactly one answer counts per day, provider unit and question, under the programme rule in force since 4 September 2026 (gap register, entry 11): an error row always loses; among the remaining rows the answer whose timestamp is closest to the scheduled run time wins; ties go to the earlier one. The scheduled run time is the start of the regular daily run for OpenAI and Gemini and the time of the first measurement run of the day for Claude. Under this rule 7,118 cells with a value remain (OpenAI 1,637, Gemini 2,192, Claude 3,289); there are 597, 42 and 288 error cells.

The gap register has 21 entries touching the window; outages mainly affect OpenAI (exhausted quota of the measurement account, most recently 18 to 27 September) and Claude (failed measurement runs in July, late August and September).

### 3. Methods

Coverage: scheduled days are all days from a provider's first measurement day to 18 August, then the anchor days; complete means all 16 questions per model tier have a value. Test-retest agreement: share of identical scores for the same question and model tier on the next measurement day, plus the Pearson correlation for pairs one calendar day apart, raw and after subtracting each question's mean, with a bootstrap interval over day pairs. Daily value: score sum divided by the maximum over 16 questions, for Claude averaged over three tiers, complete days only (OpenAI 72, Gemini 129, Claude 73).

CUSUM: tabular chart with k = 0.5 and h = 5 standard deviations in three variants, with a reference from the first 10 measurement days (May reference), with rebasing after each alarm from the following 10 measurement days, and with a rolling reference from the last 30 calendar days, as specified in Q0-INST.

Alarm check: for each downward alarm of the rebasing variant, the shift between the end of the reference and the alarm day is decomposed by question. The register entries are coded for whether they can shift the level and in which direction; changes of model labels in the answer rows count as separate events. An alarm counts as explained if such an event starts before the alarm day, concerns the two questions with the largest contribution and does not imply the opposite direction.

Cronbach's α is computed across 16 questions (case = measurement day × model tier), Wikidata coverage as the share of the first snapshot's properties, κ on the binary hit classification for author and book. Bootstrap intervals use 2,000 draws; all figures come from a single analysis file.

### 4. Results by hypothesis

*Table 1 · Instrument hypotheses of pre-registration Q0-INST and result with the data state of 1 October 2026.*

| Hypothesis | Pre-registered | Result | Reason |
|---|---|---|---|
| H-Q0-INST-01 | r ≥ 0.9 for API surfaces, 24-h repeat probes | not testable | repeat probes not collected; Bing without status from August; Search Console index field registered as dead |
| H-Q0-INST-02 | r ≥ 0.7 with five snapshots and median | not testable | multiple snapshots not collected; single measurement r = 0.746 (OpenAI), 0.612 (Gemini) |
| H-Q0-INST-03 | CUSUM detects a model update | not testable | no version field for OpenAI and Gemini; Bing AI and AI Overviews not measured |
| H-Q0-INST-04 | α ≥ 0.7 (API), 0.5 to below 0.7 (AI) | not confirmed | API part not testable; Gemini with α = 0.407 below the band |
| H-Q0-INST-05 | Wikidata coverage > 0.85, stable | not confirmed | both registered anchor items deleted within the window |
| H-Q0-INST-06 | κ ≥ 0.8 Wikidata – Knowledge Graph | not confirmed | κ = 0.0 |

H-Q0-INST-01. The repeat probes 24 hours after the regular measurement on 14 randomly chosen days were not collected. Next-day comparisons do not replace the retest, but they show how quiet the API surfaces are: the Knowledge Graph returns the same hit pattern for the author name on 99.3 percent of consecutive days, and the Wikidata successor items have the same number of statements on 98.3 percent. Bing returned an index status on 30 of 30 days in June, on none of 31 in August and on one of 30 in September.

H-Q0-INST-02. Only the single measurement can be computed. For pairs one day apart the correlation is 0.746 for OpenAI (0.695 to 0.795, 1,416 pairs), 0.612 for Gemini (0.558 to 0.665, 2,125 pairs) and 0.811 for Claude (0.753 to 0.869, 2,301 pairs). OpenAI reaches the 0.7 threshold without aggregation, Gemini does not. Much of the correlation comes from differences between questions; after subtracting each question's mean, 0.326 (OpenAI), 0.367 (Gemini) and 0.759 (Claude) remain.

H-Q0-INST-03. The rolling chart specified in Q0-INST raises 2 upward alarms and 1 downward alarm for OpenAI, 4 and 1 for Gemini, 4 and 1 for Claude. For OpenAI and Gemini the answer rows carry no version field, and Bing AI and Google AI Overviews were not measured; for the registered surfaces the hypothesis is therefore not testable. For Claude, which Q0-INST did not name but which is the only surface with a version field, the labels of two model tiers change between 21 June and 2 July, and the rolling chart raises an upward alarm on 2 July (daily value 12.5 percent against a reference mean of −1.8 percent). A measurement pause without a register entry lies in between; model change and pause cannot be separated as causes.

H-Q0-INST-04. There is no question set for API surfaces. Among the AI surfaces, OpenAI (0.553) and Claude (0.61) lie within the pre-registered band, Gemini (0.407) below it (Section 5).

H-Q0-INST-05. Q0-INST and the Wikidata baseline dataset name the items Q139720807 (author) and Q139720798 (book) as anchors. Both were deleted during the window; the measurement recorded the deletion on 25 June, and no earlier snapshots of the two items exist. The successor items Q140004504 and Q140004740 are present on all 121 days since 2 June, with a coverage of 1.0 without fluctuation and 14 to 16 and 11 to 13 statements respectively. The registered anchor did not last through the window, and the successors do not cover its first three weeks.

H-Q0-INST-06. On 242 day pairs for author and book, observed and expected agreement are 0.5 and κ is 0.0 (Figure 1). Wikidata lists author and book on every day; the Knowledge Graph finds the author name on 140 of 141 days, first on 14 May, and the book and the series on none of 139 days. Because Wikidata shows a hit on every day, κ is structurally zero here. The surfaces are not redundant: the Knowledge Graph lists the person and not the work.

[[FIG1]]

The planned Benjamini-Hochberg correction does not apply because none of the six tests produces a p-value; all are threshold comparisons.

### 5. Test-retest agreement and internal consistency

[[FIG2]]

The questions naming neither author nor work mostly reach 100 percent agreement, because the author is never named there and every answer receives the same score (Figure 2). The lowest values are in the Direct questions: the question about the person keeps its score in 43.8 percent of pairs for Gemini, 45.7 for OpenAI and 73.8 percent for Claude.

[[FIG3]]

The same pattern governs internal consistency. For Gemini 9 of the 16 questions have no variance across 129 cases, for Claude 10 across 195 cases, for OpenAI 6 across 72 cases; such questions contribute nothing to α. Within categories only the Direct group for Claude exceeds 0.7 (α = 0.784 across 3 questions); for OpenAI it is 0.292, for Gemini 0.357. A sum score across all 16 questions is therefore not supported as a scale; the categories have to be analysed separately.

### 6. Coverage and outages

[[FIG4]]

*Table 2 · Scheduled and valid measurement days by provider, 11 May to 30 September 2026.*

| Provider | Scheduled days | complete | partial | errors only | no run | missing, with register entry | missing, without register entry |
|---|---|---|---|---|---|---|---|
| OpenAI Search | 113 | 53 (46.9 %) | 41 | 19 | 0 | 18 | 1 |
| Gemini | 113 | 102 (90.3 %) | 10 | 1 | 0 | 0 | 1 |
| Claude (claude.ai) | 106 | 55 (51.9 %) | 12 | 5 | 34 | 22 | 17 |

Only Gemini measured all 15 anchor days completely; OpenAI reaches 11, Claude 10. For OpenAI, 18 of the 19 days without a value go back to exhausted quotas. Claude is missing 39 scheduled days, 17 of them without a register entry, including ten days without a measurement run from 22 June to 1 July; their cause can no longer be established.

### 7. Drift

[[FIG5]]

Against the reference of the first ten measurement days in May (mean 5.73 percent for OpenAI, 2.08 for Gemini, −9.98 for Claude), the chart raises only upward alarms: from 11 June to 17 September for OpenAI, from 19 June to 29 September for Gemini, from 7 June to 30 September for Claude. This corresponds to the rise in visibility described in Report 03; against this reference the chart does not show further shifts. The rebasing variant shows two upward steps per provider in June and July, followed by five downward alarms in total (Table 3).

*Table 3 · Downward alarms of the rebasing variant, decomposition by question and check against the gap register. pp = percentage points of the daily value.*

| Provider, alarm day | Reference (mean, SD) | Test interval (days, mean) | Largest contributions | Events in the interval | Result |
|---|---|---|---|---|---|
| OpenAI, 27 Aug | 20 Jul–16 Aug (25.21; 3.32) | 17–27 Aug (9; 22.91) | D1 −1.04 pp, L2 −0.65 pp | outage 18 Aug, cadence change 19 Aug, third-party list entry on the alarm day, dedupe | unexplained |
| OpenAI, 30 Sep | 28 Aug–7 Sep (25.62; 3.26) | 8–30 Sep (12; 24.04) | L2 −1.7 pp, GR6 −0.83 pp | outage 18–27 Sep, release date moved (concerns D3) | unexplained |
| Gemini, 14 Aug | 12–21 Jul (20.94; 4.92) | 22 Jul–14 Aug (19; 18.09) | D2 −1.12 pp, GR6 −0.89 pp | dedupe rule | unexplained |
| Claude, 17 Aug | 3–31 Jul (16.74; 2.77) | 1–17 Aug (15; 14.72) | L1 −1.99 pp, D1 −0.9 pp | none | unexplained |
| Claude, 19 Sep | 18 Aug–4 Sep (14.86; 2.06) | 5–19 Sep (4; 10.85) | D1 −1.67 pp, D2 −1.56 pp | throttling 12 Sep, release date moved (concerns D3), catch-up measurement 19 Sep | unexplained |

Outages change the number of measurement days, not the level; changes of cadence and dedupe do not affect the daily series of this analysis. The third-party list entry falls on the alarm day itself and would imply a rise; the release date change of 15 September concerns only the date question D3. The interval mean lies 1.58 to 4.01 percentage points below the reference mean; for OpenAI on 27 August and Claude on 17 August, 2.3 and 2.02 percentage points suffice because the reference periods were unusually quiet (standard deviation 3.32 and 2.77).

The Claude alarm on 19 September is the clearest: the daily value falls to −2.08 percent after lying between 9 and 19 percent since July, carried by the questions about the person and the book (D1, D2). A review of the answer texts shows that web search on these days finds no page about the author; the models name a well-known namesake or report finding nothing, and the scheme rates part of these answers as hallucination (minus three). The decline therefore has two components: a change in the search result of unknown cause and a scoring rule that does not separate not-found from confusion.

The rolling chart specified in Q0-INST raises downward alarms on the same day as the rebasing variant for Claude (19 September) and OpenAI (30 September), and one day later for Gemini (15 August).

### 8. Status of sub-studies Q0-KG to Q6

*Table 4 · Pre-registrations in the repository, frozen version of 4 October 2026.*

| Study | Subject | Data collection as registered | Status in the file | End passed |
|---|---|---|---|---|
| Q0-KG | Wikidata → Knowledge Graph latency | 11 May–22 Sep 2026 | active | yes |
| Q1 | Wikidata co-occurrence | 14 May–31 Dec 2026 | registered | no |
| Q2 | Inclusion in Common Crawl | 13 May–31 Dec 2026 | active | no |
| Q3 | Drift of the cross-provider source graph | 14 May–14 Aug 2026 | active | yes |
| Q4 | Reddit mentions | 11 May–9 Aug 2026 | active | yes |
| Q5 | DOI cadence and Wikipedia notability | 11 May 2026–30 Sep 2027 | registered | no |
| Q6 | Reader activity on Hardcover | from 14 May 2026, no end | active | – |

Q4 (since 9 August), Q3 (since 14 August) and Q0-KG (since 22 September) have passed their end of data collection without the file recording a closure or an extension; a new version is outstanding for all three. Q6 has neither an end date nor a stopping rule.

The names Q0-INST (Zenodo pre-registration) and Q0-KG (sub-study in the repository) follow the naming note in the repository README of October 2026.

### 9. Consequences for phase 2

For the book launch on 8 October 2026 the re-dated time grid from the addendum to Report 03 applies: baseline 8 September to 7 October, effect window 8 October to 7 November.

The daily values per provider at question level, especially the Direct questions, can carry effect statements: they have variance and can be decomposed by question. Effect statements should be made per provider and question group and attributed to an intervention only if the shift appears at more than one provider. Shifts of the interval mean by 1.58 to 4.01 percentage points occurred in this window without a documented cause; effects of this size cannot be separated from instrument drift.

The recommendation questions and the Knowledge Graph entry for the book have so far stayed at zero; they can carry statements about a first appearance but lack the variance for gradual statements.

Not suitable are a sum score across all 16 questions as a scale (α below 0.7 for all providers), a headline figure across providers on days when one is missing (change of basis), the CUSUM chart against a reference preceding a known level change, Bing and the Search Console index field, and statements about model updates at OpenAI and Gemini as long as the answer rows carry no version field.

Four tasks follow for the measurement: collect the repeat probes specified in Q0-INST; store the model and version field with every answer; review the scoring rule for answers that state not-found while naming a namesake and publish the result as a new codebook version; secure the quota of the OpenAI measurement account so that the effect window has no gaps.

Since 4 October 2026 the control channel via the Claude API (models without web search) has been discontinued (gap register, entry 25). It never entered the headline figure and had returned no answers since 15 September; Claude is measured only through claude.ai with web search. Also since 4 October, measurement takes place only on anchor days. The unscheduled in-between-day measurements of OpenAI and Gemini since 20 August remain in the dataset, marked as such; the corresponding register entry postdates the data state of this report and changes no figure.

### 10. Limitations

At the level of the author the study has n equal to one. For the three untestable hypotheses, the result says nothing about the properties of the instruments. Test-retest agreement does not separate real change from measurement noise. The coding of the gap register by level effect was fixed before the formal check but with knowledge of the alarm days, and it was not reviewed independently. The scheduled days for Claude before 22 July assume daily measurement, which was not automated at the time. Cronbach's α was computed over 16 single questions instead of 12 question sets, and the CUSUM chart on the daily value instead of a hit rate. The review of answer texts for the Claude alarm of 19 September is a sample, not a systematic re-scoring. All questions but one are in German.

### 11. Reproducibility

Sub-studies Q0-KG to Q6 are in the public repository github.com/marintkael/marin-research-tools in the folder pre_registrations; the instrument hypotheses are in pre-registration Q0-INST under DOI 10.5281/zenodo.20125967. The analysis code, frozen data, event coding and figure builds of this report are not yet in the repository; the code will be published with the replication archive. It contains the extracts of 1 and 4 October 2026 with query text and checksum, the event coding and the analysis with a fixed bootstrap seed.

### 12. How to cite

Kael, M. T. (2026). Validation Report Q3 / 2026: A test of the instrument hypotheses of pre-registration Q0-INST, measurement window 11 May to 30 September 2026. Marin T. Kael Research Programme. doi:10.5281/zenodo.23145378

---

*Figures: 1 Anchor surfaces Wikidata and Knowledge Graph · 2 Test-retest agreement by question · 3 Internal consistency of the question set · 4 Coverage by provider · 5 Daily value by provider with CUSUM alarms.*
