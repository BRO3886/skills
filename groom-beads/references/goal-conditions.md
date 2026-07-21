# Writing /goal conditions for groomed beads

Distilled from a "writing goal prompts" reference. The essentials the grooming
session must bake into every emitted condition:

## The core reframe

A goal is a **condition the evaluator can verify**, not instructions for the
worker. The evaluator is a separate small model that only reads the session
transcript — it cannot run commands or read files. The worker knows it's
being graded and will take the laziest literal reading. Write the finish
line, not the steps.

One-line test: *can a model that only reads the transcript point at one piece
of output and say yes or no?* If not, it's a prompt, not a goal.

## Anatomy (all three parts, always)

- **DONE** — one measurable end state (test exit code, PR state, `bd show
  <id> --json` status, file count). Binary, never subjective.
- **PROVE IT** — the exact command(s) and expected output, printed in the
  transcript. Evidence that only exists on disk doesn't exist for the
  evaluator.
- **CONSTRAINTS** — what must NOT be touched/faked/weakened on the way. This
  is the anti-gaming layer; it grows from real escapes over time.

Hard limit: 4000 characters. If it doesn't fit, the goal is over-scoped —
push the briefing onto the bead (`bd show <id>` is the READ-FIRST file that
survives across sessions) and keep the condition to the three lines.

## The worker needs a local feedback loop

The evaluator grades the finish line, but what gets the worker there is a
check **it can run itself, locally, every turn, and watch fail→pass**:

- The proof check must be locally runnable — not only in CI or the cloud. If
  the only evidence is "works once deployed", the worker guesses and stops
  early. For cloud/external dependencies, require a local stand-in (injected
  port + mock, containerized smoke).
- Bake red-green in: require the failing test first, then implementation,
  then green. A condition that only says "tests pass" lets the worker write
  the test last, to fit whatever it built.
- Forbid declaring done on stale evidence: the final action must re-run the
  canonical checks and print FRESH output (long runs get compacted; evidence
  that scrolled off doesn't count).
- Two-speed loop: cheap gate every turn (analyze/typecheck/lint), expensive
  oracle (integration/smoke) only on code that clears the gate.

## Kill the shortcuts (assume the worker will cheat)

- The worker must never be able to edit what grades it: no weakening or
  deleting tests, no skips/xfail, no hardcoding expected values, no touching
  scorer/CI config. Say so explicitly.
- Prefer invariants and repo-existing/externally-authored tests over fixed
  I/O pairs the worker can memorize, and over tests the worker wrote to fit
  its own code.
- Anchor DONE on a composed check (integration/smoke), not only unit tests —
  the gap between them is where gamed solutions hide.
- Verify the thing you care about, not a proxy ("build exits 0" ≠ "feature
  works"). Run a quick "how would this get gamed?" pass before finalizing:
  misweighting, measuring a stand-in, or wrong input slice.
- A separate skeptic beats self-checking — that's why ship-beads runs an
  adversarial review pass; the condition can require it ("review-coordinator
  verdict printed").

## Template

```
Ship bead <id> via the ship-beads skill. Full scope/design/acceptance: bd show <id>.
DONE = branch pushed + PR open (do not merge) + all acceptance criteria in
  bd show <id> demonstrably met + bd show <id> --json prints status "closed".
PROVE IT = print, as the FINAL action, fresh output of: <repo's canonical
  test command>; <the issue-specific check(s) from the bead's acceptance
  field>; gh pr view --json url,state; bd show <id> --json | jq .status.
CONSTRAINTS = follow ship-beads (TDD: failing test first; adversarial review
  before PR). Do not modify or skip existing tests, no xfail/skip, no
  hardcoded expected values, no pushes to main, no --delete-branch. If a
  check fails, fix and re-run — never report done over a red.
```

Adjust DONE per repo/appetite (e.g. "+ merged after CI green" where
auto-merge is wanted). Sequenced batches: one condition listing ids in order,
with "fully ship A before starting B".
