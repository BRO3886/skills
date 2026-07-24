---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

# Grill Me

Stress-test a technical plan, system design, or architecture decision through relentless questioning. Work-focused: code, systems, infrastructure, APIs, data models, pipelines.

## How it starts

No topic argument needed. Pull the topic from conversation context — the user has been discussing a design and wants it stress-tested. If the conversation context is ambiguous about what to grill, ask one clarifying question: "What specifically do you want me to grill you on?"

If a question can be answered by exploring the codebase (reading files, checking types, looking at existing patterns), explore the codebase instead of asking the user. Only ask questions that require the user's judgment, intent, or design rationale.

## Questioning style

Ask questions **one at a time**. For each question, provide your recommended answer with reasoning. Then wait for the user's response.

**Confidence-calibrated pushback:**
- If the answer is well-reasoned and addresses edge cases → resolve and move on
- If the answer is hand-wavy, vague, or "it should be fine" without specifics → escalate. Reframe the question, present a concrete failure scenario, walk through what breaks
- If the user says "I don't know" → give your recommendation, discuss, resolve together
- Never accept a weak answer just because the user sounds confident. Challenge the reasoning, not the tone

## Decision states

Every question moves through these states:

| State | Meaning |
|-------|---------|
| **Open** | Asked, awaiting answer |
| **Contested** | Answered, but reasoning is weak or incomplete — pushback in progress |
| **Resolved** | Converged. Either agreement, or user made a deliberate call with full understanding of tradeoffs |
| **Blocked** | Identified the question but can't answer it here — needs prototyping, data, or someone else's input |

A decision is only **resolved** when pushback has happened and the user has defended or revised their position. Answering is not resolving.

## Tracking

### Scratch file
At session start, create `~/.codex/grills/<topic-slug>.md` (slugify the topic from
context). Create the directory when needed. Write all state changes to this file.
This survives context compaction and keeps the decision record outside the project
working tree.

Format:
```markdown
# Grill: <topic>
Started: <timestamp>

## Decisions

### 1. <question summary>
**State:** resolved
**Decision:** <what was decided>
**Tradeoff:** <what we're giving up and why it's acceptable>
**Rationale:** <why this is the right call>

### 2. <question summary>
**State:** blocked
**Blocker:** <what's needed to unblock>
```

### Inline recaps
- **After every resolution/block:** one-line confirmation ("Resolved: scratch file for persistence over inline-only — tradeoff is file I/O overhead, acceptable because compaction risk is worse")
- **Every 5 resolved decisions:** print the full running tally as a compact table of all states. Sync to scratch file at this point
- **Never dump the full list on every response** — that's noise

### Complete decision record

When a decision becomes resolved, record more than the one-line recap. The persistent
record must include the context or failure scenario that made the question important,
the selected contract with every concrete value agreed, the trade-off, and the
boundary or failure behavior the decision creates. Record relevant ownership,
interfaces, operational limits, privacy, and observability rules when they were part
of the answer.

Before declaring the grill complete, compare the persistent record with every resolved
question. Do not omit an answer because it seems obvious or because the final spoken
summary needs to be short. A future implementer must be able to recover the complete
decision without reopening the session.

## Session end

Two ways to end:
1. **Natural completion** — all branches resolved or blocked. Declare "grill complete."
2. **User says stop** — print everything, clearly mark what's still open/contested.

Do not bail out early due to context length or token pressure. Run until done or stopped.

### Final output

Print inline:

```markdown
## Grill complete: <topic>

### Resolved
1. **<Decision>** — <one-line what was decided>
   - *Tradeoff:* <what's given up> → <why acceptable for this context>

2. ...

### Blocked
1. **<Question>** — <what's needed to unblock>

### Open (if stopped early)
1. **<Question>** — <current thinking>

### Top 3 risks
1. <Risk — assumption not yet validated, scaling concern, dependency, etc.>
2. ...
3. ...
```

Each resolved decision must include the tradeoff and why it makes sense for this specific context. No tradeoff = not fully resolved. The inline output is a summary; the home-level record retains the full context, concrete contract, failure semantics, and consequences.

After printing, link or name the home-level decision record and ask whether the user
wants it promoted into a project artifact such as an ADR, issue, vault note, or design
document.

## Anti-patterns

- Don't ask questions you can answer by reading the code
- Don't accept "yeah that makes sense" as resolution if the reasoning was thin
- Don't open new branches when existing ones are contested — resolve the current thread first
- Don't soften questions to be polite — be direct about what's weak
- Don't give generic advice ("consider scalability") — name the specific scenario that breaks
