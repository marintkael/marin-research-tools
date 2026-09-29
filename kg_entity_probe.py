#!/usr/bin/env python3
"""Probe the Google Knowledge Graph Search API for a name and print every result it returns.

Why this exists. A daily visibility stage in this project asked the Knowledge Graph Search API
whether an entity resolves, and stored the answer as a count of results. That count is not a
measurement. The endpoint returns a ranked list whose tail is padding: in the run of 2026-09-29 a
query for one author name returned four results, two of them distinct machine ids for that name
(resultScore 43 each) and the third an unrelated bird at resultScore 0.0374. Three orders of
magnitude inside one response is a ranking signal, not a probability, and it is not comparable
across queries.

What to store instead, per query: the top id, its score, how many results cleared an explicit
score floor, and the date the top id was first seen. The last column is the useful one, because an
id that quietly swaps is invisible to every other field. Duplicate ids for one name matter for the
same reason: downstream consumers pick one of them, and a count cannot show that there were two.

Usage:
    KG_API_KEY=... python3 kg_entity_probe.py "Some Author Name" [--floor 1.0] [--json]

The API key is read from the environment only. Nothing is written anywhere.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

ENDPOINT = "https://kgsearch.googleapis.com/v1/entities:search"
DEFAULT_FLOOR = 1.0     # arbitrary, and say so in whatever report consumes this


def probe(query, key, limit=10, timeout=20):
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"query": query, "key": key, "limit": limit, "indent": "false"})
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def rows(payload):
    out = []
    for item in payload.get("itemListElement", []) or []:
        res = item.get("result", {}) or {}
        out.append({
            "score": item.get("resultScore"),
            "id": res.get("@id"),
            "name": res.get("name"),
            "description": res.get("description"),
            "types": res.get("@type"),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--floor", type=float, default=DEFAULT_FLOOR,
                    help="score floor for the 'cleared' count (arbitrary by nature)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    key = os.environ.get("KG_API_KEY")
    if not key:
        raise SystemExit("KG_API_KEY not set in the environment")

    r = rows(probe(a.query, key, a.limit))
    cleared = [x for x in r if (x["score"] or 0) >= a.floor]
    ids_for_name = sorted({x["id"] for x in cleared
                           if (x["name"] or "").strip().lower() == a.query.strip().lower()})

    if a.json:
        print(json.dumps({
            "query": a.query,
            "returned": len(r),
            "floor": a.floor,
            "cleared": len(cleared),
            "top_id": cleared[0]["id"] if cleared else None,
            "top_score": cleared[0]["score"] if cleared else None,
            "distinct_ids_for_exact_name": ids_for_name,
            "results": r,
        }, ensure_ascii=False, indent=1))
        return

    print("query: %s" % a.query)
    print("returned %d, cleared floor %.4g: %d" % (len(r), a.floor, len(cleared)))
    for x in r:
        s = x["score"]
        print("  %-12s %-22s %-28s %s" % (
            ("%.4g" % s) if isinstance(s, (int, float)) else str(s),
            x["id"] or "-", (x["name"] or "-")[:28], x["description"] or ""))
    if len(ids_for_name) > 1:
        print("\nNOTE: %d distinct ids carry this exact name: %s" % (len(ids_for_name), ", ".join(ids_for_name)))
        print("A single count or a present/absent boolean cannot show this. Consumers pick one.")
    if not r:
        print("\nNOTE: zero results is a usable state, not a failure. It separates 'name resolves'")
        print("from 'work resolves' if you probe both, which one boolean would fuse.")


if __name__ == "__main__":
    sys.exit(main())
