#!/usr/bin/env bash
# Clean a YouTube auto-subtitle .vtt file into plain transcript text.
# Strips VTT tags and headers, dedupes the auto-sub line repeats, and injects
# a [mm:ss] (or [h:mm:ss]) marker roughly every 60 seconds so notes can cite
# jump-in timestamps. Works regardless of caption language (Latin, Devanagari,
# CJK, etc.).
# Usage: clean-vtt.sh <file.vtt>   (prints the cleaned transcript to stdout)
set -euo pipefail

arg="${1:-}"
if [[ "$arg" == "-h" || "$arg" == "--help" || -z "$arg" ]]; then
  echo "Usage: clean-vtt.sh <file.vtt>"
  echo "Strips VTT tags and headers, dedupes auto-sub repeats,"
  echo "injects a [mm:ss] marker roughly every 60 seconds."
  echo "Prints the cleaned transcript to stdout."
  [[ -z "$arg" ]] && exit 1 || exit 0
fi

if [[ ! -f "$arg" ]]; then
  echo "error: file not found: $arg" >&2
  exit 1
fi

sed -e 's/<[^>]*>//g' "$arg" \
  | awk '
    /^WEBVTT/ || /^Kind:/ || /^Language:/ || /^[[:space:]]*$/ { next }
    /-->/ {
      split($1, t, /[:.]/)
      secs = t[1] * 3600 + t[2] * 60 + t[3]
      if (secs >= mark) {
        if (secs >= 3600) printf("[%d:%02d:%02d]\n", secs / 3600, (secs % 3600) / 60, secs % 60)
        else printf("[%02d:%02d]\n", secs / 60, secs % 60)
        mark = secs + 60
      }
      next
    }
    !seen[$0]++
  '
