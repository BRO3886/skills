#!/usr/bin/env bash
# Print metadata (NO transcript) for one or more YouTube videos as TSV.
# Optional richer pass for the coordinator: search (yt-search.sh) already returns
# duration + view_count, so this is only needed when you also want like_count or
# an authoritative duration for a specific shortlist. Downloads no captions.
# Columns: video_id <TAB> duration_seconds <TAB> view_count <TAB> like_count <TAB> title
# Usage: video-metrics.sh <url-or-id> [url-or-id ...]
#
# Optional env:
#   YT_DLP_COOKIES_FROM_BROWSER=chrome   # pass browser cookies to dodge bot walls
#                                        # (needed from datacenter/CI IPs)
set -euo pipefail

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: video-metrics.sh <url-or-id> [url-or-id ...]"
  echo "Prints TSV: video_id<TAB>duration_seconds<TAB>view_count<TAB>like_count<TAB>title"
  echo "Drop shorts by filtering duration_seconds (e.g. < 180). Missing fields print as NA."
  [[ $# -eq 0 ]] && exit 1 || exit 0
fi

cookies=()
[[ -n "${YT_DLP_COOKIES_FROM_BROWSER:-}" ]] && cookies=(--cookies-from-browser "$YT_DLP_COOKIES_FROM_BROWSER")

fmt=$'%(id)s\t%(duration)s\t%(view_count)s\t%(like_count)s\t%(title)s'
# --ignore-errors so one dead/private video doesn't abort the whole batch.
uvx yt-dlp@latest --skip-download --no-warnings --ignore-errors \
  --retries 3 --extractor-retries 3 --sleep-requests 1 \
  ${cookies[@]+"${cookies[@]}"} \
  --print "$fmt" "$@"
