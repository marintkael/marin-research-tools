-- Migration 0003: Cross-LLM-Trust-Graph (Play 6)
-- Source-attribution-parsing pro (run_id, llm, question_id) liefert pro
-- Answer eine Mention-Liste je Source-Typ. Aggregation pro Snapshot ergibt
-- Trust-Score-Verteilung pro LLM (Wikipedia/Wikidata = +2, Inferenz = -1, ...).
--
-- Speist Dashboard-Heatmap "Source-Attribution per Cluster × LLM" und
-- ermöglicht Methodology-Note-02-Befund "Trust-Tier per Surface".
--
-- Felder:
--   id              auto
--   run_id          FK zu pipeline_runs.run_id (TEXT)
--   llm             openai / claude / gemini / mistral / llama3 / etc.
--   question_id     D1 / G2 / R1 etc.
--   source_type     wikipedia | wikidata | goodreads | amazon | official_site
--                   | press | github | orcid | zenodo | reddit | inference
--                   | no_source
--   mentioned       1 wenn Pattern in Answer matched, 0 wenn no_source-Bucket
--   trust_weight    +2 / +1 / 0 / -1 (Author-defined Trust-Score)
--   ts              CURRENT_TIMESTAMP
--
-- Source-Trust-Stufen (initial v1):
--   +2  wikipedia / wikidata / orcid / zenodo   → verifizierbare Primärquelle
--   +1  goodreads / amazon / official_site /
--        github                                  → semi-autoritativ
--    0  press / reddit / no_source              → neutral
--   -1  inference                                → Halluzinations-Risiko

CREATE TABLE IF NOT EXISTS ai_citation_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id       TEXT NOT NULL,
  llm          TEXT NOT NULL,
  question_id  TEXT NOT NULL,
  source_type  TEXT NOT NULL,
  mentioned    INTEGER NOT NULL DEFAULT 0,
  trust_weight REAL NOT NULL DEFAULT 0,
  ts           TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_aics_run     ON ai_citation_sources(run_id);
CREATE INDEX IF NOT EXISTS idx_aics_llm     ON ai_citation_sources(llm);
CREATE INDEX IF NOT EXISTS idx_aics_source  ON ai_citation_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_aics_run_llm ON ai_citation_sources(run_id, llm);
