#!/usr/bin/env python3
"""
Marin Research Eval Runner — wraps lm-evaluation-harness with custom models pre-loaded.

Usage:
  python run_eval.py --model claude_web_importer --model_args model_tier=sonnet
  python run_eval.py --model openai_search_preview --model_args model=gpt-4o-mini-search-preview-2025-03-11
  python run_eval.py --model gemini_grounded --model_args model=gemini-2.5-flash
"""
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# 1. Pre-load custom models so they're in the registry before harness runs
sys.path.insert(0, str(Path(__file__).parent))
import marin_models  # noqa: F401 (side-effect: register models)

# 2. Now we can use the harness API
from lm_eval import simple_evaluate
from lm_eval.tasks import TaskManager


def parse_model_args(s: str) -> dict:
    args = {}
    if not s:
        return args
    for pair in s.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            args[k.strip()] = v.strip()
    return args


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="Model name (registered)")
    p.add_argument("--model_args", default="", help="comma-separated k=v")
    p.add_argument("--tasks", default="marin_research_v1", help="comma-separated tasks")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--output", default="results/eval_LATEST.json")
    args = p.parse_args()

    task_path = str(Path(__file__).parent / "marin_tasks")
    tm = TaskManager(include_path=task_path)

    model_args_dict = parse_model_args(args.model_args)
    print(f"[run_eval] model={args.model} args={model_args_dict} tasks={args.tasks} limit={args.limit}")

    results = simple_evaluate(
        model=args.model,
        model_args=args.model_args,
        tasks=args.tasks.split(","),
        limit=args.limit,
        task_manager=tm,
        log_samples=True,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Add provenance + locked methodology version
    results["_meta"] = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "harness_version": "0.4.12",
        "marin_methodology_version": "4.0",
        "model_name": args.model,
        "model_args": model_args_dict,
        "tasks": args.tasks,
    }

    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n[run_eval] saved {out_path}")
    print(f"[run_eval] aggregate scores:")
    for task, metrics in (results.get("results") or {}).items():
        if "marin_score_raw,none" in metrics:
            print(f"  {task}  raw={metrics['marin_score_raw,none']:.3f}  norm={metrics.get('marin_score_norm,none', '?')}")


if __name__ == "__main__":
    main()
