"""
Marin Research Custom Task Utils for lm-evaluation-harness.

Locked methodology v4.0 (2026-05-23, Pre-Reg Amendment).
Score-Algo 1:1 portiert aus cache.nosync/marin/research-pipeline/src/stages/ai_citation.js
"""
import re
import json

# ── Score-Anchor Patterns (LOCKED v4.0, NICHT-täglich-änderbar) ──
# Change-Discipline: Erweiterung dieser Patterns = Methodology-Amendment
# mit neuer Task-Version (marin_research_v2, etc.), nicht silent update.

MARIN_SPECIFIC = re.compile(r"marin[\s-]*t[\.\s-]+kael", re.I)

KEY_FACTS = [
    re.compile(r"marin[\s-]*t[\.\s-]+kael", re.I),
    re.compile(r"das\s+vierte\s+feld", re.I),
    re.compile(r"22\.?\s*september\s*2026|22\.09\.2026", re.I),
    re.compile(r"varin", re.I),
    re.compile(r"deutsch\w*\s+(fantasy|autor)", re.I),
    re.compile(r"edikt", re.I),
]

NEGATIVE_HALLU = [
    # US-female-Verwechslung
    re.compile(r"american\s+author", re.I),
    re.compile(r"US[- ]author", re.I),
    re.compile(r"\bher\s+(debut|novel|book)\b", re.I),
    re.compile(r"\bshe\s+(wrote|is|debut)", re.I),
    re.compile(r"last\s+house\s+guest", re.I),
    # Person-Verwechslungs-Hallus
    re.compile(r"pauline\s+kael", re.I),
    re.compile(r"victoria\s+aveyard|blackcoat\s+rebellion|red\s+queen.*glass\s+sword", re.I),
    re.compile(r"faulkner|sound\s+and\s+the\s+fury", re.I),
    re.compile(r"holocron\s+keeper|lucasfilm|star\s+wars", re.I),
    re.compile(r"swiss\s+author|austrian.*poet.*salzburg", re.I),
    # Title-Collision (Construct-Validity-Audit 2026-05-20)
    re.compile(r"mokka\s+m[üu]ller", re.I),
    re.compile(r"marin\s+t\.?\s*mikel", re.I),
    # Brand-Collision (Maritime Research Institute Netherlands)
    re.compile(r"maritime\s+research\s+institute|wageningen|hydrodynamic", re.I),
]


def doc_to_text(doc):
    """Prompt formatting for the LLM. Naturalistic — no Pipeline-Verräter."""
    return doc["question"]


def doc_to_target(doc):
    """Placeholder target — actual scoring is in process_results."""
    return ""


def score_answer(answer: str, category: str) -> dict:
    """
    Score-Algo locked v4.0. Returns dict with score (-3..3) and status.

    Scale:
      -3  hallucinated         (NEGATIVE_HALLU matched)
       0  not_found            (no KEY_FACTS, no MARIN_SPECIFIC)
     0.5  name_only            ("marin" without t-kael)
       1  minimal_match        (1 KEY_FACTS hit)
       2  partial_book         (2-3 KEY_FACTS hits)
       3  full_citation        (4+ KEY_FACTS hits OR GenreRecommend with MARIN_SPECIFIC)
    """
    if not answer:
        return {"score": 0, "status": "not_found_empty"}

    neg_hits = sum(1 for p in NEGATIVE_HALLU if p.search(answer))
    pos_hits = sum(1 for p in KEY_FACTS if p.search(answer))

    if category == "GenreRecommend":
        # Marin-blind Pflicht-Anchor
        if MARIN_SPECIFIC.search(answer):
            return {"score": 3, "status": "genre_placement"}
        return {"score": 0, "status": "genre_baseline_no_marin"}

    if neg_hits > 0:
        return {"score": -3, "status": "hallucinated"}
    if pos_hits == 0:
        if re.search(r"\bmarin\b", answer, re.I):
            return {"score": 0.5, "status": "name_only"}
        return {"score": 0, "status": "not_found"}
    if pos_hits >= 4:
        return {"score": 3, "status": "full_citation"}
    if pos_hits >= 2:
        return {"score": 2, "status": "partial_book"}
    return {"score": 1, "status": "minimal_match"}


def process_results(doc, results):
    """
    lm-eval-harness process_results contract:
      doc: the dataset row
      results: list of model outputs (generate_until → [str])
    Returns: dict of metric_name → value
    """
    answer = results[0] if results else ""
    scored = score_answer(answer, doc["category"])
    score = scored["score"]
    # Normalize to 0-1 for harness aggregation (score in [-3, 3] → [0, 1])
    normalized = (score + 3) / 6
    # Note: marin_status_json removed from metrics dict because harness mean-aggregation
    # cannot handle strings. Per-sample status is logged via --log_samples instead.
    return {
        "marin_score_raw": score,
        "marin_score_norm": normalized,
        "marin_is_hallu": 1.0 if scored["status"] == "hallucinated" else 0.0,
        "marin_is_full": 1.0 if scored["status"] == "full_citation" else 0.0,
    }
