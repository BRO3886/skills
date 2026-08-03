---
name: youtube-vault-note
description: Turn a YouTube video into a markdown note in the user's notes vault — a note good enough to replace watching the video. Use when given a YouTube link to save, summarise, take notes on, or "make a note from", even if the user doesn't say "note" — any YouTube link with intent to capture it. Pulls the transcript in the video's original language, distils it with timestamps, searches the vault for notes the video connects to, writes a personalized "why this matters" section, and gives an honest watch/skip verdict.
argument-hint: <youtube-url> [key points you want to highlight]
context: fork
allowed-tools: Bash(bash *), Bash(uvx *), Write, Read, Glob, Grep
---

# youtube-vault-note

Create a markdown note in the user's vault for the YouTube video at `$ARGUMENTS[0]`.

**The note's job is to replace watching the video.** Reading is faster than watching; the note must carry enough that the user only returns to the video if something really lands — and when they do, the timestamps tell them where to jump. Three layers: (1) faithful distillation, (2) a personal connection pass grounded in the user's existing notes, (3) an honest watch verdict.

Requires `uv` (the scripts call `uvx yt-dlp@latest`). No API key.

## Video data

The info + transcript are pre-loaded below via `scripts/fetch.sh` (pure `yt-dlp`). The transcript arrives in the video's **original language** — do not expect English.

```!
bash ${CLAUDE_SKILL_DIR}/scripts/fetch.sh "$ARGUMENTS[0]"
```

The block above is structured:
- `===INFO===` then 7 lines: title, uploader, upload_date (YYYYMMDD), duration (seconds), view_count, language, chapters (JSON array or `null`).
- `===TRANSCRIPT=== lang=<code>` then the cleaned transcript, ending at `===END===`. The transcript carries `[mm:ss]` (or `[h:mm:ss]`) markers roughly every minute — use them to cite timestamps; never invent a timestamp that isn't near a marker.
- If the transcript body is the single token `NO_CAPTIONS`, the video has no usable captions.
- **If the block above is a literal command instead of output** (your agent doesn't support pre-load substitution), run it yourself: `bash <skill-dir>/scripts/fetch.sh "<video-url>"`.
- If the output is empty or an error (not `NO_CAPTIONS`), YouTube rate-limited / bot-walled the fetch. Re-run it; if still blocked, prefix with `YT_DLP_COOKIES_FROM_BROWSER=chrome` (cookies get past the bot wall; only needed on blocked/datacenter IPs).

## Key points from the user

$ARGUMENTS[1]

## Step 0 — Locate the vault

Resolve the vault root, first match wins:
1. `$OBSIDIAN_VAULT` or `$VAULT_PATH` env var, if set.
2. The current working directory, if it contains `.obsidian/` or is clearly a notes vault (mostly `.md` files organized in topic folders).
3. Otherwise ask the user where their vault is — once, then proceed.

Pick the destination folder by convention: if the vault has a resources / references / clippings / media folder, use it; otherwise the vault root. Match the vault's observed filename style (spaces vs hyphens, capitalization) — look at a few existing filenames before choosing.

## Step 1 — Distil

Synthesise the transcript into the note body (template below): abstract, key points, optional deep-dive section(s), moments worth keeping with timestamps.

## Step 2 — Vault connection pass

Before writing the note, ground it in who the user is and what they're working on:

1. **Find user context.** Look for an about-the-user note: common spots are a profile/about/me note, an agent-memory folder (`for-agent/`, `.claude/`, `CLAUDE.md` in the vault root), or a goals/priorities note. If none exists, infer from the most recently modified notes what they're currently working on. If you genuinely can't tell who the user is, skip the personalization section rather than guessing.
2. **Extract 5–10 concepts/entities** from the video (topics, tools, techniques, named problems).
3. **Sweep the vault for those concepts** — bounded, grep-first, never read-everything:
   - `grep -ril "<concept>"` over the vault's active folders (skip `.obsidian`, attachments/assets folders, and any archive folder).
   - Glob filename patterns for the same concepts.
4. **Read the top candidates (cap ~6, partial reads fine)** to confirm each connection is real. A grep hit is not a connection; only claim a link after reading enough of the note to know it genuinely relates.

## Step 3 — Write the note

Write to `<vault>/<destination-folder>/<title>.md`.

Frontmatter (exact structure):
```
---
date: <today YYYY-MM-DD>
type: media-note
media: youtube
source: <the video URL>
author: <uploader from INFO>
status: notes-taken
tags:
  - media
  - youtube/<uploader>
  - <2-4 content tags derived from the transcript>
---
```

Body:
```
# <title from INFO>

> [!abstract] What this is
> <one sentence on what the video is and its core argument>
>
> **Watch verdict:** <one line: "skip, the note covers it" / "jump to [mm:ss] for X, skip the rest" / "worth the full watch because Y". Be honest — most talks are skippable once distilled.>

## Key points

<5-8 standalone bullets distilled from the transcript — rephrased for recall, in ENGLISH, not raw quotes. If the user gave highlights, lead with those; otherwise derive the takeaways yourself.>

<OPTIONAL deep-dive section(s) — see the "Key points are the summary layer, not the ceiling" rule. Only when the video's payload is a framework/toolkit/method; omit for ordinary videos.>

## Why this matters to me

<First-person flowing prose (2-4 short paragraphs), written in the vault owner's voice as a personalized read. Connect the video's ideas to their actual projects, habits, and open problems — with [[wikilinks]] woven INLINE into the sentences, never as a list of related notes. End with the one or two things worth actually trying, tied to something real and current from their vault. Omit this section entirely if Step 2 found no user context.>

## Moments worth keeping

> [mm:ss] <a few moments worth preserving, each prefixed with its nearest timestamp marker so the user can jump into the video>

## My take


> [!note]- Full transcript (lang=<code>)
> <the full cleaned transcript, verbatim, in its original language, timestamp markers included>
```

## Rules

- **Title comes from INFO, not the user.** Strip characters illegal in filenames (`/ \ : * ? " < > |`) and replace em/en dashes with a plain hyphen; otherwise follow the vault's naming style.
- **Original-language transcripts are normal.** Auto-captions come back in the video's language (e.g. Hinglish in Devanagari, Japanese, Spanish). You read it fine — **always write Key points in English** regardless of transcript language. For "Moments worth keeping," render the lines into clean English and label the section "rendered from original-language audio" when the transcript isn't English.
- **Embed the full transcript** in the collapsible callout, verbatim, in its original language — it's source preservation (the collapsible keeps the note clean). Note the `lang=` code in the heading.
- **NO_CAPTIONS → honest stub, never fabricate.** If the transcript is `NO_CAPTIONS`, write the note with the real INFO (title/author/tags) but put a `> [!warning] No transcript available` callout in place of Key points, leave the remaining content sections empty, and do not invent takeaways from the title alone.
- **Key points are the summary layer, not the ceiling.** If the video's core payload is a framework, a named list of techniques, a step-by-step method, or concrete prompt/command patterns, give it its own `##` section between Key points and Why this matters to me, and capture each technique/step at actionable depth: what it's for, when to use it, and the speaker's actual phrasing or steps (lightly cleaned, not paraphrased into vagueness). The test: could the user apply the technique from the note alone, without rewatching? A talk whose message is "here are my 6 techniques" must never compress to one bullet listing six names.
- **Preserve implementable specifics.** Exact prompt wordings, numbers, tool names, before/after comparisons, and named concepts with their definitions are the reason the note exists. Losing them means the video has to be rewatched, which defeats the note. When the speaker states a mental model as a mapping (e.g. a 2x2 matrix), reproduce the mapping structure (a small table is fine), don't flatten it to prose.
- **"Why this matters to me" is grounded or absent.** Every connection must trace to a vault note you actually read in Step 2, wikilinked inline in the prose (first mention only; use display aliases where the filename differs from natural phrasing). Never fabricate the user's opinions or feelings — that's what "My take" is for; this section connects facts (what they're building, learning, struggling with) to what the video offers. If the vault sweep finds nothing that genuinely connects, write one honest line ("nothing in the vault connects to this yet; it's new territory") instead of forcing a story.
- **Watch verdict is mandatory and honest.** Default posture: the note replaces the video. Recommend a full watch only when something material doesn't survive transcription (live demos, visual walkthroughs, delivery worth experiencing).
- **Leave "My take" empty** for the user to fill in.
- Author tag is always `youtube/<uploader>`.

## Gotchas

- **The transcript is the original ASR track, not an English translation.** `fetch.sh` detects the video's language and pulls that. This is intentional — synthesise from it directly.
- **Don't dump the transcript as Key points.** Key points are distilled and in English; the raw transcript only ever goes in the collapsible.
- **Timestamp markers are coarse (~1/min).** Cite the nearest marker at or before the moment; don't fake second-level precision.
- **`yt-dlp` gets bot-walled by IP reputation**, not by anything you did wrong. Local/residential machines are usually fine; the cookies fallback above is for when it isn't.

## Available scripts

In `scripts/` (referenced above by `${CLAUDE_SKILL_DIR}`; other agents: resolve relative to this file):
- **`fetch.sh <id-or-url>`** — prints the `===INFO===` / `===TRANSCRIPT===` block (7 INFO lines incl. chapters JSON; transcript with `[mm:ss]` markers). Pulls the original-language transcript via `yt-dlp` (`uvx`), no API key. Honors `YT_DLP_COOKIES_FROM_BROWSER`.
- **`clean-vtt.sh <file.vtt>`** — strips VTT tags/headers and dedupes auto-sub repeats, injecting a `[mm:ss]` marker roughly every 60 seconds; language-agnostic. Used internally by `fetch.sh`.
