#!/usr/bin/env python3
"""Score triggering evals for the review-coordinator skill.

Triggering is nondeterministic, so the workflow is:
  1. For each query in fixtures/triggering.json, ask the skill-router model
     (given ONLY the installed skills' name+description and the query) whether
     review-coordinator would fire. Repeat N times (~3).
  2. Record the booleans in a results file: { "st1": [true,true,false], ... }.
  3. Run this scorer over fixtures + results.

Pass rule (from Skill creation best practices §5):
  should_trigger == true  -> passes if trigger-rate > 0.5
  should_trigger == false -> passes if trigger-rate < 0.5

Reports train and val accuracy separately (val is the held-out, honest number).
Exit 0 if every VAL query passes, else 1.

The scoring math is pure/importable so run_evals.py can self-test it.
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FIXTURES = os.path.join(HERE, "fixtures", "triggering.json")


def rate(bools):
    if not bools:
        return 0.0
    return sum(1 for b in bools if b) / len(bools)


def score(fixtures, results):
    """Pure: -> list of per-query dicts with rate + pass flag."""
    rows = []
    for q in fixtures["queries"]:
        runs = results.get(q["id"], [])
        r = rate(runs)
        if q["should_trigger"]:
            passed = r > 0.5
        else:
            passed = r < 0.5
        rows.append({
            "id": q["id"],
            "should_trigger": q["should_trigger"],
            "split": q["split"],
            "runs": len(runs),
            "rate": round(r, 3),
            "passed": passed,
        })
    return rows


def accuracy(rows, split):
    sub = [r for r in rows if r["split"] == split]
    if not sub:
        return None
    return sum(1 for r in sub if r["passed"]) / len(sub)


def main():
    if len(sys.argv) < 2:
        print("usage: score_triggering.py <results.json> [fixtures.json]", file=sys.stderr)
        print("results.json maps query id -> list of trigger booleans, e.g. {\"st1\":[true,true,false]}", file=sys.stderr)
        sys.exit(2)
    results = json.load(open(sys.argv[1], encoding="utf-8"))
    fx_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_FIXTURES
    fixtures = json.load(open(fx_path, encoding="utf-8"))

    rows = score(fixtures, results)
    for r in rows:
        flag = "PASS" if r["passed"] else "FAIL"
        kind = "should-fire " if r["should_trigger"] else "should-NOT  "
        miss = "" if r["runs"] else "  (no runs recorded)"
        print(f"  [{flag}] {kind} {r['id']:<5} rate={r['rate']:<5} split={r['split']}{miss}")

    tr, va = accuracy(rows, "train"), accuracy(rows, "val")
    print(f"\ntrain accuracy: {tr if tr is None else round(tr,3)}")
    print(f"val accuracy:   {va if va is None else round(va,3)}  (held-out — the honest number)")

    val_rows = [r for r in rows if r["split"] == "val"]
    if val_rows and all(r["passed"] for r in val_rows):
        print("\nVAL: all passed")
        sys.exit(0)
    print("\nVAL: failures present")
    sys.exit(1)


if __name__ == "__main__":
    main()
