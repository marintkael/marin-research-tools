# marin-research-dashboard

Interactive companion to the static
[research dashboard](https://marin-t-kael.de/research/dashboard) — built
with [Evidence.dev](https://evidence.dev) so methodology reviewers can
slice, filter and drill down through the same daily measurement data,
not just look at a pre-rendered snapshot.

Live at **https://dashboard.marin-t-kael.de**.

## Data source

The dashboard pulls from the two public REST endpoints of the
`marin-research-pipeline` Worker:

- `/api/latest` — full snapshot of the most recent daily run
- `/api/timeseries?days=30` — last 30 days of run-level aggregates

Both endpoints are unauthenticated and return JSON with the exact same
shape the static dashboard already consumes. The Evidence build
re-fetches them at `npm run sources` time and writes Parquet files into
the static bundle, so query latency in the browser is local DuckDB-WASM.

## Local development

```bash
npm ci
npm run sources      # fetch the snapshot + timeseries, write Parquet
npm run dev          # http://localhost:3000
```

## Build for deploy

```bash
npm run sources
npm run build
node scripts/patch-wasm-to-cdn.mjs   # rewrite WASM URLs to jsDelivr CDN
                                     # — without this, deploy fails on
                                     # CF Pages 25 MiB per-file limit
```

## Deploy

```bash
CLOUDFLARE_API_TOKEN=$CF_TOKEN \
CLOUDFLARE_ACCOUNT_ID=3cff4d60f16032d78a178305caf97264 \
npx wrangler@3 pages deploy build --project-name=marin-dashboard --branch=main
```

The repo's `.github/workflows/dashboard-daily-rebuild.yml` does this
automatically every day at 05:00 UTC (after the pipeline cron at 04:00).

## Layout

```
pages/
├── index.md           Overview (KPI cards, provider bar, LLM bar, category bar, timeline)
├── compare.md         2-LLM slicer + delta-spread
├── timeline.md        30-day per-LLM line chart, provider/channel slicer
├── runs.md            Pipeline run history (status, duration, stage failures)
└── llm/[llm].md       Per-LLM drill-down (parametric route, one URL per LLM)

sources/marin/         Custom @evidence-dev/source-javascript tables
├── connection.yaml    type: javascript
├── by_llm.js          Today's per-LLM scores
├── by_provider.js     Today's per-provider scores
├── by_category.js     Today's per-question-category scores
├── run_meta.js        Single-row KPI for the latest run
├── timeseries.js      30-day daily run aggregates
└── llm_timeseries.js  Long-format: (day, LLM) → score over 30 days

lib/_fetch.js          Shared HTTP helper (cached per `sources` run)
scripts/patch-wasm-to-cdn.mjs   Post-build CDN-rewrite (CF Pages 25 MiB workaround)
```

## License

Same as the parent repository — MIT.
