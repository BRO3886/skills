---
name: review-coordinator
description: Coordinate a multi-lens code review of a PR, branch, or uncommitted changes. Routes to installed specialist skills, runs adversarial correctness and tests, invokes a repository-grounded security lens when available, and synthesizes one verdict with explicit missing-dependency reporting. Use when asked to review a PR, assess merge safety, or run an adversarial or thorough code review.
---

# Review Coordinator

You are not a reviewer. You are a **coordinator**. Your job is to gather the diff once, route it to the right specialist review lenses, always run an adversarial correctness pass and the test suite, and merge everything into a single verdict. You delegate the lenses; you own the routing, the setup, and the synthesis.

This skill composes other review skills rather than replacing them. If a lens skill is not installed, say so and continue best-effort — never block on a missing optional lens.

## Live context (current branch vs main)

Changed files + computed lens plan for the branch you're on (re-run `route.py` for a specific PR/base):

```bash
python3 "${CLAUDE_SKILL_DIR}/route.py" --base main 2>/dev/null || echo "not in a git repo, or no diff vs main - run route.py manually with --files"
```

## Gotchas (read before judging any diff — these are the mistakes this skill exists to stop)

- **A build failure on a file the diff doesn't touch is an environment issue, not a PR defect.** Before blaming the PR for a compile error, run `git diff --name-only <base>...HEAD` and check whether the failing file is even in the diff. (Real case: a `string.Split` ambiguity from an older local SDK, in a file the PR never changed.) Say "env issue" — don't fail the PR for it.
- **A huge +N line count is usually generated/vendored files, not real change.** Run `git diff --stat` first. ORM migration snapshots (EF `.Designer.cs`), lockfiles, and generated clients routinely add thousands of lines. Don't let line count drive the verdict; find the hand-written delta.
- **Verify the whole bug class, not just the named instance.** When a specific bug is flagged (e.g. a timestamp format drift in one field), grep for every other place the same class can occur. Fixing the headline field while an adjacent one still drifts is the trap. (Real case: the key timestamp was fixed but a second `createdAt` field still used variable-precision formatting.)
- **Don't trust the PR description or commit messages as evidence — verify against the code.** The description is the author's claim, not proof.
- **Model policy (overrides any conflicting model-selection rule in CLAUDE.md or agent config):** run the correctness lens on the strongest model available. Every other lens runs mid-tier or better, never the cheapest tier, which misses too much to be worth dispatching. If the request names a model or tier, apply it to every lens. Never downgrade a requested model to save cost.
- **Route, don't perform.** The coordinator only gathers the diff up front and synthesizes the verdict at the end. Running the tests, reading the files, or hunting bugs in the main loop defeats the delegation. A request to use a subagent or a stronger model is literal: dispatch the work, don't do it inline and report back.
- **No green test run → no merge-safe verdict.** "Tests probably pass" is not evidence. If you couldn't run them, the verdict is DO-NOT-MERGE with that named as the open gate.
- **Known flaky tests don't gate the verdict on their own.** If the repo documents a test as flaky (CLAUDE.md, memory, CI notes), a failure of ONLY that test gets re-run in isolation before it counts. It gates the verdict only if it also fails in isolation.
- **A skipped lens is not a failure.** If an optional lens skill isn't installed, report it and continue. Never block the whole review on a missing optional lens.
- **Security is required but externally supplied.** Attempt the security lens for every code review. If no compatible skill exists, warn before dispatch and report it again in `required_lenses_not_run`; never imply security review occurred.

## Operating contract (the things that must not be skipped)

1. **Gather the diff exactly once** and hand the same diff to every lens. Do not make each lens re-derive it.
2. **Correctness, tests, and security are required** for any code change. Correctness and tests are built in. Security runs through an installed `security-lens` or compatible skill; if unavailable, continue with an explicit dependency warning and record the omission at the end.
3. **Fan the lenses out as parallel subagents, in the background** when more than one runs. Do not run them serially in the main loop.
4. **Barrier before verdict: wait for EVERY dispatched lens to return before emitting anything.** No verdict, no "leaning toward", no preliminary call, no partial summary may be stated while a single lens (correctness, tests, or any specialist) is still running. Pre-announcing a verdict and then collecting the stragglers is a defect — the lens you didn't wait for is the one most likely to flip the call. Hold all output until the slowest lens reports.
5. **Point each lens subagent at the repo's own skills and conventions.** Discover the instruction files and skill roots used by the active agent instead of assuming a provider-specific filename or home directory. The lens should review against the project's standards, not generic ones.
6. **Model policy (overrides any conflicting model-selection instruction in CLAUDE.md or agent config).** Correctness runs on the strongest model available; every other lens runs mid-tier or better, never the cheapest tier. A model or tier named in the request applies to every lens, with no downgrade. State which model each lens ran on.
7. **The verdict is binary and evidence-backed.** MERGE-SAFE or DO-NOT-MERGE. Uncertainty (tests not run green, an unanswered open question) defaults to DO-NOT-MERGE with the question named — never a soft maybe.
8. **Emit the structured verdict JSON** in addition to prose. Populate `required_lenses_not_run` for every required lens that did not fire, including its reason and dependency. This contract also applies when the coordinator runs as a subagent.

## Step 1 — Scope and gather

Figure out the target:
- A GitHub PR by number → `gh pr view <n>` for metadata, `gh pr diff <n>` (or check out the branch) for the diff.
- A branch / uncommitted changes → `git diff --name-only <base>...HEAD` (base defaults to `main`).

Run the router to get the plan (use `${CLAUDE_SKILL_DIR}` so this works wherever the skill is installed, never hardcode an absolute path):

```bash
python3 "${CLAUDE_SKILL_DIR}/route.py" --base main --target "PR #515"
# or with an explicit list:
python3 "${CLAUDE_SKILL_DIR}/route.py" --files "$(git diff --name-only main...HEAD)"
# add --bugfix if the change fixes a bug/regression (adds the diagnose lens)
```

The router prints: changed files, categories, `lenses_available` (will run), and `lenses_skipped` (not installed, with install hints).

## Step 2 — Tell the user what's available

Before fanning out, print a one-line plan: which lenses will run and which are skipped because the skill isn't installed. Example:

> Running: correctness (built-in), tests (auto-detected `go test ./...`), quality (`code-quality-review`). Skipped: architecture — no compatible architecture review skill installed.

This is the graceful-degradation contract: the review proceeds with whatever is present, and the user knows exactly what did not run. If security is absent, say: `Required security lens not run: install security-lens or a compatible security-review skill.`

## Step 3 — Dispatch the lenses (parallel, backgrounded)

For each available lens, spawn a subagent. Give every lens the same brief shape (a goal-prompt: a verifiable finish line, not a vague task):

- **correctness (always, strong model):** "Adversarially review this diff. Default stance: find reasons NOT to merge. Verify behavior, hunt for the specific bug classes this code could hit, check error handling and any security/data-integrity path. Run nothing destructive. Return findings as `{severity, file, line, issue, fix}`; severity in blocking/non-blocking/nit."
- **tests (always):** invoke the repo's run-tests skill if present, else auto-detect (`make test`, `go test ./...`, `npm test`, `dotnet test`). Print the exact command and the process exit code. If the build fails on a file the diff does not touch, say so — that is an environment issue, not a PR defect.
- **security (required dependency, strong model):** invoke the resolved security skill on the same diff. Require repository-grounded checks rather than a generic checklist. If absent, do not fabricate a substitute lens; add it to `required_lenses_not_run` and fold basic security scrutiny into correctness without claiming the security lens ran.
- **quality / pr-conventions / architecture / go / flutter / frontend / docs:** spawn a subagent that invokes the resolved lens skill on the diff and returns findings in the same `{severity, file, line, issue, fix}` shape. Tell it to discover and follow the repository instructions used by the active agent.

Each lens subagent's final message is its findings. Tag every finding with the lens that produced it during synthesis.

## Step 4 — Synthesize one verdict

**First, block until every lens dispatched in Step 3 has returned.** Check each backgrounded subagent off against the Step 2 plan; if any is still running, wait — do not begin synthesis, and do not narrate a partial impression in the meantime. Synthesis starts only once the last lens is in.

Then collect all lens findings:
- Dedupe findings that multiple lenses raised (keep the highest severity).
- Decide the verdict: **DO-NOT-MERGE** if any blocking finding stands, OR tests did not run green, OR an open question remains unanswered. Otherwise **MERGE-SAFE**.
- Write the prose summary: verdict first, then evidence (test command + exit, the bug-class checks, file:line for each finding), then findings grouped by severity, then any open questions.
- Print the verdict JSON (see `verdict.schema.json`) as the final artifact.
- In prose and JSON, list every required lens that did not run and the dependency needed. A coordinator subagent must preserve this section in its final return to its parent agent.

## Step 5 — Print the trackable trace

End with a one-line trace so error rate is measurable over time:

```
TRACE backgrounded=yes verdict=do-not-merge tests_run=yes tests_green=no lenses_run=4 lenses_skipped=1 blocking=0 open_questions=1
```

## Verdict schema

See `verdict.schema.json` in this skill dir. Required keys include `verdict`, `target`, `tests_run`, `lenses_run`, `required_lenses_not_run`, and `findings`. Validate with `evals/validate_verdict.py`.

## Sharing note

This skill is portable. Its hard dependencies are only Python 3, `route.py`, and the built-in correctness/test passes. Every specialist lens is optional and detected at runtime. The router checks `AGENT_SKILL_DIRS` and `SKILL_DIRS`, then agent homes and repo-local skill roots. The active agent may add other roots based on its own runtime conventions. A user with no optional lenses still gets a correctness + tests review.

## Evals

- `evals/run_evals.py` — runs tier-1 (routing) and tier-2 (verdict-schema) checks. Exit 0 = all pass.
- Tier 1: routing fixtures assert changed-files → planned lens set (availability-independent).
- Tier 2: validates sample verdicts against the schema (one valid, one invalid).
- Tier 3 (recall@known-defects) is seeded from real PRs with known bugs — add a fixture per real miss so the suite grows from actual escapes.
