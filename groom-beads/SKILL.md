---
name: groom-beads
description: >
  Interactive grooming session that takes raw beads (bd) issues or epics and
  turns them into self-contained, ship-ready work contracts — then emits a
  ready-to-paste /goal condition for executing them in a later session. Use
  whenever the user wants to groom, refine, scope, or prep beads issues
  ("groom abc-42", "grooming session", "make these ready to pick", "prep this
  epic", "let's scope the backlog", "get these issues ready for /goal"), or
  wants to turn vague backlog items into something an autonomous session can
  ship. Run this in an interactive chat — ideally on the strongest available
  model — NOT inside an autonomous/goal run.
---

# Groom beads issues

Turn raw beads issues into contracts a *different, context-free session* can
ship autonomously. That future session (see the `ship-beads` skill) will have
nothing but the bead and the repo — no memory of this conversation. Everything
that matters must therefore land **on the bead itself**, and the finish line
must be verifiable by a goal-mode evaluator that can only read a transcript.

This is a thinking-partner session, not a form-filling exercise. The model
doing the grooming carries the reasoning load — challenge scope, propose
splits, spot missing constraints — which is why grooming runs interactively on
a strong model while implementation is later delegated to cheaper ones.

## Phase 0 — intake and homework (before asking anything)

1. Resolve the targets: ids from the user's message, else propose candidates
   from `bd ready --sort priority` / `bd list --status open --pretty`. For an
   epic, `bd show <id>` and enumerate its children.
2. Read each bead fully: `bd show <id> --json` (description, design,
   acceptance, notes, deps, labels).
3. **Explore the codebase before asking questions.** Read the files the issue
   touches, the tests that cover them, the repo's CLAUDE.md verify commands.
   A question the code can answer is wasted user time; codebase exploration
   also surfaces contradictions worth grilling ("the issue says X but the code
   already does Y — what's actually wanted?").

## Phase 1 — grill, one question at a time

Invoke the `grill-with-docs` skill (Skill tool) and run the interview by its
rules — one question per turn, always with your recommended answer, explore
the codebase instead of asking when the code can answer, challenge terms
against the existing glossary. Don't re-implement the interview style from
memory; that skill is its canonical home.

One precedence rule on top of it, because this session has two write-back
targets: **the bead is the executor's contract and always gets the outcome**
(Phase 2 below); CONTEXT.md and ADRs are the *durable* record and get updated
per grill-with-docs on top — glossary entries when a term is sharpened, an
ADR only when its three tests pass (hard to reverse, surprising without
context, real trade-off). A bead's design field disappears from view when
the bead closes; a decision that should outlive the issue belongs in the
docs, and the bead's design field should then just reference it.

Push back where the issue is vague, over-broad, or contradicts the code —
capitulating to save time now costs a failed autonomous run later.

Cover, per issue (skip what the bead already answers):

- **Problem & why now** — what breaks/hurts today; how we know it's fixed.
- **Scope in / scope out** — name what is explicitly NOT in this issue.
  Scope-out lines prevent an autonomous session from wandering.
- **Acceptance criteria** — observable behaviors, each one checkable by a
  command or a concrete manual step. "Works offline" is not checkable;
  "airplane mode → profile screen renders cached data read-only" is.
- **Verification plan** — the exact local commands the executor will run and
  watch fail→pass. If no local check exists, design one here (a test to
  write first, a stand-in for a cloud dependency). An issue with no local
  feedback loop is **not groomable** — the executor would ship on vibes.
- **Design constraints** — approach, files involved, patterns to follow,
  things that must not change. Capture real trade-off decisions in a line or
  two ("chose X over Y because Z") so the executor doesn't relitigate them.
- **Edge cases** — probe with concrete scenarios ("two members split ₹61
  three ways — who eats the paisa?") until boundaries are precise.
- **Size** — if honest scoping reveals multiple independent shippable slices,
  split: `bd create` children under the epic (`abc-42.1` style), each groomed
  to this same standard, and wire ordering with `bd dep add`.

## Phase 2 — write back as decisions crystallize (not batched)

After each resolved thread, update the bead immediately:

- `bd update <id> --description "…"` — problem, scope in/out. The bead must
  read as self-contained: assume the reader has zero context.
- `bd update <id> --design "…"` — approach, key files (`path:line` refs),
  constraints, decided trade-offs.
- `bd update <id> --acceptance "…"` — the numbered, checkable criteria.
- `bd dep add <issue> <blocker>` — ordering between siblings.

Long text: write to a temp file and use `--body-file` / `--design-file` where
supported; never fight shell quoting inline.

## Phase 3 — emit the goal condition and mark groomed

For each groomed issue (or a small sequenced batch), write a `/goal` condition
following `references/goal-conditions.md` — read that file now if you haven't.
Shape:

```
Ship bead <id> via the ship-beads skill (bd show <id> has full scope/design/acceptance).
DONE = <measurable end state, e.g. PR opened + checks green + bd shows closed>.
PROVE IT = <exact commands whose FRESH output must be printed in the transcript>.
CONSTRAINTS = <anti-gaming lines: don't weaken/delete tests, no skips,
  acceptance criteria in bd show <id> all demonstrably met, re-run checks as
  the final action>.
```

Keep it under 4000 chars — the how/why lives on the bead (`bd show <id>` is
the executor's briefing file; that beats a temp file because it survives
across sessions and machines). Then:

1. `bd update <id> --notes "<the goal condition>"` — stored with the issue.
2. `bd label add <id> groomed` — status stays `open` so `bd ready` still
   surfaces it; the label is the "ready to pick" marker (beads has no native
   groomed status — built-ins are open/in_progress/blocked/deferred/closed/
   pinned/hooked).
3. Print the condition in the chat for copy-paste into `/goal` next session.

## Session close

Summarize: which beads are now `groomed`, their dependency order, and the
exact `/goal` line(s) to fire. Then follow the repo's own session-close rules
(export/commit/push of `.beads/issues.jsonl` per that repo's CLAUDE.md).
