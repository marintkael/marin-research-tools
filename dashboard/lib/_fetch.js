// Shared fetch helpers for all marin source tables. Each table file imports
// the cached snapshot via `getLatest()` / `getTimeseries(days)`, both of
// which hit the public marin-research-pipeline endpoints exactly once per
// `evidence sources` run (module-level memoisation).
//
// Endpoints:
//   /api/latest                 → snapshot of the most recent daily run
//   /api/timeseries?days=N      → array of up to N daily runs
//
// Both endpoints are public (no auth) and return the same JSON shape the
// Astro SSR dashboard already consumes — single source of truth.

const PIPELINE_BASE =
  process.env.EVIDENCE_PIPELINE_BASE ||
  'https://marin-research-pipeline.p96xckbr4c.workers.dev';

let _latest = null;
let _timeseries = null;

export async function getLatest() {
  if (_latest) return _latest;
  const r = await fetch(`${PIPELINE_BASE}/api/latest`);
  if (!r.ok) throw new Error(`/api/latest HTTP ${r.status}`);
  _latest = await r.json();
  return _latest;
}

export async function getTimeseries(days = 30) {
  if (_timeseries) return _timeseries;
  const r = await fetch(`${PIPELINE_BASE}/api/timeseries?days=${days}`);
  if (!r.ok) throw new Error(`/api/timeseries HTTP ${r.status}`);
  _timeseries = await r.json();
  return _timeseries;
}

// The score / by_* fields are JSON-stringified in D1 to keep schema flat.
// Wrap JSON.parse so a single bad row doesn't blow up the whole build.
export function safeParse(s, fallback = null) {
  if (!s || typeof s !== 'string') return s ?? fallback;
  try {
    return JSON.parse(s);
  } catch {
    return fallback;
  }
}
