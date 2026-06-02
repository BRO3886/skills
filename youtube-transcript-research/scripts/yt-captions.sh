#!/usr/bin/env bash
# Pull a YouTube video's English auto-subtitles and print the CLEANED transcript.
# Combines the yt-dlp caption download + clean-vtt.sh into one step.
# Usage: yt-captions.sh <video-id-or-url>
#   exit 0 = transcript printed to stdout
#   exit 2 = no usable English captions (caller should skip / backfill)
#
# Optional env:
#   YT_DLP_COOKIES_FROM_BROWSER=chrome   # pass browser cookies to dodge bot walls
#                                        # (needed from datacenter/CI IPs)
set -euo pipefail

arg="${1:-}"
if [[ -z "$arg" || "$arg" == "-h" || "$arg" == "--help" ]]; then
  echo "Usage: yt-captions.sh <video-id-or-url>"
  echo "Prints the cleaned transcript to stdout. Exit 2 if no English captions."
  [[ -z "$arg" ]] && exit 1 || exit 0
fi

# Bare ID -> full URL; pass URLs through untouched.
if [[ "$arg" == http* ]]; then url="$arg"; else url="https://youtu.be/$arg"; fi

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cookies=()
[[ -n "${YT_DLP_COOKIES_FROM_BROWSER:-}" ]] && cookies=(--cookies-from-browser "$YT_DLP_COOKIES_FROM_BROWSER")

uvx yt-dlp@latest --skip-download --write-auto-subs --sub-langs "en.*,en" \
  --sub-format vtt --no-warnings --ignore-errors \
  --retries 3 --extractor-retries 3 --sleep-requests 1 \
  ${cookies[@]+"${cookies[@]}"} \
  -o "$tmp/vid.%(ext)s" "$url" >&2 || true

# Prefer en, then any en.* variant the channel published.
vtt="$(ls "$tmp"/*.vtt 2>/dev/null | head -1 || true)"
if [[ -z "$vtt" || ! -f "$vtt" ]]; then
  echo "NO_CAPTIONS: $arg" >&2
  exit 2
fi

bash "$dir/clean-vtt.sh" "$vtt"
