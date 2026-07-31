#!/usr/bin/env python3
"""Grade one security-lens run against a fixture's expected.json.

Pure and importable — run_evals.py uses it, and you can grade a manual run:
  python3 grade.py fixtures/01-missing-authorize/expected.json findings.json

Pass criteria:
  should_find:  every expected {check, file} pair matched by at least one
                reported finding with the same check number and a file path
                containing the expected file substring.
  expect_clean: zero findings of severity blocking/non-blocking (nits allowed —
                a nit on a clean fixture is noise, not a false positive).
"""
from __future__ import annotations
import json
import sys


def grade(findings, expected):
    """Return a list of error strings; empty = pass."""
    errors = []
    findings = findings or []

    if expected.get("expect_clean"):
        real = [f for f in findings
                if f.get("severity") in ("blocking", "non-blocking")]
        for f in real:
            errors.append(
                f"false positive on clean fixture: check={f.get('check')} "
                f"file={f.get('file')} issue={str(f.get('issue'))[:120]}")
        return errors

    for want in expected.get("should_find", []):
        hit = any(
            f.get("check") == want["check"]
            and want["file"] in (f.get("file") or "")
            for f in findings
        )
        if not hit:
            got = [(f.get("check"), f.get("file")) for f in findings]
            errors.append(
                f"missed: check={want['check']} file~={want['file']} "
                f"(reported: {got or 'nothing'})")
    return errors


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    expected = json.load(open(sys.argv[1], encoding="utf-8"))
    findings = json.load(open(sys.argv[2], encoding="utf-8"))
    errors = grade(findings, expected)
    for e in errors:
        print("FAIL", e)
    print("PASS" if not errors else f"{len(errors)} failure(s)")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
