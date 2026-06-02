---
name: youtube-transcript-research
description: Research a topic by reading many YouTube transcripts instead of watching the videos, using gog (YouTube Data API) for search. Use when the user wants to research, learn about, or gather insights on a topic whose knowledge lives in talks, teardowns, interviews, or tutorials — product design, behavioural science, competitive/market analysis, marketing tactics, how-tos — even when they don't say "YouTube" or "transcript", and has gog installed and prefers the YouTube Data API's relevance ranking for search. A coordinator finds and curates videos, then fans out subagents to read transcripts in parallel and return cited findings.
allowed-tools: Bash(gog *), Bash(uvx *), Bash(bash *), Bash(cd /tmp*)
---

# YouTube transcript research (gog search backend)

Research a topic by reading the transcripts of many YouTube videos, instead of watching them. A **coordinator** searches and curates the video set on metadata, then **fans out one subagent per angle** to pull transcripts, read them, and return tight cited syntheses. The coordinator never reads raw transcripts; subagents never see each other's.

This skill uses **gog** (YouTube Data API, OAuth) for the search step, for people who have gog set up and prefer the Data API's relevance ranking. Everything else — metrics (views/likes) and captions — runs on `yt-dlp` via `uvx`, which costs **no** API quota. So only the search call consumes your Data API quota.

## When to use / when not

- **Multi-angle sweep (this skill):** a real research question with several facets, where watching 80 min × 8+ videos isn't worth it. Use the coordinator + fan-out flow below.
- **Quick one-off:** if it's one narrow question and a handful of videos, skip the orchestration — one agent does search → pull → read inline. Don't spin up the fan-out for a 2-video lookup.

## Prerequisites

- **`gog`** on PATH, OAuth'd for a Google account, and **`GOG_ACCOUNT=<email>`** set to that account. `gog yt search` needs an account (`--account`); the bundled script reads it from `GOG_ACCOUNT`.
- **`uvx`** (ships with [`uv`](https://docs.astral.sh/uv/)) — runs `yt-dlp` on demand for metrics + captions, nothing to install. The bundled scripts call `uvx yt-dlp@latest` so you're never on a stale build YouTube has already broken.
- **Bundled scripts** in this skill's `scripts/` directory: `gog-search.sh`, `yt-captions.sh`, `video-metrics.sh`, `clean-vtt.sh`.
- **A `<SKILL_DIR>` you can resolve to an absolute path.** Throughout this doc, replace `<SKILL_DIR>` with the absolute path to *this* skill folder. Subagents typically run from `/tmp` and cannot resolve relative `scripts/` paths, so always hand them the absolute path.

## Flow

### Phase 1 — Coordinator: discover + curate (metadata only)

1. **Define N disjoint angles.** Decompose the topic into non-overlapping facets. Each angle gets **3-5 query variations** (different phrasings surface different videos).

2. **Search each variation** (gog returns Data API relevance order; the script enriches with yt-dlp for duration + views):
   ```bash
   GOG_ACCOUNT=<email> bash <SKILL_DIR>/scripts/gog-search.sh "<query>" 15
   ```
   TSV columns: `video_id  duration_seconds  view_count  channel  title`. Build URLs as `https://youtu.be/<video_id>`. Pool results across an angle's variations. The gog search is one Data API call per query; the per-video duration/view enrichment is yt-dlp scrape (no quota), so it's a touch slower than a pure scrape search but doesn't burn extra quota.

3. **Curate on metadata** — this is the coordinator's whole job. The search output already carries duration + views:
   - **Dedupe across angles** by `video_id` (a video belongs to one angle only).
   - **Drop shorts**: discard `duration_seconds < 180`.
   - **Assign** each surviving video to exactly one angle.
   - **Attach** `view_count` to each entry as *context*.
   - **Mark clickbait titles** with a soft `clickbait?` flag — telltales: numbered listicles ("7 Foods…"), urgency/timeline ("…FAST", "in 7 days", "300 to 100 in 5 days"), ALL-CAPS words, "Doctor Reveals", "#1", emoji, "…and you can too". This is a *context flag passed to the reader*, exactly like views — NOT a drop filter (clickbait titles often wrap real content). Judge the content, not the title.
   - Do **not** rank or gate on quality, and do **not** drop low-view videos (or clickbait-titled ones) — metrics and flags travel with the transcript so the reader can weigh them. Selection is by relevance + caption availability, capped at ~8-12 per angle, never by popularity or title style.
   - *Optional:* for like counts, run `bash <SKILL_DIR>/scripts/video-metrics.sh <id> [<id> ...]` (TSV adds `like_count`). Skip unless you need likes.

### Phase 2 — Fan out: one subagent per angle (parallel)

Spawn one subagent per angle, each handed its assigned read-list (videoIds + the views context). They run concurrently — a fast/cheap model tier is fine, this is reading and summarising. When building each prompt, substitute the real absolute skill-directory path for `<SKILL_DIR>`. Prompt template:

```
You are researching ONE angle: "<angle>". Work the task directly — do NOT run
any session-init, onboarding, or setup routines; just do the research.

Read-list (video_id | views | clickbait?):
<the curated list for this angle>

For each video, pull the cleaned transcript in one step:
  bash <SKILL_DIR>/scripts/yt-captions.sh <video_id>
- It prints the cleaned transcript to stdout.
- If it exits non-zero / prints "NO_CAPTIONS", that video has no usable English
  captions — skip it and pull the next from the list (backfill).

Then READ the transcripts and synthesise. Treat views as SOFT context, not
truth: a hugely popular video isn't automatically right, and a low-view one
isn't automatically wrong — but a video with almost no engagement is worth a
grain of salt. There are no dislike counts (YouTube removed them), so read
views as a weak engagement signal only.

A `clickbait?` flag is a yellow flag, not a verdict: read the video anyway, but
check whether the CONTENT delivers on the title or contradicts it. Clickbait
often signals oversimplification or an overclaimed timeline/effect-size — call
out specifically where the content fails to back the title (e.g. a "lower X in 7
days" video whose own transcript admits it takes weeks).

Return: key insights, each with a (title + URL + views) citation, and a flag on
anything that reads as marketing fluff or whose content didn't live up to a
clickbait title.
```

### Phase 3 — Coordinator: consolidate

Merge the per-angle briefs into the final deliverable, preserving citations. The deliverable is **whatever the user asked for** — a written answer in the reply, or a file at a path the user specifies. Don't assume any particular notes system or write location; if the user wants it saved, use the path they gave.

## Gotchas

- **`gog-search.sh` needs `GOG_ACCOUNT` set** — it errors clearly if unset. gog must already be OAuth'd for that account, and `gog` must be on PATH.
- **Only the search costs Data API quota.** gog's `search.list` is the one Data API call per query. Duration, views, likes, and captions all come from yt-dlp (scrape), so they don't touch your quota — this is deliberate, to avoid doubling API usage on every video.
- **Search ranking is relevance, not view count.** gog defaults to `--order relevance`, tuned for topical fit, which is what research wants. Don't re-sort by popularity; it biases toward big channels and off-topic virality.
- **Shorts must be filtered by duration** (`< 180s`) — gog search exposes no duration, so the script enriches it via yt-dlp; filter on the `duration_seconds` column.
- **Metrics are context, never a gate.** Don't rank or pre-filter videos by views — that kills the underrated gem, which is exactly what good research finds. Pass the numbers to the reader as soft signal.
- **Clickbait is a soft signal too, not a drop filter.** Flag clickbait titles and pass the flag to the reader — but never exclude a video on its title alone. The subagent's job is to check whether the transcript backs the title and flag where it doesn't.
- **Most videos lack usable auto-subs.** Curate ~8-12 per angle but keep the rest as backfill; subagents skip caption-less ones and pull the next.
- **Coordinator stays out of transcript bodies.** It curates on metadata (small) only. Reading raw transcripts is the subagent's job — keep them out of the coordinator's context so it can hold many angles.
- **yt-dlp blocking still applies to the enrichment + captions.** YouTube bot-walls `yt-dlp` from datacenter IPs (cloud VMs, CI, containers on cloud hosts) — `"Sign in to confirm you're not a bot"` / HTTP 429. Local/residential machines are usually fine. If you hit it, set `YT_DLP_COOKIES_FROM_BROWSER=chrome` (the scripts pass `--cookies-from-browser` through; cookies are personal — never commit them). The scripts already use `uvx yt-dlp@latest` and set retries/sleep.

## Available scripts

All live in `<SKILL_DIR>/scripts/` — reference them by absolute path (a subagent's cwd is never the skill dir). The yt-dlp-backed ones accept the optional `YT_DLP_COOKIES_FROM_BROWSER` env var.

- **`gog-search.sh "<query>" [max]`** — searches via gog (Data API relevance), enriches with yt-dlp for duration/views. Needs `GOG_ACCOUNT`. TSV of `video_id, duration_seconds, view_count, channel, title`. The coordinator's discovery + curation input.
- **`yt-captions.sh <id-or-url>`** — pulls English auto-subtitles and prints the **cleaned** transcript to stdout in one step (download + clean combined). Exit 2 + `NO_CAPTIONS` if none. The subagent's per-video call. yt-dlp, no API.
- **`video-metrics.sh <url-or-id> ...`** — *optional.* TSV of `video_id, duration_seconds, view_count, like_count, title` via yt-dlp. Use only when you want like counts beyond what search already gives.
- **`clean-vtt.sh <file.vtt>`** — strips VTT tags, timestamps, headers and dedupes auto-sub repeats; prints clean transcript to stdout. Underlies `yt-captions.sh`; call it directly only if you pulled a `.vtt` yourself.

## Checklist

- [ ] `GOG_ACCOUNT` set; gog installed + OAuth'd
- [ ] Angles defined, disjoint, 3-5 query variations each
- [ ] Searched via `gog-search.sh`; candidates pooled per angle
- [ ] Deduped across angles; shorts (<180s) dropped using `duration_seconds`
- [ ] Each video assigned to one angle, views + clickbait? flag attached as context (never used to drop)
- [ ] One subagent per angle, parallel, given its read-list + absolute `<SKILL_DIR>`
- [ ] Subagents pull cleaned transcripts via `yt-captions.sh`, skip caption-less + backfill
- [ ] Briefs consolidated with citations preserved, written to wherever the user asked
