---
name: ship-beads
description: >
  Autonomous end-to-end pipeline for shipping a groomed beads (bd) issue:
  claim → branch → plan → TDD implementation (goal-contract Opus builders)
  → adversarial review → verified PR → confession pass → close bead. Use
  whenever a goal
  condition or user message says to ship/work on/pick up a beads issue
  ("ship abc-42", "work on bead xyz-7", "pick up the groomed issues",
  "/goal … via the ship-beads skill"), in any repo with a .beads tracker.
  The counterpart to groom-beads: grooming writes the contract, this skill
  executes it.
---

# Ship a beads issue

Execute a groomed bead as a self-contained mission. The bead IS the briefing:
`bd show <id>` carries scope (description), approach (design), the finish
line (acceptance), and usually the goal condition (notes). This skill is
repo-agnostic — verify commands, branch rules, and product rules come from
the target repo's CLAUDE.md, never from memory.

Division of labor (the reason this pipeline exists): the orchestrating
session owns grounding, ambiguity resolution, contract-writing, judgment,
and independent verification; implementation is delegated to **Opus**
subagents (coding subagents are Opus, always — Sonnet builds are slower and
worse on real codebases). Two execution modes:

- **Delegated (default in interactive sessions, mandatory when the main
  loop is Fable):** fire one background Opus builder carrying the whole
  bead as a goal-style contract (step 3), verify its output independently,
  then run the review step. The main loop never edits app code.
- **Inline (autonomous /goal runs):** the session implements directly,
  delegating well-scoped legs; same contracts apply to any leg it fires.

## Step 0 — read the contract

- `bd show <id> --json`: read description, design, acceptance, notes, deps.
- Read the repo's CLAUDE.md for verify commands and standing rules; read the
  files the design names — including any CONTEXT.md or docs/adr/ entries it
  references (grooming deliberately persists durable decisions there and
  keeps the bead's design field as a pointer; skipping them means executing
  without the reasoning behind the contract).
- **If the bead has no acceptance criteria** (ungroomed): don't improvise a
  scope. If the user is present, run a compressed grooming pass with them
  (or point at groom-beads); if running autonomously, proceed only when the
  issue is genuinely trivial (typo-class) — otherwise stop and report that
  the bead needs grooming, which beats shipping the wrong thing.
- If the bead is blocked (`bd show` deps unresolved), stop and say so.

## Step 1 — claim and branch

- `bd update <id> --claim` (sets in_progress + assignee, idempotent).
- `git checkout main && git pull --ff-only origin main` — never branch off
  stale main; never commit to main. Branch name by type: `fix/…`, `feat/…`,
  `chore/…`, `refactor/…`.

## Step 2 — plan in the main loop

Turn the bead's design into a concrete step plan: files to touch, tests to
write first, what gets delegated vs. kept. Keep depth (architecture,
cross-cutting edits, anything requiring judgment) in the main loop; delegate
breadth (well-specified, independent implementation legs, mechanical sweeps).

## Step 3 — implement, test-first

TDD is the feedback loop, not a formality: write the failing test that
captures each acceptance criterion **before** the implementation, watch it
fail for the right reason, make it pass, refactor. Use the repo's own test
tiers and commands (from its CLAUDE.md). Two-speed loop: run the cheap gate
(analyze/typecheck/lint) constantly, the expensive tier (integration/smoke)
on code that clears it.

Delegation rules for implementation subagents:

- Model: **Opus** (`model: "opus"`) for anything that writes code. Sonnet
  for non-coding gathering/research legs; Haiku only for trivial mechanical
  lookups. An explicit model instruction from the user always wins.
- **Builder prompts are goal-style contracts** (per "Writing goal prompts"):
  - `DONE =` a measurable end state tied to the bead's acceptance criteria.
  - `PROVE IT =` exact commands + expected output, printed FRESH as the
    final actions. Language test caches don't count — for Go, tagged suites
    run with `-count=1` (or after `go clean -testcache`); a `(cached)`
    result is an unverified result.
  - `CONSTRAINTS =` what must not be weakened/faked: no test deletions or
    assertion weakening, red-test-first for every behavioral change (revert
    the fix, watch the new test fail, capture the output), expected values
    from outside the implementation, no AI attribution in any git artifact.
  - **Consumer-completeness sweep**, spelled out per repo: every consumer of
    each changed field/shape (API spec like openapi.yaml + regenerated
    types, DTOs, docs/ctx or equivalent living docs, smoke tests, scripts).
    The deliverable lists what the sweep found and did; "nothing else
    consumes it" only counts with the grep behind it.
  - Merge policy stated explicitly (default: stop at open PR, step 7).
  - Plus the usual contract lines: deliverable format, hard size cap, "your
    final message IS the deliverable", no nested subagents unless the task
    demands it.
- Fan out independent legs in one message and keep working the integration
  seam yourself; never idle while a subagent runs.
- Subagent output is untrusted until the main loop's own gate passes on it —
  run the build/tests yourself before relaying any claim; don't take "done"
  on faith.

Load the skill that matches the change (Skill tool) and follow it — e.g. the
repo's language/convention skill (siddhartha-flutter, siddhartha-go),
frontend/polish skills for UI work, tdd where installed. The bead's design
field may name the ones the grooming session considered relevant.

## Step 4 — adversarial review (before merge)

Run the `review-coordinator` skill against the diff — in delegated mode,
fire a separate review subagent (Opus allowed) that invokes the skill on
the OPEN PR; in inline mode, invoke it on the branch diff before the PR. A
separate skeptic beats self-checking: the implementer shares its own blind
spots. If the `review-coordinator` skill is not installed, do not fall back
to an ad-hoc self-review. Stop and ask the user for permission to install it
from https://github.com/BRO3886/skills, then run it once it is available.
Feed the review concrete adversarial angles from the diff (the lossy
boundaries, the "can this false-pass now" inversions of each fix). Fix
every confirmed finding, re-run the full gate, and only then move toward
merge; file non-blocking findings as beads so they don't evaporate. Review
lenses run on Sonnet at minimum (never Haiku); Opus is allowed for
correctness/security lenses.

## Step 5 — PR

- Invoke `make-pr-easy-to-review`: clean commit batches (conventional-commit
  titles), a description that leads with problem and root cause, reviewer
  guidance.
- PR title in plain English sentences — no conventional-commit prefix. Body
  via `--body-file` (never heredoc/inline). Reference the bead ("Closes
  <id>" / "Ships <id>").
- No AI attribution anywhere — no Co-Authored-By, no generated-with lines.

## Step 6 — verify and prove

Non-negotiable, and the goal-mode payload: run the repo's canonical suite
plus every check named in the bead's acceptance field, and **print the fresh
output**. The goal evaluator can only see what's in the transcript, and
long-run evidence gets compacted — so as the FINAL action, re-run the
canonical checks and print a compact proof summary (command → result), plus
`gh pr view --json url,state` and `bd show <id> --json` status. Report
faithfully: a red result is reported red, with output; never claim green
over a red, never weaken/skip/delete a test to get to green.

## Step 7 — merge policy

Default: leave the PR open for the human. Merge only when the goal condition
or the user explicitly says to, and then only after CI actually passes
(`gh pr view --json statusCheckRollup` / `gh run watch --exit-status`).
`gh pr merge <n> --merge` — never `--delete-branch` without explicit
approval.

## Step 8 — confession pass (delegated mode)

After a builder reports done (and before or just after merge), send it the
post-mortem confession prompt: what did you fake, shortcut, or do less
rigorously than the report implied — evidence authenticity, freshness
(test caches count), sweep completeness (which grep hits were dismissed
unread), test independence (where each expected value came from),
suppressed observations, cargo-culted steps, and claims asserted without a
backing check. Close any gap it confesses yourself (re-run the stale suite,
open the unread file) before treating the work as verified. This catches
what the review can't: the delta between what was reported and what was
actually run.

## Step 9 — close the bead

- `bd close <id> --reason "PR #N: <one line>"`.
- Stage the resulting `.beads/issues.jsonl` export inside the feature PR
  (close on the branch before the final commit) rather than an orphan chore
  commit.
- Respect repo-specific verification gates: e.g. a repo whose rules require
  on-device confirmation before a fix counts as verified gets "fix applied,
  awaiting verification" language. Closing the bead never overrides a repo's
  definition of verified.

## Multiple issues in one mission

Sequence, don't interleave: fully ship A (through step 6) before branching
B, so every branch cuts from fresh main and PRs don't stack. Respect `bd`
dependency order. Only the close-export may be batched if closes happened
after merges.
