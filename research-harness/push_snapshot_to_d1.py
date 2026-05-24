#!/usr/bin/env python3
"""
Push harness-snapshot to Cloudflare Worker /__push_claude_web endpoint.

Schema (existing endpoint expects):
  { run_at, scored_at, results[{model, question_id, category, question, answer, score, status, sources}], aggregate }

This wrapper makes lm-eval-harness snapshots compatible with existing D1 schema.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_env():
    """Load .env from common locations (env vars override .env)."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path.home() / ".marin-research" / ".env",
    ]
    extra = os.environ.get("MARIN_ENV_FILE")
    if extra:
        candidates.insert(0, Path(extra).expanduser())
    for env_file in candidates:
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))
            return


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", required=True)
    p.add_argument("--worker_url", default="https://marin-research-pipeline.p96xckbr4c.workers.dev/__push_claude_web")
    args = p.parse_args()

    load_env()
    token = os.environ.get("MARIN_RESEARCH_TRIGGER_TOKEN")
    if not token:
        print("ERROR: MARIN_RESEARCH_TRIGGER_TOKEN not in .env", file=sys.stderr)
        return 1

    snap = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))

    # Guard: if every model in this run failed (all 3 LLMs upstream-blocked,
    # rate-limited, etc.), the snapshot has 0 result rows. Pushing an empty
    # payload to the worker is a wasted call and the worker rejects it with
    # HTTP 500 (it requires non-empty results to compute aggregates).
    # Treat this as a no-op success — exit 0 so the workflow stays green and
    # the next scheduled run gets a fresh shot at the upstreams.
    n_rows = len(snap.get("results") or [])
    if n_rows == 0:
        print(
            "SKIP push_snapshot_to_d1: snapshot has 0 result rows "
            "(all models failed upstream — e.g. shared OpenAI rate-limit, "
            "Gemini 503). Not pushing to /__push_claude_web. Will retry on "
            "next scheduled run.",
            file=sys.stderr,
        )
        return 0

    # Translate harness-snapshot schema → worker /__push_claude_web schema
    # (existing endpoint expects claude_web format, so we route harness data through same path)
    payload = {
        "run_at": snap["run_at"],
        "scored_at": snap["scored_at"],
        "results": snap["results"],
        "aggregate": snap["aggregate"],
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        args.worker_url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "marin-research-harness-push/4.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"HTTP {r.status} · {r.read().decode('utf-8')}")
            return 0
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} · {e.read().decode('utf-8')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
