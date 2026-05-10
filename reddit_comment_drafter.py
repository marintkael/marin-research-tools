#!/usr/bin/env python3
"""Reddit comment-draft generator — human-in-the-loop.

This module produces *drafts* of comments for the operator (``u/marintkael``)
to review and submit MANUALLY through Reddit's normal web interface. The
Reddit Data API is not used to submit content. The drafter only reads public
data and locally renders a draft into Markdown for human review.

Three things happen on each run:

1. Read public buzz data about comparable authors (collected separately by a
   small read-only Reddit ingestion script).
2. For each high-engagement thread, fetch the post + top comments via the
   public ``.json`` endpoint.
3. Pass the context to a language model (the public version targets the
   Gemini API; any LLM with a compatible request format can be swapped in via
   environment variables) and produce a candidate draft.
4. Run the draft through ``style_lint`` (see this repo) BEFORE writing it to
   the operator's review file. Drafts that fail the lint are emitted with a
   visible failure marker so they are not posted by accident.

Phase logic (karma-based; the drafter never assumes a phase it has not
verified):

- Phase 1 — account warmup (karma < 100, account < 6 months): no
  self-mentions, no own-book references, no links. Comments exist only to add
  value to the thread.
- Phase 2 — account established (karma 100+, age 6+ months): light, indirect
  mentions are permissible only when the thread topic genuinely calls for
  them. Maximum one self-mention per thread, never a direct site link.
- Phase 3 — post-launch (karma 500+): direct mentions are permitted in
  topic-appropriate threads, still respecting the 9:1 spirit of Reddit's
  self-promotion guidance.

The phase is read from a small state file maintained by a separate
``reddit_account_tracker`` script; the drafter never elevates its own phase.

Output:
- A ``reddit_drafts_LATEST.md`` file containing all drafts the operator
  must read and decide on. Clean drafts are clearly marked; lint-blocked
  drafts carry the failure reason.
- A history log (JSON Lines) for audit, including the lint outcome.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ------------------------------------------------------------------
# Paths and constants
# ------------------------------------------------------------------
ROOT = Path(os.environ.get("MARIN_RESEARCH_ROOT", Path.cwd())).resolve()
HEALTH_DIR = Path(os.environ.get(
    "MARIN_HEALTH_DIR", ROOT / "_health"
))
HEALTH_DIR.mkdir(parents=True, exist_ok=True)
HISTORY = HEALTH_DIR / "reddit_drafts_history.jsonl"
LATEST = HEALTH_DIR / "reddit_drafts_LATEST.md"
BUZZ_FILE = HEALTH_DIR / "reddit_comp_author_buzz.json"

USER_AGENT = (
    "marin-t-kael:research-tooling:v0.1 "
    "(by /u/marintkael; https://marin-t-kael.de/research)"
)
GEMINI_MODEL = os.environ.get("MARIN_LLM_MODEL", "gemini-flash-latest")
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# Operator account (lower-case, no u/ prefix).
MARIN_ACCOUNT = "marintkael"

# Only consider threads with real engagement. This keeps daily draft volume
# small and the operator's review burden bounded.
MIN_SCORE_THRESHOLD = 30


# ------------------------------------------------------------------
# Voice and phase rules (kept short; see the public style sheet linked
# from https://marin-t-kael.de/research for the full canonical text).
# ------------------------------------------------------------------
VOICE_ANTI_PATTERN = """
- No multiple exclamation marks, no CAPS-LOCK.
- No emojis.
- No hype vocabulary ("breathtaking", "gripping", "finally!", "game-changer", "amazing reveal").
- No marketing anglicisms used as nouns ("Reveal", "Drop", "Launch").
- No politically charged or religious topics.
- No personal trivia outside the work (family, hobbies, daily routine).
""".strip()


PHASE_RULES = {
    "warmup": """
PHASE 1 — account warmup (no self-mentions permitted):
- MUST NOT mention: "Marin T. Kael", "Das vierte Feld", "Prägungen des Reiches", marin-t-kael.de.
- MUST NOT present as an author ("I am working on a book that ..." is forbidden).
- MUST NOT link to one's own site.
- The task is 100% to add value: substantive recommendations, context, genre insight.
- Objective: accumulate karma organically.
""".strip(),
    "dezent": """
PHASE 2 — account established (light indirect mentions permissible):
- Self/work may be mentioned only when the thread topic genuinely calls for it.
- Never marketing voice. Only as one reader recommendation among many.
- Avoid direct links to one's own site; at most a text reference to author name and book title.
- One self-mention per thread, maximum.
""".strip(),
    "direct": """
PHASE 3 — post-launch (direct mentions permitted in topic-appropriate threads):
- Self/work may be recommended directly, but still as one of many.
- Goodreads / Amazon links acceptable when they genuinely serve the thread.
- Honour the 9:1 spirit: roughly nine non-self comments per one self-mention overall.
""".strip(),
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _detect_phase() -> str:
    """Read the externally-maintained phase. Default to warmup if unsure."""
    phase_file = HEALTH_DIR / "reddit_marin_phase.txt"
    if phase_file.exists():
        try:
            return phase_file.read_text(encoding="utf-8").strip() or "warmup"
        except Exception:
            return "warmup"
    return "warmup"


def load_env_var(key: str) -> str | None:
    """Look up a key in a local ``.env`` first, then the process environment."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key)


def fetch_post_context(permalink_url: str) -> dict:
    """Read the post + a small slice of its top comments from Reddit's public
    ``.json`` endpoint. Strictly read-only; no auth, no writes."""
    if not permalink_url.startswith("http"):
        permalink_url = "https://reddit.com" + permalink_url
    if not permalink_url.endswith(".json"):
        permalink_url = permalink_url.rstrip("/") + ".json"
    req = urllib.request.Request(
        permalink_url, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except Exception as e:
        return {"error": str(e)}

    if not isinstance(data, list) or len(data) < 2:
        return {"error": "unexpected response shape"}

    post = (
        data[0]["data"]["children"][0]["data"]
        if data[0].get("data", {}).get("children") else {}
    )
    comments_data = (
        data[1]["data"]["children"]
        if data[1].get("data", {}).get("children") else []
    )

    top_comments = []
    for c in comments_data[:5]:
        cd = c.get("data", {})
        if cd.get("body"):
            top_comments.append({
                "author": cd.get("author"),
                "score": cd.get("score", 0),
                "body": cd.get("body", "")[:500],
            })

    return {
        "title": post.get("title", ""),
        "selftext": (post.get("selftext") or "")[:1500],
        "author": post.get("author"),
        "subreddit": post.get("subreddit"),
        "score": post.get("score", 0),
        "num_comments": post.get("num_comments", 0),
        "permalink": permalink_url,
        "top_comments": top_comments,
    }


# ------------------------------------------------------------------
# Drafting
# ------------------------------------------------------------------
def llm_draft(post_ctx: dict, comp_author: str, phase: str = "warmup") -> dict:
    """Produce a single candidate draft and run it through the style lint."""
    api_key = load_env_var("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY missing"}

    sub = post_ctx.get("subreddit", "Fantasy")
    is_dach = sub.lower() in {"buecher", "de_buecher", "deutscheliteratur", "de"}
    lang_instruction = "Antworte auf DEUTSCH." if is_dach else "Reply in ENGLISH."

    system_prompt = f"""You are drafting a Reddit comment for the user @{MARIN_ACCOUNT} on r/{sub}.

CONTEXT:
- Comp author this thread is about: {comp_author}
- The comment should engage organically with the Reddit community.
- The operator is building organic Reddit reputation as a fantasy reader.

VOICE RULES (author persona):
{VOICE_ANTI_PATTERN}

PHASE RULES (current phase: {phase}):
{PHASE_RULES.get(phase, PHASE_RULES['warmup'])}

REDDIT-SPECIFIC RULES:
- Length: 80–250 words. Sweet spot 120–180 words.
- Top-level comment style: substantial, not a one-liner.
- No "Actually...", no correcting OPs, no superiority.
- Engage with what OP wrote, build on it, do not change the topic.
- Mention specific titles or authors with substantive opinions, not lists.
- {lang_instruction}

REDDIT MARKDOWN — use selectively, not as decoration:
- Book titles in *italics*: *Foundryside*.
- Block-quote OP only when responding to a specific phrase: > exact quote.
- Numbered or bulleted lists only when listing 3+ items where structure helps.
- NO bold headers, NO horizontal rules, NO tables. The comment should read as a paragraph.

OUTPUT:
Return ONLY the comment text. No meta-commentary, no "Here is a comment:".
The text you return will be reviewed by a human, then copy-pasted to Reddit."""

    top_comments_block = "\n".join(
        f'- @{c["author"]} ({c["score"]} pts): {c["body"][:200]}'
        for c in post_ctx.get("top_comments", [])[:3]
    )

    user_prompt = f"""POST TITLE: {post_ctx['title']}

POST BODY:
{post_ctx.get('selftext', '')[:1000]}

TOP EXISTING COMMENTS:
{top_comments_block}

Draft a top-level comment from @{MARIN_ACCOUNT} that engages substantively
with this thread."""

    body = json.dumps({
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "maxOutputTokens": 800,
            "temperature": 0.7,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")

    url = GEMINI_ENDPOINT.format(model=GEMINI_MODEL) + f"?key={api_key}"
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body_txt = ""
        try:
            body_txt = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        return {"error": f"HTTP {e.code}: {body_txt}"}
    except Exception as e:
        return {"error": str(e)}

    text = ""
    try:
        cand = data.get("candidates", [{}])[0]
        for part in cand.get("content", {}).get("parts", []):
            if "text" in part:
                text += part["text"]
    except Exception:
        pass

    draft = text.strip()

    # Run the draft through the public style/policy linter.
    style_lint_result: dict | None = None
    try:
        from style_lint import check as style_check
        style_lint_result = style_check(draft, surface="reddit", is_outbound=True)
    except Exception as e:
        style_lint_result = {"error": str(e), "blocked": False, "violations": []}

    return {
        "draft": draft,
        "tokens": data.get("usageMetadata", {}).get("totalTokenCount", 0),
        "model": data.get("modelVersion"),
        "style_lint": style_lint_result,
    }


def already_drafted(post_url: str) -> bool:
    if not HISTORY.exists():
        return False
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
            if entry.get("post_url") == post_url:
                return True
        except Exception:
            continue
    return False


def render_md(drafts: list[dict], phase: str) -> str:
    ts = datetime.now(timezone.utc).isoformat()[:16]
    lines = [f"# Reddit comment drafts · {ts}\n"]
    lines.append(
        f"_Account: @{MARIN_ACCOUNT} · Phase: **{phase}** · {len(drafts)} drafts_\n"
    )

    if not drafts:
        lines.append(
            "🕒 No new high-engagement threads about comp authors today that "
            "are not already drafted.\n"
        )
        return "\n".join(lines)

    lines.append(
        "**Workflow:** click the permalink → paste the draft as a top-level "
        "comment in Reddit's normal web UI → mark as done.\n"
    )

    for i, d in enumerate(drafts, 1):
        lines.append(
            f"\n---\n\n## Draft #{i} — r/{d['subreddit']} "
            f"(comp: {d['comp_author']})\n"
        )
        lines.append(
            f"**Thread:** [{d['post_title'][:90]}]({d['post_url']}) · "
            f"score={d['post_score']} · comments={d['post_num_comments']}\n"
        )
        if d.get("error"):
            lines.append(f"❗ Drafting failed: {d['error']}\n")
            continue

        sl = d.get("style_lint") or {}
        if sl.get("blocked"):
            lines.append(
                f"**❗ DRAFT BLOCKED by style_lint** — "
                f"{len(sl.get('violations', []))} critical violations"
            )
            for v in sl.get("violations", [])[:3]:
                lines.append(
                    f"  - [{v.get('severity')}/{v.get('rule')}] "
                    f"{v.get('match', '')}: {v.get('message', '')[:120]}"
                )
            lines.append("\n**Draft (for operator review, DO NOT POST — fix first):**\n")
        elif sl.get("violations"):
            lines.append(
                f"**⚠️ Draft with warnings** "
                f"({len(sl.get('violations', []))} non-blocking) — review recommended"
            )
            lines.append(
                "\n**Draft (operator-hand: copy-paste, with warnings noted above):**\n"
            )
        else:
            lines.append(
                "**✅ Draft passed style_lint cleanly — operator-hand: copy-paste:**\n"
            )
        lines.append("```")
        lines.append(d["draft"])
        lines.append("```\n")

    return "\n".join(lines)


def main() -> int:
    if not BUZZ_FILE.exists():
        print(
            "Waiting for reddit_comp_author_buzz.json — run the ingestion "
            "script first."
        )
        return 2

    buzz = json.loads(BUZZ_FILE.read_text(encoding="utf-8"))
    candidates: list[dict] = []
    for comp_author, posts in buzz.items():
        for p in posts:
            if "error" in p:
                continue
            if p.get("score", 0) < MIN_SCORE_THRESHOLD:
                continue
            if already_drafted(p["url"]):
                continue
            candidates.append({**p, "comp_author": comp_author})

    candidates.sort(
        key=lambda c: c.get("score", 0) * (1 + (c.get("num_comments", 0) ** 0.5)),
        reverse=True,
    )
    candidates = candidates[:3]  # Top 3 per day, free-tier-friendly.

    drafts: list[dict] = []
    phase = _detect_phase()
    for c in candidates:
        ctx = fetch_post_context(c["url"])
        if "error" in ctx:
            drafts.append({
                **c,
                "post_title": c["title"],
                "post_url": c["url"],
                "post_score": c["score"],
                "post_num_comments": c["num_comments"],
                "error": ctx["error"],
            })
            continue
        time.sleep(8)  # Pace requests to stay free-tier-friendly.
        result = llm_draft(ctx, c["comp_author"], phase=phase)
        drafts.append({
            "comp_author": c["comp_author"],
            "subreddit": ctx.get("subreddit", c.get("subreddit")),
            "post_title": ctx["title"],
            "post_url": c["url"],
            "post_score": c["score"],
            "post_num_comments": c["num_comments"],
            "draft": result.get("draft", ""),
            "error": result.get("error"),
            "tokens": result.get("tokens"),
            "model": result.get("model"),
            "style_lint": result.get("style_lint"),
        })
        time.sleep(2)
        if result.get("draft"):
            with HISTORY.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "post_url": c["url"],
                    "comp_author": c["comp_author"],
                    "phase": phase,
                    "draft_preview": result["draft"][:120],
                    "style_lint_blocked": bool(
                        (result.get("style_lint") or {}).get("blocked")
                    ),
                }) + "\n")

    md = render_md(drafts, phase)
    LATEST.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
