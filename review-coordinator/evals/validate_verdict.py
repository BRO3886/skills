#!/usr/bin/env python3
"""Minimal stdlib validator for review-coordinator verdict JSON.

No jsonschema dependency — just enough to enforce the contract the synthesis
step must produce. Exit 0 = valid, 1 = invalid (reasons printed to stderr).
"""
from __future__ import annotations
import json
import sys

VERDICTS = {"merge-safe", "do-not-merge"}
SEVERITIES = {"blocking", "non-blocking", "nit"}


def validate(obj):
    errors = []
    if not isinstance(obj, dict):
        return ["top-level value is not an object"]

    for key in ("verdict", "target", "tests_run", "lenses_run", "required_lenses_not_run", "findings"):
        if key not in obj:
            errors.append(f"missing required key: {key}")

    if "verdict" in obj and obj["verdict"] not in VERDICTS:
        errors.append(f"verdict must be one of {sorted(VERDICTS)}, got {obj.get('verdict')!r}")
    if "target" in obj and not (isinstance(obj["target"], str) and obj["target"].strip()):
        errors.append("target must be a non-empty string")
    if "tests_run" in obj and not isinstance(obj["tests_run"], bool):
        errors.append("tests_run must be a boolean")
    if "tests_green" in obj and not (isinstance(obj["tests_green"], bool) or obj["tests_green"] is None):
        errors.append("tests_green must be boolean or null")
    if "lenses_run" in obj and not isinstance(obj["lenses_run"], list):
        errors.append("lenses_run must be an array")

    missing_required = obj.get("required_lenses_not_run")
    if missing_required is not None:
        if not isinstance(missing_required, list):
            errors.append("required_lenses_not_run must be an array")
        else:
            for i, item in enumerate(missing_required):
                if not isinstance(item, dict):
                    errors.append(f"required_lenses_not_run[{i}] is not an object")
                    continue
                for key in ("lens", "reason", "dependency"):
                    if not (isinstance(item.get(key), str) and item[key].strip()):
                        errors.append(f"required_lenses_not_run[{i}].{key} must be a non-empty string")

    findings = obj.get("findings")
    if findings is not None:
        if not isinstance(findings, list):
            errors.append("findings must be an array")
        else:
            for i, f in enumerate(findings):
                if not isinstance(f, dict):
                    errors.append(f"findings[{i}] is not an object")
                    continue
                for k in ("severity", "lens", "issue"):
                    if k not in f:
                        errors.append(f"findings[{i}] missing required key: {k}")
                if "severity" in f and f["severity"] not in SEVERITIES:
                    errors.append(f"findings[{i}].severity must be one of {sorted(SEVERITIES)}, got {f['severity']!r}")
                if "issue" in f and not (isinstance(f["issue"], str) and f["issue"].strip()):
                    errors.append(f"findings[{i}].issue must be a non-empty string")

    # invariant: a merge-safe verdict cannot carry a blocking finding
    if obj.get("verdict") == "merge-safe" and isinstance(findings, list):
        if any(isinstance(f, dict) and f.get("severity") == "blocking" for f in findings):
            errors.append("verdict is merge-safe but a blocking finding is present")

    return errors


def main():
    if len(sys.argv) != 2:
        print("usage: validate_verdict.py <verdict.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as fh:
        obj = json.load(fh)
    errors = validate(obj)
    if errors:
        for e in errors:
            print(f"INVALID: {e}", file=sys.stderr)
        sys.exit(1)
    print("valid")
    sys.exit(0)


if __name__ == "__main__":
    main()
