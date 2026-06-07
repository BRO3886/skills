# skills

A small collection of [Agent Skills](https://agentskills.io) I use and share. Each skill is a self-contained folder with a `SKILL.md` (the procedure the agent loads on demand) plus any bundled scripts. They follow the cross-tool Agent Skills standard, so they work with Claude Code and any agent that reads `SKILL.md` and can run shell commands.

## Skills

### `youtube-transcript-research`
Research a topic by reading the transcripts of many YouTube videos instead of watching them. A coordinator searches and curates a video set on metadata, then fans out one subagent per angle to pull transcripts, read them, and return cited findings. This variant uses **gog** (YouTube Data API, OAuth) for the search ranking; metrics and captions come from `yt-dlp` (no extra API quota).

- Requires: [`gog`](https://github.com/openclaw/gogcli) on PATH + OAuth'd, `GOG_ACCOUNT` set, and `uv` (for `uvx yt-dlp`).
- If you don't have gog, use `youtube-transcript-research-dlp` below.

### `youtube-transcript-research-dlp`
Same pipeline, but the search runs on `yt-dlp` too — **no API key, no account, no quota**. The zero-setup variant: with `uv` installed it works immediately. This is the one to grab if you just want it to run.

- Requires: `uv` only (the scripts call `uvx yt-dlp@latest`).

### `siddhartha-go`
My Go backend coding conventions and architecture patterns — project structure, service/repository layering, Uber Fx DI, Ent ORM, error handling, testing with in-memory repos, and the preferred stack. Useful as a style guide for Go backend work or for keeping collaborators consistent.

### `siddhartha-flutter`
My Flutter app conventions and architecture — feature-first MVVM (View → ViewModel → Repository → data-sources), the preferred stack (Riverpod 3, freezed, dio + retrofit, go_router, drift), the three-model (DTO/domain/view-state) wall, a sealed `Failure` error pipeline, opt-in offline-first sync, and a copy-per-feature vertical slice. Useful as a style guide for Flutter work or for keeping collaborators consistent.

## Installing a skill

Copy the skill folder into your agent's skills directory. For Claude Code:

```bash
cp -R youtube-transcript-research-dlp ~/.claude/skills/
```

Then invoke it by name (or let the agent trigger it from its description). For other agents, point them at the folder per their skill-loading convention.

## A note on the two YouTube skills

They do the same job with different search backends. If you install **both** in the same agent, their descriptions overlap and the agent may load either one on a generic "research X on YouTube" request. Install the one that matches your setup — `-dlp` for zero-config, the gog one if you already run gog and prefer the Data API ranking.

## YouTube blocking

`yt-dlp` is bot-walled from datacenter IPs (cloud VMs, CI, containers on cloud hosts) — you'll hit "Sign in to confirm you're not a bot". On a local/residential machine it's usually fine. From the cloud, set `YT_DLP_COOKIES_FROM_BROWSER=chrome` (the scripts pass `--cookies-from-browser` through; cookies are personal, never commit them). The scripts use `uvx yt-dlp@latest` and set retries/sleep to stay current and back off.

## License

MIT
