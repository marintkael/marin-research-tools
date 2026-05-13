#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
#
# source_attribution_parser.py
#
# Python port of the Cross-LLM Trust Graph source-attribution parser
# (originally written in JavaScript for the Cloudflare-Workers research
# pipeline; one-to-one mirror of that logic for offline replication).
#
# Twelve source patterns are matched against an LLM answer with a fixed
# trust-weight hierarchy:
#
#     +2  wikipedia / wikidata / orcid / zenodo     verifiable primary
#     +1  goodreads / amazon / official_site /
#          github                                    semi-authoritative
#      0  press / reddit / no_source                 neutral
#     -1  inference                                  hallucination risk
#
# The output is a list of dicts compatible with the D1 / SQLite schema
# in migrations/0003_ai_citation_sources.sql:
#
#     {llm, question_id, source_type, mentioned, trust_weight}
#
# CLI usage (single answer from stdin):
#
#     echo "According to Wikipedia and ORCID, the author ..." | \
#       python3 source_attribution_parser.py --llm openai --question D1
#
# Library usage:
#
#     from source_attribution_parser import parse_sources
#     rows = parse_sources(answer_text, llm_id="claude", question_id="D2")
#
# Used by pre-registration Q3 (Cross-LLM Trust Graph drift, 12 patterns x
# 9 LLMs over 90 days) to derive the source x LLM heatmap and the
# trust-score-distribution-per-model curve.

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import List, Pattern


@dataclass(frozen=True)
class SourcePattern:
    type: str
    weight: float
    regex: Pattern[str]


# Pattern order mirrors the JavaScript reference implementation 1:1.
# Regex flags: re.IGNORECASE everywhere (the JS source uses /.../i).
SOURCE_PATTERNS: List[SourcePattern] = [
    SourcePattern(
        type="wikipedia",
        weight=2,
        regex=re.compile(r"\bwikipedia\b", re.IGNORECASE),
    ),
    SourcePattern(
        type="wikidata",
        weight=2,
        regex=re.compile(
            r"\bwikidata\b|\bq139720807\b|\bq139720798\b",
            re.IGNORECASE,
        ),
    ),
    SourcePattern(
        type="orcid",
        weight=2,
        regex=re.compile(r"\borcid\b|0009-0006-2105-8190", re.IGNORECASE),
    ),
    SourcePattern(
        type="zenodo",
        weight=2,
        regex=re.compile(r"\bzenodo\b|10\.5281\/zenodo", re.IGNORECASE),
    ),
    SourcePattern(
        type="goodreads",
        weight=1,
        regex=re.compile(r"\bgoodreads\b", re.IGNORECASE),
    ),
    SourcePattern(
        type="amazon",
        weight=1,
        regex=re.compile(
            r"\bamazon\b|\bkindle\s+direct\b|\bkdp\b",
            re.IGNORECASE,
        ),
    ),
    SourcePattern(
        type="official_site",
        weight=1,
        regex=re.compile(
            r"marin-t-kael\.de|\bmarin\s+t\.?\s+kael[' ]?s?\s+website\b",
            re.IGNORECASE,
        ),
    ),
    SourcePattern(
        type="github",
        weight=1,
        regex=re.compile(
            r"github\.com\/marintkael|\bgithub\b",
            re.IGNORECASE,
        ),
    ),
    SourcePattern(
        type="press",
        weight=0,
        regex=re.compile(
            r"\bpresse(mitteilung)?\b|\bpress[- ]release\b|\binterview\b",
            re.IGNORECASE,
        ),
    ),
    SourcePattern(
        type="reddit",
        weight=0,
        regex=re.compile(r"\breddit\b|\br\/[a-z]", re.IGNORECASE),
    ),
    SourcePattern(
        type="inference",
        weight=-1,
        regex=re.compile(
            r"\beigene\s+inferenz\b"
            r"|\bown\s+inference\b"
            r"|\bbased\s+on\s+(my\s+)?training\s+data\b"
            r"|\bi\s+don'?t\s+have\s+(specific\s+)?information\b"
            r"|\bi\s+am\s+not\s+(sure|certain|aware)\b"
            r"|\bverm[uü]tlich\b"
            r"|\bpresumably\b"
            r"|\bI\s+have\s+no\s+(specific\s+)?(data|information)\b"
            r"|\bI\s+do\s+not\s+have\s+(specific\s+)?(data|information)\b"
            r"|\bnicht\s+bekannt\b",
            re.IGNORECASE,
        ),
    ),
]


def parse_sources(answer: str, llm_id: str, question_id: str) -> list[dict]:
    """Parse a single LLM answer into source-attribution rows.

    Mirrors parseSources() in the JS reference implementation.

    Parameters
    ----------
    answer : str
        Raw LLM answer text. Empty or None returns an empty list.
    llm_id : str
        Identifier of the answering LLM (e.g. 'openai', 'claude',
        'mistral', 'llama3'). Stored as-is on every row.
    question_id : str
        Identifier of the question in the daily Cross-LLM Trust Graph
        run (e.g. 'D1', 'G2', 'R1'). Stored as-is on every row.

    Returns
    -------
    list[dict]
        Zero or more rows of the shape
        ``{llm, question_id, source_type, mentioned, trust_weight}``.
        If no pattern matches, exactly one row of type 'no_source' with
        ``mentioned=False`` and ``trust_weight=0`` is returned.
    """
    rows: list[dict] = []
    if not answer:
        return rows

    any_matched = False
    for p in SOURCE_PATTERNS:
        if p.regex.search(answer):
            rows.append(
                {
                    "llm": llm_id,
                    "question_id": question_id,
                    "source_type": p.type,
                    "mentioned": True,
                    "trust_weight": p.weight,
                }
            )
            any_matched = True

    if not any_matched:
        rows.append(
            {
                "llm": llm_id,
                "question_id": question_id,
                "source_type": "no_source",
                "mentioned": False,
                "trust_weight": 0,
            }
        )

    return rows


def _main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse a single LLM answer (read from stdin) into source-"
            "attribution rows compatible with the Cross-LLM Trust Graph "
            "schema."
        )
    )
    parser.add_argument(
        "--llm",
        required=True,
        help="Identifier of the answering LLM (e.g. openai, claude).",
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Question identifier (e.g. D1, G2, R1).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output.",
    )
    args = parser.parse_args()

    answer = sys.stdin.read()
    rows = parse_sources(
        answer=answer,
        llm_id=args.llm,
        question_id=args.question,
    )
    if args.pretty:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
