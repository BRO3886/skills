#!/usr/bin/env python3
"""Eval harness for the review-coordinator skill.

Tier 1 (routing): assert changed-files -> planned lens set, availability-independent.
Tier 2 (verdict-schema): assert the validator accepts a good verdict and rejects a bad one.

Deterministic, stdlib-only. Exit 0 = all pass, 1 = any failure.
Run: python3 evals/run_evals.py
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)


def _load(modname, path):
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


route = _load("route", os.path.join(SKILL_DIR, "route.py"))
validator = _load("validate_verdict", os.path.join(HERE, "validate_verdict.py"))
scorer = _load("score_triggering", os.path.join(HERE, "score_triggering.py"))


def tier1_routing():
    fixtures_path = os.path.join(HERE, "fixtures", "routing.json")
    fixtures = json.load(open(fixtures_path, encoding="utf-8"))
    passed, failed = 0, 0
    for fx in fixtures:
        got, _tags = route.plan_lenses(fx["files"], bugfix=fx.get("bugfix", False))
        want = fx["expect_lenses"]
        # order-independent comparison
        if sorted(got) == sorted(want):
            passed += 1
        else:
            failed += 1
            print(f"  FAIL [{fx['name']}]")
            print(f"       want: {sorted(want)}")
            print(f"       got:  {sorted(got)}")
    print(f"tier1 routing: {passed} passed, {failed} failed (of {len(fixtures)})")
    return failed == 0


def tier2_schema():
    sv = os.path.join(HERE, "sample_verdicts")
    failed = 0

    valid_obj = json.load(open(os.path.join(sv, "valid.json"), encoding="utf-8"))
    errs = validator.validate(valid_obj)
    if errs:
        failed += 1
        print(f"  FAIL [valid.json] expected valid, got errors: {errs}")
    else:
        print("  OK   [valid.json] accepted")

    invalid_obj = json.load(open(os.path.join(sv, "invalid.json"), encoding="utf-8"))
    errs = validator.validate(invalid_obj)
    if not errs:
        failed += 1
        print("  FAIL [invalid.json] expected rejection, but it passed")
    else:
        print(f"  OK   [invalid.json] rejected ({len(errs)} error(s))")

    print(f"tier2 schema: {'all passed' if failed == 0 else f'{failed} failed'}")
    return failed == 0


def tier2b_scorer_math():
    """Deterministic check of the triggering scorer's math against hand-computed
    rates. This verifies the SCORER, not trigger quality (which needs model runs)."""
    fixtures = json.load(open(os.path.join(HERE, "fixtures", "triggering.json"), encoding="utf-8"))
    results = json.load(open(os.path.join(HERE, "sample_triggering_results.json"), encoding="utf-8"))
    rows = {r["id"]: r for r in scorer.score(fixtures, results)}
    failed = 0
    expect = {
        "st1": (1.0, True),    # [T,T,T] should-fire -> pass
        "st4": (0.667, True),  # [T,F,T] should-fire -> pass
        "sn1": (0.0, True),    # [F,F,F] should-not -> pass
        "sn7": (0.333, True),  # [T,F,F] should-not, rate<0.5 -> pass
    }
    for qid, (want_rate, want_pass) in expect.items():
        got = rows[qid]
        if abs(got["rate"] - want_rate) > 0.001 or got["passed"] != want_pass:
            failed += 1
            print(f"  FAIL [{qid}] want rate={want_rate} pass={want_pass}, got rate={got['rate']} pass={got['passed']}")
    # sample is constructed so every val query passes
    val_all_pass = all(r["passed"] for r in rows.values() if r["split"] == "val")
    if not val_all_pass:
        failed += 1
        print("  FAIL sample val set should all pass")
    print(f"tier2b triggering-scorer math: {'all passed' if failed == 0 else f'{failed} failed'}")
    return failed == 0


def main():
    print("=== review-coordinator evals ===")
    ok1 = tier1_routing()
    ok2 = tier2_schema()
    ok3 = tier2b_scorer_math()
    if ok1 and ok2 and ok3:
        print("\nALL EVALS PASSED")
        sys.exit(0)
    print("\nEVAL FAILURES PRESENT")
    sys.exit(1)


if __name__ == "__main__":
    main()
