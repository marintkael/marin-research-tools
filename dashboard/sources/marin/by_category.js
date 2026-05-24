// One row per question category (Direct, Genre, LongTail, CompCluster,
// GenreRecommend, Research) in the latest snapshot.
import { getLatest, safeParse } from '../../lib/_fetch.js';

const latest = await getLatest();
const ai = latest?.field2_ki_zitations_treue?.ai_citation ?? {};
const byCategory = safeParse(ai.by_category, {}) ?? {};

export const data = Object.entries(byCategory).map(([category, v]) => ({
  category,
  score: Number(v.score ?? 0),
  n: Number(v.n ?? 0),
  percent: Number(v.percent ?? 0),
}));
