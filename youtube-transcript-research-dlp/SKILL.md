---
name: youtube-transcript-research-dlp
description: Research a topic by reading many YouTube transcripts instead of watching the videos. Use when the user wants to research, learn about, or gather insights on a topic whose knowledge lives in talks, teardowns, interviews, or tutorials — product design, behavioural science, competitive/market analysis, marketing tactics, how-tos — even when they don't say "YouTube" or "transcript". A coordinator finds and curates videos, then fans out subagents to read transcripts in parallel and return cited findings. Best when watching several long videos by hand isn't worth the time.
allowed-tools: Bash(uvx *), Bash(bash *), Bash(cd /tmp*)
---

# YouTube transcript research (yt-dlp)

Research a topic by reading the transcripts of many YouTube videos, instead of watching them. A **coordinator** searches and curates the video set on metadata, then **fans out one subagent per angle** to pull transcripts, read them, and return tight cited syntheses. The coordinator never reads raw transcripts; subagents never see each other's.

The whole pipeline runs on `yt-dlp` (via `uvx`) — no API key, no account, no quota. It's a self-contained skill: drop the folder into any agent that can run shell commands and read its instructions.

## When to use / when not

- **Multi-angle sweep (this skill):** a real research question with several facets, where watching 80 min × 8+ videos isn't worth it. Use the coordinator + fan-out flow below.
- **Quick one-off:** if it's one narrow question and a handful of videos, skip the orchestration — one agent does search → pull → read inline. Don't spin up the fan-out for a 2-video lookup.

## Prerequisites

- **`uvx`** (ships with [`uv`](https://docs.astral.sh/uv/)) — runs `yt-dlp` on demand, nothing to install. The bundled scripts call `uvx yt-dlp@latest` so you're never on a stale build YouTube has already broken.
- **Bundled scripts** in this skill's `scripts/` directory: `yt-search.sh`, `yt-captions.sh`, `video-metrics.sh`, `clean-vtt.sh`.
- **A `<SKILL_DIR>` you can resolve to an absolute path.** Throughout this doc, replace `<SKILL_DIR>` with the absolute path to *this* skill folder. Subagents typically run from `/tmp` and cannot resolve relative `scripts/` paths, so always hand them the absolute path.

## Flow

### Phase 1 — Coordinator: discover + curate (metadata only)

1. **Define N disjoint angles.** Decompose the topic into non-overlapping facets. Each angle gets **3-5 query variations** (different phrasings surface different videos).

2. **Search each variation** (relevance order, which is YouTube's own default ranking):
   ```bash
   bash <SKILL_DIR>/scripts/yt-search.sh "<query>" 15
   ```
   TSV columns: `video_id  duration_seconds  view_count  channel  title`. Build URLs as `https://youtu.be/<video_id>`. Pool results across an angle's variations. This is a single search request per query — no per-video calls — so it's fast and unlikely to trip rate limits.

3. **Curate on metadata** — this is the coordinator's whole job. The search output already carries duration + views, so you can curate directly from it:
   - **Dedupe across angles** by `video_id` (a video belongs to one angle only).
   - **Drop shorts**: discard `duration_seconds < 180`.
   - **Assign** each surviving video to exactly one angle.
   - **Attach** `view_count` to each entry as *context*.
   - **Mark clickbait titles** with a soft `clickbait?` flag — telltales: numbered listicles ("7 Foods…"), urgency/timeline ("…FAST", "in 7 days", "300 to 100 in 5 days"), ALL-CAPS words, "Doctor Reveals", "#1", emoji, "…and you can too". This is a *context flag passed to the reader*, exactly like views — NOT a drop filter (clickbait titles often wrap real content; e.g. a "25 Foods… FAST" video can still have decent science). Judge the content, not the title.
   - Do **not** rank or gate on quality, and do **not** drop low-view videos (or clickbait-titled ones) — metrics and flags travel with the transcript so the reader can weigh them. Selection is by relevance + caption availability, capped at ~8-12 per angle, never by popularity or title style.
   - *Optional:* if you want like counts or an authoritative duration for the shortlist, run `bash <SKILL_DIR>/scripts/video-metrics.sh <id> [<id> ...]` (TSV adds `like_count`). Skip it unless you need likes — it does a per-video fetch, which is heavier than search.

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

- **Search ranking is relevance, not view count.** `ytsearch` uses YouTube's default search-page ordering, which is tuned for topical fit — that's what research wants. Don't try to re-sort by popularity; it biases toward big channels and off-topic virality.
- **Shorts must be filtered by duration** (`< 180s`) — search exposes no duration filter, and shorts now run up to 3 minutes, so a `< 60s` cutoff isn't enough. `duration_seconds` comes straight from `yt-search.sh`.
- **Metrics are context, never a gate.** Don't rank or pre-filter videos by views — that kills the underrated gem, which is exactly what good research finds. Pass the numbers to the reader as soft signal.
- **Clickbait is a soft signal too, not a drop filter.** Flag clickbait titles (listicles, "…FAST", "in 7 days", ALL-CAPS, "Doctor Reveals", emoji) and pass the flag to the reader — but never exclude a video on its title alone. A clickbait wrapper can still hold real content; the subagent's job is to check whether the transcript backs the title and flag where it doesn't. Title style ≠ content quality.
- **Most videos lack usable auto-subs.** Curate ~8-12 per angle but keep the rest as backfill; subagents skip caption-less ones and pull the next.
- **Coordinator stays out of transcript bodies.** It curates on metadata (small) only. Reading raw transcripts is the subagent's job — keep them out of the coordinator's context so it can hold many angles.
- **Blocking / sandboxed environments — read this before running in the cloud.** YouTube throttles and bot-walls `yt-dlp` based on **IP reputation**, not on Docker per se:
  - **Local / residential machine** (a laptop, or a container NAT'd behind a home IP): usually works out of the box. This is the intended environment.
  - **Datacenter IPs — cloud VMs, CI runners, containers on cloud hosts:** frequently hit `"Sign in to confirm you're not a bot"` or HTTP 429, often on the first request. There is no zero-config fix for this.
  - **Mitigations**, most effective first:
    1. **Cookies** — set `YT_DLP_COOKIES_FROM_BROWSER=chrome` (or `firefox`, `safari`, …) before running; the scripts pass `--cookies-from-browser` through. Authenticated cookies are the single most reliable way past the bot wall. Cookies are personal — never commit them or bundle them in a shared copy of this skill.
    2. **Stay current** — the scripts already use `uvx yt-dlp@latest`; don't pin an old yt-dlp.
    3. **Switch player client** — for stubborn blocks, add `--extractor-args "youtube:player_client=android,web_safari"` to the yt-dlp calls.
    4. **Back off** — the scripts already set `--retries`/`--sleep-requests`; raise them if you're pulling many videos in a burst.
- **`yt-dlp` updates fix breakage.** When YouTube changes its player internals, an older yt-dlp silently stops extracting until it's updated — `uvx yt-dlp@latest` is what keeps the scripts working across those changes.

## Available scripts

All live in `<SKILL_DIR>/scripts/` — reference them by absolute path (a subagent's cwd is never the skill dir). All accept the optional `YT_DLP_COOKIES_FROM_BROWSER` env var.

- **`yt-search.sh "<query>" [max]`** — searches YouTube via yt-dlp (no API key/quota/account). TSV of `video_id, duration_seconds, view_count, channel, title`. One request per query. The coordinator's discovery + curation input.
- **`yt-captions.sh <id-or-url>`** — pulls English auto-subtitles and prints the **cleaned** transcript to stdout in one step (download + clean combined). Exit 2 + `NO_CAPTIONS` if none. The subagent's per-video call.
- **`video-metrics.sh <url-or-id> ...`** — *optional.* TSV of `video_id, duration_seconds, view_count, like_count, title`. A heavier per-video fetch; use only when you want like counts beyond what search already gives.
- **`clean-vtt.sh <file.vtt>`** — strips VTT tags, timestamps, headers and dedupes auto-sub repeats; prints clean transcript to stdout. Underlies `yt-captions.sh`; call it directly only if you pulled a `.vtt` yourself.

## Checklist

- [ ] Angles defined, disjoint, 3-5 query variations each
- [ ] Searched by relevance via `yt-search.sh`; candidates pooled per angle
- [ ] Deduped across angles; shorts (<180s) dropped using `duration_seconds`
- [ ] Each video assigned to one angle, views + clickbait? flag attached as context (never used to drop)
- [ ] One subagent per angle, parallel, given its read-list + absolute `<SKILL_DIR>`
- [ ] Subagents pull cleaned transcripts via `yt-captions.sh`, skip caption-less + backfill
- [ ] Briefs consolidated with citations preserved, written to wherever the user asked
