// One row per daily run (last 30 days). Drives the time-series charts on
// the Overview + LLM-detail pages.
import { getTimeseries } from '../../lib/_fetch.js';

const ts = await getTimeseries(30);
const points = Array.isArray(ts?.points) ? ts.points : [];

export const data = points.map((p) => ({
  run_id: p.id ?? null,
  run_at: p.run_at ?? null,
  score_percent: Number(p.score_percent ?? 0),
  total_llms: Number(p.total_llms ?? 0),
  primary_channel_percent: Number(p.primary_channel_percent ?? 0),
  control_channel_percent: Number(p.control_channel_percent ?? 0),
  echo_bias_inflation_pp: Number(p.echo_bias_inflation_pp ?? 0),
  stages_ok: Number(p.stages_ok ?? 0),
  stages_failed: Number(p.stages_failed ?? 0),
  duration_ms: Number(p.duration_ms ?? 0),
  triggered_by: p.triggered_by ?? null,
}));
