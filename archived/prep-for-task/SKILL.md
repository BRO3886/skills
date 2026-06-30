---
name: prep-for-task
description: Bootstrap context for a new session on the current project. Run this BEFORE starting any implementation work.
disable-model-invocation: true
---

# Prep for Task

Bootstrap context for a new session on the current project. Run this BEFORE starting any implementation work.

## Project instructions

```!
cat CLAUDE.md 2>/dev/null || echo "No CLAUDE.md found"
```

## Auto memory

```!
PROJECT_DIR=$(pwd | sed 's|/|-|g; s|^-||'); cat ~/.claude/projects/"$PROJECT_DIR"/memory/MEMORY.md 2>/dev/null || echo "No MEMORY.md found"
```

## Instructions

The project instructions and auto memory above have been pre-loaded. Now launch these exploration subagents **in parallel** to gain comprehensive project context:

### Agent 1: Project Overview

Read these files and summarize the project state:

- `README.md` — services, configuration, credentials
- Run `git log --oneline -20` for recent commit history
- Run `git status` for working tree state
- Check `~/.claude/plans/*.md` — read any plan files modified in the last 7 days

### Agent 2: Codebase Structure

Explore the full directory tree and map out the project structure. Adapt based on what you find:

- Top-level directories and their purpose
- Key entry points (main files, index files, server/app bootstrapping)
- Where the core business logic lives
- Any notable config files, build tooling, or infra files (Dockerfile, CI configs, etc.)

### Agent 3: Journal History

Read ALL files in `journals/` sorted by name (ascending), if the directory exists. For each session entry, extract signal and condense it. Return a structured summary to the main instance — do NOT return raw journal content:

```
## Journal Summary
### Recently Built / Fixed
<bullet per notable feature or fix, most recent first>

### Technical Gotchas
<bullet per confirmed gotcha or non-obvious behaviour>

### Architectural Decisions
<bullet per decision with rationale>

### Deferred / Known Issues
<bullet per thing explicitly deferred or known to be broken>
```

Omit anything already superseded by a later journal entry. Be terse — this summary must fit in ~30 lines. If no `journals/` directory exists, skip this agent.

## After Exploration

Summarize your findings to the user in this format:

```
## Project State
- Recent features: <list>
- Known issues: <list>

## Recent Changes
<last 5 commits, one line each>

## Key Gotchas to Remember
<top 5 technical pitfalls from journals and memory>

## Suggested Next Task
Based on open issues, in-progress branches, plan files, and deferred items from journals — suggest the single most logical next task and ask if that's the priority or if something else takes precedence.
```

## Rules

- Use subagents for ALL exploration — maximize parallelism
- Do NOT write or modify any files during prep
- Do NOT start implementation until the user gives you a task