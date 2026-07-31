#!/usr/bin/env python3
"""Agent-in-the-loop evals for the security-lens skill.

For each fixture, invokes a user-supplied headless agent command, applies the
security-lens skill in diff mode, parses the findings JSON, and grades it
against expected.json (see grade.py). The prompt is passed on standard input.

Each fixture run is a real agent invocation and costs tokens. Model behavior is
nondeterministic, so use --runs 3 and judge by pass fraction: a fixture passes
overall when >= half its runs pass (the trigger-rate method).

Usage:
  python3 run_evals.py                     # all fixtures, 1 run each (smoke)
  python3 run_evals.py --runs 3            # full eval
  python3 run_evals.py --fixture 02        # substring filter
  python3 run_evals.py --command 'agent-cli --print'

Requires: `--command` or `AGENT_EVAL_COMMAND` naming a headless agent command
that accepts a prompt on standard input.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")

sys.path.insert(0, HERE)
from grade import grade  # noqa: E402

PROMPT_TEMPLATE = """Read the skill file {skill_md} and apply it in DIFF MODE to the diff below.

Rules for this run:
- The diff is the entire changeset under review. You may read existing repo files for surrounding context, but do NOT run tests, do NOT modify anything.
- Report ONLY findings the skill's checklist and ground rules justify.
- Your FINAL output must be ONLY a JSON array of findings, no prose before or after:
  [{{"check": <1-12>, "severity": "blocking|non-blocking|nit", "file": "<path>", "line": <int|null>, "issue": "<one sentence>", "fix": "<one sentence>"}}]
- If there are no findings, output exactly: []

--- DIFF UNDER REVIEW ---
{diff}
"""


def extract_json_array(text):
    """Pull the last top-level JSON array out of possibly-noisy output."""
    candidates = []
    depth, start = 0, None
    for i, ch in enumerate(text):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start:i + 1])
    for cand in reversed(candidates):
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def run_once(fixture_dir, command, timeout):
    diff = open(os.path.join(fixture_dir, "diff.patch"), encoding="utf-8").read()
    skill_md = os.path.join(SKILL_DIR, "SKILL.md")
    prompt = PROMPT_TEMPLATE.format(skill_md=skill_md, diff=diff)
    cmd = shlex.split(command)
    try:
        out = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    if out.returncode != 0:
        return None, f"agent command exited {out.returncode}: {out.stderr[:200]}"
    findings = extract_json_array(out.stdout)
    if findings is None:
        return None, f"no JSON array in output: {out.stdout[:200]!r}"
    return findings, None


def main():
    ap = argparse.ArgumentParser(description="Run security-lens identification evals.")
    ap.add_argument("--runs", type=int, default=1, help="runs per fixture (default 1; use 3 for a real eval)")
    ap.add_argument("--fixture", default="", help="substring filter on fixture dir name")
    ap.add_argument("--command", default=os.environ.get("AGENT_EVAL_COMMAND", ""),
                    help="headless agent command; prompt is passed on stdin")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per run (default 600)")
    args = ap.parse_args()
    if not args.command:
        ap.error("provide --command or set AGENT_EVAL_COMMAND")

    dirs = sorted(
        d for d in os.listdir(FIXTURES)
        if os.path.isdir(os.path.join(FIXTURES, d)) and args.fixture in d
    )
    if not dirs:
        print(f"no fixtures matching {args.fixture!r}")
        sys.exit(2)

    overall_pass, overall_fail = 0, 0
    for d in dirs:
        fdir = os.path.join(FIXTURES, d)
        expected = json.load(open(os.path.join(fdir, "expected.json"), encoding="utf-8"))
        passes = 0
        for i in range(args.runs):
            findings, err = run_once(fdir, args.command, args.timeout)
            if err:
                print(f"  [{d}] run {i + 1}: ERROR {err}")
                continue
            errors = grade(findings, expected)
            if errors:
                print(f"  [{d}] run {i + 1}: FAIL " + "; ".join(errors))
            else:
                passes += 1
                print(f"  [{d}] run {i + 1}: pass")
        rate = passes / args.runs
        ok = rate >= 0.5
        overall_pass += ok
        overall_fail += (not ok)
        print(f"{'PASS' if ok else 'FAIL'} [{d}] pass rate {passes}/{args.runs}")

    print(f"\nfixtures: {overall_pass} passed, {overall_fail} failed (of {len(dirs)}), runs per fixture: {args.runs}")
    sys.exit(0 if overall_fail == 0 else 1)


if __name__ == "__main__":
    main()
