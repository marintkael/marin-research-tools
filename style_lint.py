#!/usr/bin/env python3
"""
Marin Style-Lint — content-policy pre-check pipeline.

A small, opinionated linter that runs over draft material before it leaves the
operator's workstation. The goal is not stylistic perfection; it is to catch
the specific classes of content drift that have historically caused problems
for AI-augmented authorship: canon contradictions, persona drift, and
platform-rule violations.

This is the public, generic version of the linter. Operator-specific patterns
(real-name firewall, internal-system-name leak detection, project-private
patterns) are loaded from a local ``.env``-driven config layer that is NOT
committed to this repository. Everything in this file is safe to share.

Documentation of the broader research framework:
    https://marin-t-kael.de/research

Usage:
    python3 style_lint.py --text "draft to lint" --surface reddit
    python3 style_lint.py --stdin --surface hardcover
    python3 style_lint.py --file path/to/draft.md
    python3 style_lint.py --root path/to/material/ --strict

Library:
    from style_lint import check
    result = check(comment_text, surface="reddit")
    if result["blocked"]:
        print("CANNOT POST"); print(result["violations"])

Exit codes:
    0 — clean
    1 — S1 (showstopper) finding
    2 — S2 (factual) finding
    3 — S3+ (drift) finding in --strict mode
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------- Patterns ----------
# Every pattern carries a severity (S1 hardest, S3 softest) and a
# ``preserve_if`` callback that excludes legitimate uses (e.g. file-system
# paths, anti-pattern documentation lines, internal comments).

PATTERNS = [
    # ===== S1 — SHOWSTOPPER =====
    {
        "severity": "S1",
        "rule": "praegungen-encoding",
        "pattern": re.compile(r"\bPraegung"),
        "preserve_if": lambda line: any(p in line for p in [
            "Praegungen_des_Reiches",   # file-system path idiom
            "praegungen-des-reiches",    # URL slug
            "pdftitle=",                 # PDF metadata
            '"Praegung"',                # explicit quote in anti-pattern doc
            "Praegung_",                 # filename prefix
            "NEVER:",                    # linter rule itself
        ]),
        "message": (
            "Saga name must be rendered with the umlaut ('Prägungen'). "
            "The folder-name 'Praegungen_des_Reiches' is a path idiom, not a "
            "display string."
        ),
    },
    {
        "severity": "S1",
        "rule": "protagonist-hallucination",
        "pattern": re.compile(r"\bJoran\b"),
        "preserve_if": lambda line: "does not exist" in line or "existiert nicht" in line,
        "message": (
            "'Joran' is not a character in the canon. The protagonist of book "
            "one is Arin, a male scribe-apprentice in the Schreiberhaus."
        ),
    },
    {
        "severity": "S1",
        "rule": "protagonist-gender",
        "pattern": re.compile(
            r"\b(?:Tochter eines (?:abgesetzten )?Schreibmeisters|"
            r"daughter of a (?:deposed )?scribe)\b"
        ),
        "preserve_if": lambda line: False,
        "message": (
            "Incorrect protagonist gender. Arin is male, a scribe-apprentice in "
            "the Schreiberhaus."
        ),
    },
    {
        "severity": "S1",
        "rule": "author-gender-encoding",
        "pattern": re.compile(r"\b(?:Autor:in|Autor\*in|AutorIn)\b"),
        "preserve_if": lambda line: any(p in line for p in [
            "NEVER:",
            "„Autor:in",
            "ist falsch",
            "is wrong",
        ]),
        "message": (
            "The author persona is encoded as masculine. The German gender-"
            "neutral forms 'Autor:in', 'Autor*in', and 'AutorIn' are not "
            "permitted. Use 'Autor' or 'schreibt'."
        ),
    },
    {
        "severity": "S1",
        "rule": "launch-date-drift",
        "pattern": re.compile(r"\b(?:2026-07-06|2026-07-01|01\.07\.2026|06\.07\.2026)\b"),
        "preserve_if": lambda line: any(p in line for p in [
            "NEVER:",
            "T-83", "T-90",
            "2026-07-01 | 2026-07-06",
        ]) or "Pre-Launch" in line or 'timeline-T">T-' in line,
        "message": (
            "Launch date is 2026-09-22 (locked). Earlier 2026-07-* dates were "
            "drafting defaults that have since been retired."
        ),
    },

    # ===== S2 — FACTUAL =====
    {
        "severity": "S2",
        "rule": "internal-volume-count-leak",
        "pattern": re.compile(r"\b(?:16-Bände|16 Bände|sechzehn Bände)\b"),
        "preserve_if": lambda line: any(p in line for p in ["NEVER:", "~~16"]),
        "message": (
            "Internal working volume count appears in outbound material. "
            "Internal documentation may discuss this; outbound communication "
            "must not."
        ),
    },
    {
        "severity": "S1",
        "rule": "volume-count-outbound",
        "pattern": re.compile(
            r"\b(?:17 Bände|17 Bänden|siebzehn Bände|siebzehnbändig|auf 17 Bände|auf siebzehn)\b"
        ),
        "preserve_if": lambda line: any(p in line for p in [
            "NEVER:", "Anti-Pattern", "INTERNAL",
            "Style-Sheet", "CANONICAL_TRUTH",
        ]),
        "message": (
            "Concrete volume counts must not appear in outbound communication. "
            "Use 'multi-volume saga' / 'opening volume of the saga'."
        ),
    },
    {
        "severity": "S1",
        "rule": "world-mechanic-hallucination",
        "pattern": re.compile(
            r"(?:Konsequenzen einträgt|in das man die eigenen Konsequenzen|"
            r"den die eigenen Konsequenzen|die eigenen Konsequenzen)"
        ),
        "preserve_if": lambda line: any(p in line for p in [
            "NEVER:", "Anti-Pattern", "Drift-Fix",
            "Style-Sheet", "CANONICAL_TRUTH",
            "Hallu", "forbidden",
        ]),
        "message": (
            "World-mechanic hallucination: the 'fourth field' is the un-written / "
            "potential — NOT 'a field into which one inscribes one's "
            "consequences'. See the public style sheet for the canonical "
            "definition."
        ),
    },

    # ===== S3 — ENCODING DRIFT =====
    {
        "severity": "S3",
        "rule": "ascii-umlaut-drift",
        "pattern": re.compile(
            r"\b(?:ueber|fuer|Strassen|Strasse|Muenze|Muenzen|Koenig|Koenigreich|"
            r"aelteste|spuerbar|Doerfer|duerfen|uebergehend|ueberladend|"
            r"Subtilitaet|Subtilitaets|erhaelt|Foederation|Verlaeufe|Strassen-)\b"
        ),
        "preserve_if": lambda line: any(p in line for p in [
            "#", "def ", "http", "'", "ascii", "NEVER", "|",
            "praegungen-des-reiches",
        ]),
        "message": "ASCII transliteration of German umlauts in outbound material. Use ä/ö/ü/ß.",
    },
]


# NOTE for the public release: an operator-specific "S4 — REAL-NAME FIREWALL"
# rule and a "system-internals leak" rule are loaded at runtime from
# ``.env``-resolved private pattern files (see policies/README.md). They are
# not bundled with this repository because the patterns themselves would leak
# the very thing they detect. The framework supports the rule shape; the
# concrete patterns belong to the operator.
def _load_private_rules() -> list[dict]:
    private_path = os.environ.get("STYLE_LINT_PRIVATE_RULES")
    if not private_path:
        return []
    try:
        spec_path = Path(private_path)
        if not spec_path.exists():
            return []
        # The private rules file is expected to expose a list named ``RULES``
        # whose elements have the same shape as the entries in PATTERNS above.
        ns: dict = {}
        exec(spec_path.read_text(encoding="utf-8"), {"re": re}, ns)
        return list(ns.get("RULES", []))
    except Exception:
        return []


# Surfaces with platform-specific rules. Outbound = the file or string is
# leaving the operator's workstation. Internal drafts skip the outbound rules.
OUTBOUND_PATTERNS = [
    "_PressKit/",
    "_APlusContent/",
    "_Newsletter/",
    "_Audio/pronunciation",   # to voice actor
    "_Translation/glossar",   # to translator
    "website/",
    "site/",
]


def is_outbound(path: Path) -> bool:
    s = str(path)
    return any(p in s for p in OUTBOUND_PATTERNS)


REDDIT_SURFACE_PATTERNS = [
    {
        "severity": "S2",
        "rule": "reddit-self-promo-cta",
        "pattern": re.compile(
            r"\b(?:check out my (?:book|debut|novel)|"
            r"buy my (?:book|novel|debut)|"
            r"pre-?order (?:now|today|here))\b",
            re.IGNORECASE,
        ),
        "message": (
            "Explicit self-promo CTA — Reddit 9:1 rule and r/Fantasy spam "
            "detection will flag this."
        ),
    },
    {
        "severity": "S2",
        "rule": "reddit-template-bot-signature",
        "pattern": re.compile(
            r"(?:^|\n)\s*(?:Disclaimer:|As an AI(?: language model)?|I am a bot)",
            re.IGNORECASE,
        ),
        "message": "Template bot-pattern detected — Reddit auto-flag risk.",
    },
]

HARDCOVER_SURFACE_PATTERNS = [
    {
        "severity": "S2",
        "rule": "hardcover-self-promo-in-review",
        "pattern": re.compile(
            r"\b(?:check out my book|my own debut|read my novel)\b",
            re.IGNORECASE,
        ),
        "message": "Hardcover community norm: no self-promo in reviews.",
    },
]


def lint_file(path: Path) -> list[dict]:
    findings: list[dict] = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [{
            "file": str(path),
            "severity": "ERROR",
            "rule": "read-error",
            "message": f"Cannot read: {e}",
            "line": 0,
            "context": "",
        }]
    return _lint_text(content, is_outbound_flag=is_outbound(path), file_label=str(path))


def _lint_text(content: str, is_outbound_flag: bool = True,
               surface: str | None = None,
               file_label: str = "<string>") -> list[dict]:
    findings: list[dict] = []
    extra_patterns = []
    if surface == "reddit":
        extra_patterns = REDDIT_SURFACE_PATTERNS
    elif surface == "hardcover":
        extra_patterns = HARDCOVER_SURFACE_PATTERNS

    rules = PATTERNS + _load_private_rules()

    for line_num, line in enumerate(content.split("\n"), start=1):
        for rule in rules:
            preserve_if = rule.get("preserve_if") or (lambda _line: False)
            if preserve_if(line):
                continue
            for match in rule["pattern"].finditer(line):
                findings.append({
                    "file": file_label,
                    "severity": rule["severity"],
                    "rule": rule["rule"],
                    "line": line_num,
                    "col": match.start(),
                    "match": match.group(0),
                    "context": line.strip()[:140],
                    "message": rule["message"],
                    "outbound": is_outbound_flag,
                    "surface": surface,
                })
        if is_outbound_flag:
            for rule in extra_patterns:
                for match in rule["pattern"].finditer(line):
                    findings.append({
                        "file": file_label,
                        "severity": rule["severity"],
                        "rule": rule["rule"],
                        "line": line_num,
                        "col": match.start(),
                        "match": match.group(0),
                        "context": line.strip()[:140],
                        "message": rule["message"],
                        "outbound": True,
                        "surface": surface,
                    })

    # Reddit-specific: self-mention ratio (9:1 spirit)
    if surface == "reddit" and is_outbound_flag:
        self_mention_re = re.compile(
            r"\b(?:Marin T\.? Kael|Das vierte Feld|Prägungen des Reiches|"
            r"marin-t-kael\.de)\b",
            re.IGNORECASE,
        )
        mentions = list(self_mention_re.finditer(content))
        word_count = len(re.findall(r"\b\w+\b", content))
        if mentions and word_count < 200 * len(mentions):
            findings.append({
                "file": file_label,
                "severity": "S3",
                "rule": "reddit-self-mention-ratio",
                "line": 0, "col": 0,
                "match": f"{len(mentions)} mentions / {word_count} words",
                "context": "(ratio-check)",
                "message": (
                    f"{len(mentions)} self-mentions in {word_count} words — "
                    "Reddit 9:1 rule recommends sparser self-reference "
                    "(target: 1 mention per 200+ words)."
                ),
                "outbound": True,
                "surface": "reddit",
            })

    return findings


def check(text: str, surface: str | None = None,
          is_outbound: bool = True) -> dict:
    """Library API.

    Returns a dict with ``passed``, ``blocked`` (S1/S4-level violations are
    blocking), ``violations`` (per-finding detail) and ``word_count``.
    """
    findings = _lint_text(text, is_outbound_flag=is_outbound, surface=surface)
    by_sev: dict[str, list] = {}
    for f in findings:
        by_sev.setdefault(f["severity"], []).append(f)
    blocked = bool(by_sev.get("S1") or by_sev.get("S4"))
    return {
        "passed": len(findings) == 0,
        "blocked": blocked,
        "surface": surface,
        "is_outbound": is_outbound,
        "violations": findings,
        "by_severity": {k: len(v) for k, v in by_sev.items()},
        "word_count": len(re.findall(r"\b\w+\b", text)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Marin Style-Lint — content-policy pre-check pipeline."
    )
    parser.add_argument("--file", help="Single file to lint", default=None)
    parser.add_argument("--text", help="Inline text to lint", default=None)
    parser.add_argument("--stdin", action="store_true",
                        help="Read text from stdin")
    parser.add_argument("--surface",
                        choices=["site", "reddit", "hardcover", "press", "wikidata"],
                        default=None)
    parser.add_argument("--internal", action="store_true",
                        help="Mark as internal (skip outbound rules)")
    parser.add_argument("--root", help="Root directory",
                        default=None)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on any finding")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # String mode (drafter / reviewer integrations)
    if args.text or args.stdin:
        text = args.text if args.text else sys.stdin.read()
        is_out = not args.internal
        result = check(text, surface=args.surface, is_outbound=is_out)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Marin Style-Lint · surface={args.surface or 'generic'} · "
                f"words={result['word_count']}"
            )
            print(f"Status: passed={result['passed']} "
                  f"blocked={result['blocked']}\n")
            for v in result["violations"]:
                icon = "❗" if v["severity"] in ("S1", "S4") else (
                    "⚠️" if v["severity"] == "S2" else "ℹ️"
                )
                print(f"  {icon} [{v['severity']}/{v['rule']}] "
                      f"L{v['line']}: '{v['match']}'")
                print(f"     {v['message']}\n")
        if result["blocked"]:
            return 2
        if args.strict and result["violations"]:
            return 1
        return 0

    # Directory / file mode
    if args.file:
        files = [Path(args.file)]
    else:
        root = Path(args.root) if args.root else Path(os.getcwd())
        files = (
            list(root.glob("**/*.md"))
            + list(root.glob("**/*.html"))
            + list(root.glob("**/*.yaml"))
        )
        files = [
            f for f in files
            if "_Style-Sheet" not in str(f) and ".pre-drift-fix-bak" not in str(f)
        ]

    all_findings: list[dict] = []
    for f in files:
        all_findings.extend(lint_file(f))

    by_sev: dict[str, list] = {}
    for finding in all_findings:
        by_sev.setdefault(finding["severity"], []).append(finding)

    if args.json:
        print(json.dumps({
            "total": len(all_findings),
            "by_severity": {k: len(v) for k, v in by_sev.items()},
            "findings": all_findings,
        }, indent=2))
    else:
        if not all_findings:
            print("✓ Clean — no drift against the style sheet.")
        else:
            print(f"=== Style-Lint findings ({len(all_findings)} total) ===\n")
            for sev in ["S1", "S2", "S3", "S4", "ERROR"]:
                items = by_sev.get(sev, [])
                if not items:
                    continue
                print(f"--- {sev} ({len(items)}) ---")
                for f in items:
                    rel = Path(f["file"]).name
                    print(f"  [{f['rule']}] {rel}:{f['line']} '{f['match']}'")
                    print(f"      {f['message']}")
                    print(f"      Context: {f['context']}")
                print()

    if "S1" in by_sev:
        return 1
    if "S2" in by_sev:
        return 2
    if args.strict and any(s in by_sev for s in ["S3", "S4"]):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
