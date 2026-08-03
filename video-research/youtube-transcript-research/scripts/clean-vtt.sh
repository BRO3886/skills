#!/usr/bin/env bash
# Clean a YouTube auto-subtitle .vtt file into plain transcript text.
# Strips VTT tags, timestamps, headers, and dedupes the auto-sub line repeats.
# Usage: clean-vtt.sh <file.vtt>   (prints the cleaned transcript to stdout)
set -euo pipefail

arg="${1:-}"
if [[ "$arg" == "-h" || "$arg" == "--help" || -z "$arg" ]]; then
  echo "Usage: clean-vtt.sh <file.vtt>"
  echo "Strips VTT tags, timestamps, and headers, dedupes auto-sub repeats."
  echo "Prints the cleaned transcript to stdout."
  [[ -z "$arg" ]] && exit 1 || exit 0
fi

if [[ ! -f "$arg" ]]; then
  echo "error: file not found: $arg" >&2
  exit 1
fi

sed -e 's/<[^>]*>//g' "$arg" \
  | grep -v -e '-->' -e '^WEBVTT' -e '^Kind:' -e '^Language:' -e '^[[:space:]]*$' \
  | awk '!seen[$0]++'
