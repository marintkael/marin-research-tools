// One row per provider (OpenAI, Gemini, Anthropic, …) in the latest
// snapshot. Aggregated across all the provider's LLMs.
import { getLatest, safeParse } from '../../lib/_fetch.js';

const latest = await getLatest();
const ai = latest?.field2_ki_zitations_treue?.ai_citation ?? {};
const byProvider = safeParse(ai.by_provider, {}) ?? {};

export const data = Object.entries(byProvider).map(([provider, v]) => ({
  provider,
  score: Number(v.score ?? 0),
  n: Number(v.n ?? 0),
  n_llms: Number(v.n_llms ?? 0),
  percent: Number(v.percent ?? 0),
  avg_score: Number(v.avg_score ?? 0),
  // llms is an array — JS source flattens arrays to "a,b,c" strings.
  llms_csv: Array.isArray(v.llms) ? v.llms.join(',') : '',
}));
