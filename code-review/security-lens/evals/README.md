# security-lens evals

Regression suite for the security lens's *identification quality*: does it still
find the vulnerability classes it exists to catch, and does it still stay quiet
on the patterns this repo explicitly allows?

## How it works

Each fixture under `fixtures/` is one frozen review scenario:

- `diff.patch` — a realistic diff against real repo paths, containing either a
  planted vulnerability or deliberately-clean code.
- `expected.json` — the ground truth: `should_find` lists `{check, file}` pairs
  the lens must report (check = the checklist number in SKILL.md), or
  `expect_clean: true` for false-positive traps.

`run_evals.py` feeds each diff to a user-supplied headless agent command applying
the skill in diff mode, extracts the findings JSON, and `grade.py` compares it
to the ground truth. Because agent output is nondeterministic, run each fixture
3 times and judge by pass fraction (>= 0.5 passes overall).

## Fixture types

- **Synthetic canaries** (01–05): minimal planted violations, one per high-value
  checklist item — missing `[Authorize]`, non-constant-time PIN compare,
  unsanitized `dangerouslySetInnerHTML`, `FromSqlRaw` interpolation, missing
  `[AuditRedact]` on new PII.
- **Reversed safeguard** (06): an existing protection (the portal host allowlist
  gate) removed — models the "regression reintroduces an old vuln" case.
- **False-positive traps** (07–08): clean diffs baited with the lens's ground
  rules (no firm scoping, startup DDL raw SQL). These protect precision — a lens
  that cries wolf gets ignored.

## Running

```bash
# deterministic pieces only (free, instant)
python3 grade.py fixtures/01-missing-authorize/expected.json some-findings.json

# one smoke run per fixture (8 agent invocations)
python3 run_evals.py --command 'agent-cli --print'

# real eval: 3 runs per fixture (24 agent invocations — token cost is real)
AGENT_EVAL_COMMAND='agent-cli --print' python3 run_evals.py --runs 3

# iterate cheaply on one fixture
python3 run_evals.py --fixture 02 --command 'agent-cli --print'
```

## Growing the suite

When the lens misses a real issue in a real PR (an escape), add a fixture
reproducing it — that's how the suite tracks actual failure modes instead of
imagined ones. Same when it produces a false positive someone had to argue down:
freeze that diff as an `expect_clean` trap.
