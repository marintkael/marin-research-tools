#!/usr/bin/env python3
"""
Run all 5 LLMs (3 API + 2 imported) and produce a consolidated snapshot.

Output: results/snapshot_LATEST.json compatible with /__push_claude_web schema.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

# Auto-load .env from foundation root (single source of truth)
def load_env():
    candidates = [
        Path("/Users/marcelkristhofen/Documents/Claude/personal-ai-foundation/.env"),
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
    ]
    for env_file in candidates:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
            return env_file
    return None

env_loaded = load_env()
print(f"[env] loaded from: {env_loaded}")

import marin_models  # noqa: F401

from lm_eval import simple_evaluate
from lm_eval.tasks import TaskManager

GATEWAY_BASE = "https://gateway.ai.cloudflare.com/v1/3cff4d60f16032d78a178305caf97264/marin-ai-citation"

MODEL_CONFIGS = [
    {
        "name": "openai_search_preview_mini",
        "model": "openai_search_preview",
        "model_args": f"model=gpt-4o-mini-search-preview-2025-03-11,gateway={GATEWAY_BASE}",
        "provider": "OpenAI",
        "scope_label": "gpt-4o-mini-search-preview",
    },
    {
        "name": "openai_search_preview_full",
        "model": "openai_search_preview",
        "model_args": f"model=gpt-4o-search-preview-2025-03-11,gateway={GATEWAY_BASE}",
        "provider": "OpenAI",
        "scope_label": "gpt-4o-search-preview",
    },
    {
        "name": "gemini_2_5_flash_grounded",
        "model": "gemini_grounded",
        # Gateway is REQUIRED for Marin's Gemini key (project-bound)
        "model_args": f"model=gemini-2.5-flash,gateway={GATEWAY_BASE}",
        "provider": "Gemini",
        "scope_label": "gemini-2.5-flash-grounded",
    },
    {
        "name": "claude_sonnet_4_6_web",
        "model": "claude_web_importer",
        "model_args": "model_tier=sonnet,sweep_dir=/tmp/marin_sweep",
        "provider": "Claude",
        "scope_label": "claude-sonnet-4.6 (web)",
    },
    {
        "name": "claude_opus_4_7_web",
        "model": "claude_web_importer",
        "model_args": "model_tier=opus,sweep_dir=/tmp/marin_sweep",
        "provider": "Claude",
        "scope_label": "claude-opus-4.7 (web)",
    },
]


def run_model(cfg, tm, skip_on_error=True) -> dict:
    print(f"\n[{cfg['name']}] running...")
    try:
        results = simple_evaluate(
            model=cfg["model"],
            model_args=cfg["model_args"],
            tasks=["marin_research_v1"],
            task_manager=tm,
            log_samples=True,
        )
        agg = results["results"]["marin_research_v1"]
        samples = results.get("samples", {}).get("marin_research_v1", [])
        return {
            "config": cfg,
            "ok": True,
            "n_samples": len(samples),
            "marin_score_raw": agg.get("marin_score_raw,none"),
            "marin_score_norm": agg.get("marin_score_norm,none"),
            "marin_is_hallu_rate": agg.get("marin_is_hallu,none"),
            "marin_is_full_rate": agg.get("marin_is_full,none"),
            "samples": [
                {
                    "doc_id": s.get("doc_id"),
                    "question": (s.get("doc") or {}).get("question", "")[:200],
                    "question_id": (s.get("doc") or {}).get("id"),
                    "category": (s.get("doc") or {}).get("category"),
                    "answer": (s.get("filtered_resps") or [""])[0][:1000],
                    "marin_score_raw": s.get("marin_score_raw"),
                    "marin_is_hallu": s.get("marin_is_hallu"),
                    "marin_is_full": s.get("marin_is_full"),
                }
                for s in samples
            ],
        }
    except Exception as e:
        print(f"[{cfg['name']}] FAILED: {e}")
        if not skip_on_error:
            raise
        return {"config": cfg, "ok": False, "error": str(e)[:500]}


def build_snapshot(per_model_results):
    """Aggregate into push-to-D1 schema."""
    all_rows = []
    by_model = {}
    by_category = {}
    total_score = 0.0
    total_n = 0
    for r in per_model_results:
        if not r.get("ok"): continue
        cfg = r["config"]
        model_id = cfg["name"]
        bm = by_model.setdefault(model_id, {"score": 0, "n": 0, "n_error": 0, "provider": cfg["provider"]})
        for s in r.get("samples", []):
            score = float(s.get("marin_score_raw") or 0)
            bm["score"] += score
            bm["n"] += 1
            total_score += score
            total_n += 1
            cat = s.get("category") or "Direct"
            bc = by_category.setdefault(cat, {"score": 0, "n": 0})
            bc["score"] += score
            bc["n"] += 1
            all_rows.append({
                "model": cfg["scope_label"],
                "question_id": s.get("question_id"),
                "category": cat,
                "question": s.get("question"),
                "answer": s.get("answer"),
                "score": score,
                "status": "harness_eval",
                "sources": [],
                "has_web_search": True,
            })
        bm["percent"] = round(bm["score"] / (bm["n"] * 3) * 1000) / 10 if bm["n"] else None
    for v in by_category.values():
        v["percent"] = round(v["score"] / (v["n"] * 3) * 1000) / 10 if v["n"] else None

    return {
        "schema_version": "lm_eval_harness/4.0",
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": {
            "source": "lm_evaluation_harness",
            "harness_version": "0.4.12",
            "marin_methodology_version": "4.0",
            "task_version": "marin_research_v1",
        },
        "results": all_rows,
        "aggregate": {
            "total_score": total_score,
            "by_model": by_model,
            "by_category": by_category,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="results/snapshot_LATEST.json")
    p.add_argument("--skip", default="", help="comma-separated model names to skip")
    args = p.parse_args()

    task_path = str(Path(__file__).parent / "marin_tasks")
    tm = TaskManager(include_path=task_path)

    skip_set = set([s.strip() for s in args.skip.split(",") if s.strip()])
    cfgs = [c for c in MODEL_CONFIGS if c["name"] not in skip_set]

    per_model = []
    for cfg in cfgs:
        r = run_model(cfg, tm, skip_on_error=True)
        per_model.append(r)

    snap = build_snapshot(per_model)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snap, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"\n=== SNAPSHOT ===")
    print(f"Saved: {out}")
    print(f"Total rows: {len(snap['results'])}  Total score: {snap['aggregate']['total_score']:.2f}")
    for m, v in snap["aggregate"]["by_model"].items():
        print(f"  {m:<35}  n={v['n']:>3}  score={v['score']:.1f}  pct={v.get('percent')}%")


if __name__ == "__main__":
    main()
