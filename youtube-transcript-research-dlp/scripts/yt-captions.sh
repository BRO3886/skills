#!/usr/bin/env bash
# Pull a YouTube video's ORIGINAL-LANGUAGE subtitles and print the CLEANED transcript.
# Combines the yt-dlp caption download + clean-vtt.sh into one step.
#
# Pulls the video's own language (Hindi, etc.), not just English — Indian-creator
# videos publish Hindi auto-subs, which an English-only fetch silently dropped as
# NO_CAPTIONS. Detects the original language, pulls it (manual subs preferred, then
# auto), and falls back to English. Downstream readers can read non-English fine.
#
# Usage: yt-captions.sh <video-id-or-url>
#   exit 0 = transcript printed to stdout
#   exit 2 = no usable captions in any language (caller should skip / backfill)
#
# Optional env:
#   YT_DLP_COOKIES_FROM_BROWSER=chrome   # pass browser cookies to dodge bot walls
#                                        # (needed from datacenter/CI IPs)
set -euo pipefail

arg="${1:-}"
if [[ -z "$arg" || "$arg" == "-h" || "$arg" == "--help" ]]; then
  echo "Usage: yt-captions.sh <video-id-or-url>"
  echo "Prints the cleaned transcript to stdout. Exit 2 if no captions in any language."
  [[ -z "$arg" ]] && exit 1 || exit 0
fi

# Bare ID -> full URL; pass URLs through untouched.
if [[ "$arg" == http* ]]; then url="$arg"; else url="https://youtu.be/$arg"; fi

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# android_vr needs no JS runtime (dodges the n-challenge that breaks the default
# web client and was a major source of false NO_CAPTIONS); retries/sleep absorb
# transient 429s. Cookies expanded at each call site (array-in-array quoting is
# unsafe on macOS bash 3.2).
COMMON=(--no-warnings --ignore-errors
        --extractor-args "youtube:player_client=android_vr"
        --retries 5 --extractor-retries 5 --sleep-requests 1)
cookies=()
[[ -n "${YT_DLP_COOKIES_FROM_BROWSER:-}" ]] && cookies=(--cookies-from-browser "$YT_DLP_COOKIES_FROM_BROWSER")

# Detect the video's original language so we pull the subs that actually exist.
lang="$(uvx yt-dlp@latest "${COMMON[@]}" ${cookies[@]+"${cookies[@]}"} \
  --skip-download --print "%(language)s" "$url" 2>/dev/null | head -1 || true)"
[[ -z "$lang" || "$lang" == "NA" || "$lang" == "none" ]] && lang="en"

pull() {
  uvx yt-dlp@latest "${COMMON[@]}" ${cookies[@]+"${cookies[@]}"} --skip-download \
    --write-subs --write-auto-subs --sub-langs "$1" --sub-format vtt \
    -o "$tmp/vid.%(ext)s" "$url" >&2 || true
}

# Original language first (e.g. hi.*,hi), then English fallback.
pull "${lang}.*,${lang}"
vtt="$(ls "$tmp"/*.vtt 2>/dev/null | head -1 || true)"
if [[ -z "$vtt" && "$lang" != "en" ]]; then
  pull "en.*,en"
  vtt="$(ls "$tmp"/*.vtt 2>/dev/null | head -1 || true)"
fi

if [[ -z "$vtt" || ! -f "$vtt" ]]; then
  echo "NO_CAPTIONS: $arg" >&2
  exit 2
fi

got="$(basename "$vtt" | sed -E 's/^vid\.(.+)\.vtt$/\1/')"
echo "captions: lang=$got" >&2
bash "$dir/clean-vtt.sh" "$vtt"
