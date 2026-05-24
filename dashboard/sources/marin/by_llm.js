// One row per LLM in the latest snapshot. Filter / slice this table to
// build per-provider / per-channel views in the dashboard pages.
import { getLatest, safeParse } from '../../lib/_fetch.js';

const latest = await getLatest();
const ai = latest?.field2_ki_zitations_treue?.ai_citation ?? {};
const byLlm = safeParse(ai.by_llm, {}) ?? {};

export const data = Object.entries(byLlm).map(([llm, v]) => ({
  llm,
  score: Number(v.score ?? 0),
  n: Number(v.n ?? 0),
  percent: Number(v.percent ?? 0),
  channel: v.channel ?? 'unknown',
  provider: v.provider ?? 'unknown',
}));
