// One-row table: KPIs for the most recent run. Backs the Overview-page
// header cards (total score, primary/control channel %, echo-bias inflation,
// LLM count, datapoint count).
import { getLatest } from '../../lib/_fetch.js';

const latest = await getLatest();
const run = latest?.run ?? {};
const ai = latest?.field2_ki_zitations_treue?.ai_citation ?? {};

export const data = [
  {
    run_id: run.id ?? null,
    run_at: run.run_at ?? null,
    triggered_by: run.triggered_by ?? null,
    duration_ms: Number(run.duration_ms ?? 0),
    stages_ok: Number(run.stages_ok ?? 0),
    stages_failed: Number(run.stages_failed ?? 0),
    score_percent: Number(ai.score_percent ?? 0),
    total_llms: Number(ai.total_llms ?? 0),
    total_questions: Number(ai.total_questions ?? 0),
    total_datapoints: Number(ai.total_datapoints ?? 0),
    total_score: Number(ai.total_score ?? 0),
    primary_channel_percent: Number(ai.primary_channel_percent ?? 0),
    primary_channel_datapoints: Number(ai.primary_channel_datapoints ?? 0),
    control_channel_percent: Number(ai.control_channel_percent ?? 0),
    control_channel_datapoints: Number(ai.control_channel_datapoints ?? 0),
    echo_bias_inflation_pp: Number(ai.echo_bias_inflation_pp ?? 0),
  },
];
