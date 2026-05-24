// Long-format daily series: one row per (day, LLM). Built by parsing each
// run's stringified `by_llm` blob and exploding it into rows. This is the
// table Evidence pivots on for the LLM-comparison Line-Chart on the
// Overview page and the per-LLM Drill-Down page.
import { getTimeseries, safeParse } from '../../lib/_fetch.js';

const ts = await getTimeseries(30);
const points = Array.isArray(ts?.points) ? ts.points : [];

const rows = [];
for (const p of points) {
  const byLlm = safeParse(p.by_llm, {}) ?? {};
  for (const [llm, v] of Object.entries(byLlm)) {
    rows.push({
      run_at: p.run_at ?? null,
      llm,
      provider: v.provider ?? 'unknown',
      channel: v.channel ?? 'unknown',
      score: Number(v.score ?? 0),
      n: Number(v.n ?? 0),
      percent: Number(v.percent ?? 0),
    });
  }
}

export const data = rows;
