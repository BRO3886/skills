#!/usr/bin/env bash
# Fetch a YouTube video's info + ORIGINAL-LANGUAGE transcript for a media note.
# No API key, no local server — pure yt-dlp via uvx. Prints a structured block:
#
#   ===INFO===
#   <title>
#   <uploader>
#   <upload_date YYYYMMDD>
#   <duration_seconds>
#   <view_count>
#   <language>                 # detected original language code (or "en" fallback)
#   ===TRANSCRIPT=== lang=<code|none>
#   <cleaned transcript in the video's ORIGINAL language>   # or the token NO_CAPTIONS
#   ===END===
#
# Usage: fetch.sh <video-id-or-url>
# Optional env:
#   YT_DLP_COOKIES_FROM_BROWSER=chrome   # get past YouTube bot-walls (datacenter/CI IPs)
set -euo pipefail

arg="${1:-}"
if [[ -z "$arg" || "$arg" == "-h" || "$arg" == "--help" ]]; then
  echo "Usage: fetch.sh <video-id-or-url>" >&2
  [[ -z "$arg" ]] && exit 1 || exit 0
fi
if [[ "$arg" == http* ]]; then url="$arg"; else url="https://youtu.be/$arg"; fi

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# android_vr needs no JS runtime (dodges the n-challenge that breaks the default
# web client); retries/sleep absorb transient 429s. Cookies expanded at each call
# site (array-in-array quoting is unsafe on macOS bash 3.2).
COMMON=(--no-warnings --ignore-errors
        --extractor-args "youtube:player_client=android_vr"
        --retries 5 --extractor-retries 5 --sleep-requests 2)
cookies=()
[[ -n "${YT_DLP_COOKIES_FROM_BROWSER:-}" ]] && cookies=(--cookies-from-browser "$YT_DLP_COOKIES_FROM_BROWSER")

# --- INFO (one field per line; a title can contain any delimiter, so never join) ---
info="$(uvx yt-dlp@latest "${COMMON[@]}" ${cookies[@]+"${cookies[@]}"} --skip-download \
  --print "%(title)s" --print "%(uploader)s" --print "%(upload_date)s" \
  --print "%(duration)s" --print "%(view_count)s" --print "%(language)s" \
  --print "%(chapters)j" \
  "$url" 2>/dev/null || true)"

lang="$(printf '%s\n' "$info" | sed -n '6p')"
[[ -z "$lang" || "$lang" == "NA" || "$lang" == "none" ]] && lang="en"

printf '===INFO===\n%s\n' "$info"

# --- TRANSCRIPT (original language; manual subs preferred, then auto; en fallback) ---
pull() {
  uvx yt-dlp@latest "${COMMON[@]}" ${cookies[@]+"${cookies[@]}"} --skip-download \
    --write-subs --write-auto-subs --sub-langs "$1" --sub-format vtt \
    -o "$tmp/vid.%(ext)s" "$url" >&2 || true
}
pull "${lang}.*,${lang}"
vtt="$(ls "$tmp"/*.vtt 2>/dev/null | head -1 || true)"
if [[ -z "$vtt" && "$lang" != "en" ]]; then
  pull "en.*,en"
  vtt="$(ls "$tmp"/*.vtt 2>/dev/null | head -1 || true)"
fi

if [[ -z "$vtt" || ! -f "$vtt" ]]; then
  printf '===TRANSCRIPT=== lang=none\nNO_CAPTIONS\n===END===\n'
  exit 0
fi

got="$(basename "$vtt" | sed -E 's/^vid\.(.+)\.vtt$/\1/')"
printf '===TRANSCRIPT=== lang=%s\n' "$got"
bash "$dir/clean-vtt.sh" "$vtt"
printf '===END===\n'
