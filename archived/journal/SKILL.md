---
name: journal
description: Write a journal entry for today's work session on the current project
disable-model-invocation: true
---

# Journal

Write a journal entry for today's work session on the current project.

## Pre-flight

### Symlink check
```!
readlink journals 2>/dev/null || echo "NOT_SYMLINKED"
```

### Git repo check
```!
git -C journals rev-parse --is-inside-work-tree 2>/dev/null || echo "NOT_GIT_REPO"
```

If the symlink check says `NOT_SYMLINKED` → **STOP. Do not write anything.** Tell the user: "journals/ is not a symlinked directory. Set it up first: `ln -s ~/projects/work-journals/<project-name> journals`"

If the git repo check says `NOT_GIT_REPO` → **STOP.** Tell the user the target is not a git repo and journalling will not be backed up.

**Never commit or push anything inside `journals/` to the project repo.** Journals are backed up only via the separate git repo the symlink points to.

## Before Writing

Ask the user: "Anything specific you want captured or emphasized in this entry?" — wait for a response before proceeding. If they say no or nothing specific, write from conversation context.

## Instructions

1. Determine today's date (YYYY-MM-DD format)
2. **MANDATORY file check** — run this exact command before writing anything:
   ```bash
   ls journals/*-$(date +%Y-%m-%d)-journal.md 2>/dev/null || echo "NO_FILE_FOR_TODAY"
   ```
   You MUST run this command and read its output. Do NOT skip this step. Do NOT assume no file exists.
3. **If a file was found**: Read it, then append a new session section AFTER the last `---` separator at the bottom. Use `## Session N` heading (increment from the last session number in the file). Add `---` at the end of your entry. **NEVER create a new file when one already exists for today.**
4. **If `NO_FILE_FOR_TODAY`**: Create a new file with the next sequence number: `<NNN>-<YYYY-MM-DD>-journal.md`. Add `---` at the end.

## Entry Format

```markdown
# Journal Entry <NNN> - <date> - <short title>

(or ## Session 2/3/etc if appending to existing file)

## Goal

<What was the objective this session?>

## What Changed

<Concrete list of what was built/fixed/refactored>

## Key Insights

<Technical learnings, gotchas discovered, things that failed and why, things that succeeded>

## Decisions Made

<Any architectural or design decisions and their rationale>

---
```

## Rules

- Be specific and technical - this is for future Claude sessions, not humans
- Include code snippets for non-obvious patterns
- Document what FAILED and why, not just successes
- Keep it concise but complete - no fluff
- Always end with `---` separator for future appending

## Post-Journal Housekeeping

After writing the journal entry, also update:

- **`CLAUDE.md`** — Update any new architecture patterns, known issues, or context that future sessions need.
- **Commit and push the journal repo** — After writing the journal file, commit and push it in the work-journals repo:

  ```bash
  cd $(readlink journals) && git add -A && git commit -m "journal: <NNN> - <YYYY-MM-DD> - <short title>" && git push
  ```

  Use the symlink target path (from `readlink journals`) as the working directory. Never run these git commands from inside the project repo.

- **Auto memory `MEMORY.md`** — Located at `~/.claude/projects/<project-path>/memory/MEMORY.md`. Apply these rules strictly:
  - **Only write durable signal** — stable patterns, confirmed gotchas, architectural decisions. Never write session-specific state (e.g. "today we worked on X").
  - **Update, don't append** — if a pattern already exists, update it in place. Never duplicate entries.
  - **Prune stale entries** — if this session invalidated or superseded a previous pattern (e.g. a bug was fixed, an approach was changed), remove or correct the old entry. Stale memory is worse than no memory.
  - **Be terse** — each entry should be one or two lines max. MEMORY.md must stay under 100 lines total.
  - **What belongs here**: recurring gotchas, non-obvious API behaviours, confirmed architectural constraints, decisions with rationale, file paths that are always relevant.
  - **What does NOT belong here**: things already in CLAUDE.md or README, one-off fixes, anything that may change next session.