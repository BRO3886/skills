# skills

A small collection of [Agent Skills](https://agentskills.io) I use and share. Each skill is a self-contained folder with a `SKILL.md` (the procedure the agent loads on demand) plus any bundled scripts. They follow the cross-tool Agent Skills standard, so they work with Claude Code and any agent that reads `SKILL.md` and can run shell commands.

## Skills

### Tax filing

#### `file-indian-itr`
Prepare and file an Indian income-tax return from one local intake directory. It inventories Form 16, AIS/TIS/26AS, bank, broker, deduction, loss, and disclosure evidence; asks an exhaustive applicability interview for missing categories; reconciles the calculation against current official rules; and drives the official e-Filing portal with harness-neutral accessibility/screenshot computer use. It keeps credentials, OTPs, declarations, and irreversible submission under taxpayer control and requires all validation layers plus a readable acknowledgement before reporting the return filed.

- Requires: Python 3 for the optional local intake-inventory script, browser or desktop computer-use tooling, and taxpayer access to the official Income Tax e-Filing portal.

### Video & research

#### `youtube-transcript-research`
Research a topic by reading the transcripts of many YouTube videos instead of watching them. A coordinator searches and curates a video set on metadata, then fans out one subagent per angle to pull transcripts, read them, and return cited findings. This variant uses **gog** (YouTube Data API, OAuth) for the search ranking; metrics and captions come from `yt-dlp` (no extra API quota).

- Requires: [`gog`](https://github.com/openclaw/gogcli) on PATH + OAuth'd, `GOG_ACCOUNT` set, and `uv` (for `uvx yt-dlp`).
- If you don't have gog, use `youtube-transcript-research-dlp` below.

#### `youtube-transcript-research-dlp`
Same pipeline, but the search runs on `yt-dlp` too — **no API key, no account, no quota**. The zero-setup variant: with `uv` installed it works immediately. This is the one to grab if you just want it to run.

- Requires: `uv` only (the scripts call `uvx yt-dlp@latest`).

#### `youtube-vault-note`
Turn a single YouTube video into a markdown note in your notes vault — a note designed to **replace watching the video**. Pulls the original-language transcript (with per-minute timestamp markers for jumping back in), distils key points and any frameworks at actionable depth, searches your vault for notes the video connects to, writes a personalized first-person "why this matters to me" section with inline wikilinks, and ends with an honest watch/skip verdict. Vault-agnostic: resolves the vault from `$OBSIDIAN_VAULT`/`$VAULT_PATH`, the cwd, or by asking once.

- Requires: `uv` only (the scripts call `uvx yt-dlp@latest`).
- Distinct from the research skills above: those sweep many videos on a topic; this deep-captures one video into your vault.

### Code conventions

#### `siddhartha-go`
My Go backend coding conventions and architecture patterns — project structure, service/repository layering, Uber Fx DI, Ent ORM, error handling, testing with in-memory repos, and the preferred stack. Useful as a style guide for Go backend work or for keeping collaborators consistent.

#### `siddhartha-flutter`
My Flutter app conventions and architecture — feature-first MVVM (View → ViewModel → Repository → data-sources), the preferred stack (Riverpod 3, freezed, dio + retrofit, go_router, drift), the three-model (DTO/domain/view-state) wall, a sealed `Failure` error pipeline, opt-in offline-first sync, and a copy-per-feature vertical slice. Useful as a style guide for Flutter work or for keeping collaborators consistent.

### Code review

#### `review-coordinator`
Coordinate a multi-lens code review of a PR, branch, or uncommitted changes. It gathers the diff once, routes it to whatever specialist review skills you have installed (quality, conventions, architecture, language idioms), always runs an adversarial correctness pass plus the test suite, and synthesizes one merge-safe or do-not-merge verdict backed by evidence. It degrades gracefully: with no optional lenses installed you still get correctness plus tests. Ships a `route.py` router, a verdict JSON schema, and evals.

- Requires: Python 3 (for the bundled `route.py` router).

#### `security-lens`
Run a repository-grounded security review of a diff or codebase. Discover the project's assets, trust boundaries, authentication and authorization rules, sensitive data, persistence, external integrations, deployment controls, and documented exceptions before reviewing. Use as a security lens during code review, for security-sensitive changes, or for a repository security sweep. Report verified findings and explicitly identify checks that could not be completed.

### Workflow

#### `groom-beads`
Interactive grooming session that turns raw beads (`bd`) issues or epics into self-contained, ship-ready work contracts, then emits a ready-to-paste `/goal` condition for a later, context-free session to execute. Run it interactively on a strong model. The counterpart to `ship-beads`.

- Requires: the beads issue tracker (`bd`) available in the repo.

#### `ship-beads`
Autonomous end-to-end pipeline for shipping a groomed beads issue: claim, branch, plan, test-first implementation via delegated builders, adversarial review, a verified PR, a confession pass, and closing the bead. Repo-agnostic: the verify commands and product rules come from the target repo's own `CLAUDE.md`. The counterpart to `groom-beads`.

- Requires: the beads issue tracker (`bd`) available in the repo.

### CLI tooling

#### `rem-cli`
Bundled skill for the [`rem`](https://github.com/BRO3886/rem) CLI: create, query, update, complete, tag, and search macOS Reminders, with full command and natural-language date references.

- Requires: macOS and `rem`.

#### `ical-cli`
Bundled skill for the [`ical`](https://github.com/BRO3886/ical) CLI: manage macOS calendars and events, including recurrence, alerts, invitations, RSVP, availability, conference links, and import/export.

- Requires: macOS and `ical`.

#### `healthsync`
Bundled skill for [`healthsync`](https://github.com/BRO3886/healthsync): query a parsed Apple Health export through the CLI or its local SQLite database, with detailed schema guidance and read-only safety rules.

- Requires: `healthsync` and a populated local database.

#### `gtasks-cli`
Bundled skill for the [`gtasks`](https://github.com/BRO3886/gtasks) CLI: authenticate with Google Tasks and manage task lists and tasks, with quick and advanced command references.

- Requires: `gtasks` configured with Google OAuth credentials.

## Archived

Skills I no longer use but keep in the repo. They are not installed and not maintained.

- `grill-me` — stress-test a plan or design through a one-question-at-a-time interview that follows each branch until its decisions are resolved.
- `grill-with-docs` — stress-test a plan and update `CONTEXT.md` and ADRs as decisions crystallise.
- `journal` — write a journal entry for today's work session on the current project.
- `prep-for-task` — bootstrap context for a new session on the current project.

## Structure

Skills are grouped by category into folders. `archived/` holds retired skills kept for reference.

```
archived/          journal, prep-for-task, grill-me, grill-with-docs
tax-filing/        file-indian-itr
video-research/    youtube-transcript-research, -dlp, youtube-vault-note
code-conventions/  siddhartha-go, siddhartha-flutter
code-review/       review-coordinator, security-lens
workflow/          groom-beads, ship-beads
cli-tooling/       rem-cli, ical-cli, healthsync, gtasks-cli
```

## Installing a skill

Copy the skill folder into your agent's skills directory. For Claude Code:

```bash
cp -R video-research/youtube-transcript-research-dlp ~/.claude/skills/
```

Then invoke it by name (or let the agent trigger it from its description). For other agents, point them at the folder per their skill-loading convention.

## A note on the two YouTube skills

They do the same job with different search backends. If you install **both** in the same agent, their descriptions overlap and the agent may load either one on a generic "research X on YouTube" request. Install the one that matches your setup — `-dlp` for zero-config, the gog one if you already run gog and prefer the Data API ranking.

## YouTube blocking

`yt-dlp` is bot-walled from datacenter IPs (cloud VMs, CI, containers on cloud hosts) — you'll hit "Sign in to confirm you're not a bot". On a local/residential machine it's usually fine. From the cloud, set `YT_DLP_COOKIES_FROM_BROWSER=chrome` (the scripts pass `--cookies-from-browser` through; cookies are personal, never commit them). The scripts use `uvx yt-dlp@latest` and set retries/sleep to stay current and back off.

## License

MIT
