#!/usr/bin/env python3
"""
Marin Style-Lint — manuscript style-consistency check.

A small, opinionated linter that checks manuscript text and supporting
material for canon contradictions and encoding drift. It is concerned with
internal consistency of the saga *Prägungen des Reiches* — name spellings,
umlaut encoding, world-mechanic vocabulary — not with prose quality.

Documentation of the broader research framework:
    https://marin-t-kael.de/research

Usage:
    python3 style_lint.py --text "your text here"
    python3 style_lint.py --stdin
    python3 style_lint.py --file path/to/file.md
    python3 style_lint.py --root path/to/material/ --strict

Library:
    from style_lint import check
    result = check(text)
    if result["violations"]:
        for v in result["violations"]:
            print(v)

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
            "Earlier volume count appears in current text. The saga is "
            "referenced as 'multi-volume', not by an explicit number."
        ),
    },
    {
        "severity": "S1",
        "rule": "volume-count-explicit",
        "pattern": re.compile(
            r"\b(?:17 Bände|17 Bänden|siebzehn Bände|siebzehnbändig|auf 17 Bände|auf siebzehn)\b"
        ),
        "preserve_if": lambda line: any(p in line for p in [
            "NEVER:", "Anti-Pattern", "INTERNAL",
            "Style-Sheet", "CANONICAL_TRUTH",
        ]),
        "message": (
            "Explicit volume counts must not appear in public text. "
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
        "message": "ASCII transliteration of German umlauts in manuscript text. Use ä/ö/ü/ß.",
    },
]


def lint_file(path: Path) -> list[dict]:
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
    return _lint_text(content, file_label=str(path))


def _lint_text(content: str, file_label: str = "<string>") -> list[dict]:
    findings: list[dict] = []
    for line_num, line in enumerate(content.split("\n"), start=1):
        for rule in PATTERNS:
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
                })
    return findings


def check(text: str) -> dict:
    """Library API.

    Returns a dict with ``passed``, ``blocked`` (S1-level violations are
    blocking), ``violations`` (per-finding detail) and ``word_count``.
    """
    findings = _lint_text(text)
    by_sev: dict[str, list] = {}
    for f in findings:
        by_sev.setdefault(f["severity"], []).append(f)
    blocked = bool(by_sev.get("S1"))
    return {
        "passed": len(findings) == 0,
        "blocked": blocked,
        "violations": findings,
        "by_severity": {k: len(v) for k, v in by_sev.items()},
        "word_count": len(re.findall(r"\b\w+\b", text)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Marin Style-Lint — manuscript style-consistency check."
    )
    parser.add_argument("--file", help="Single file to lint", default=None)
    parser.add_argument("--text", help="Inline text to lint", default=None)
    parser.add_argument("--stdin", action="store_true",
                        help="Read text from stdin")
    parser.add_argument("--root", help="Root directory",
                        default=None)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on any finding")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # String mode
    if args.text or args.stdin:
        text = args.text if args.text else sys.stdin.read()
        result = check(text)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(
                f"Marin Style-Lint · words={result['word_count']}"
            )
            print(f"Status: passed={result['passed']} "
                  f"blocked={result['blocked']}\n")
            for v in result["violations"]:
                icon = "❗" if v["severity"] == "S1" else (
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
            for sev in ["S1", "S2", "S3", "ERROR"]:
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
    if args.strict and "S3" in by_sev:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
