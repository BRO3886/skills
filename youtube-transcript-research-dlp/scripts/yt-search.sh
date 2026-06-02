#!/usr/bin/env bash
# Search YouTube via yt-dlp — no API key, no quota, no account.
# Uses YouTube's own search-page relevance ranking (anonymous, logged-out).
# Prints one TSV row per result. Columns:
#   video_id <TAB> duration_seconds <TAB> view_count <TAB> channel <TAB> title
# Missing fields print as "NA". Drop shorts later by filtering duration < 180.
# Usage: yt-search.sh "<query>" [max=15]
#
# Optional env:
#   YT_DLP_COOKIES_FROM_BROWSER=chrome   # pass browser cookies to dodge bot walls
#                                        # (needed from datacenter/CI IPs)
set -euo pipefail

q="${1:-}"
max="${2:-15}"
if [[ -z "$q" || "$q" == "-h" || "$q" == "--help" ]]; then
  echo "Usage: yt-search.sh \"<query>\" [max]"
  echo "Prints TSV: video_id<TAB>duration_seconds<TAB>view_count<TAB>channel<TAB>title"
  [[ -z "$q" ]] && exit 1 || exit 0
fi

cookies=()
[[ -n "${YT_DLP_COOKIES_FROM_BROWSER:-}" ]] && cookies=(--cookies-from-browser "$YT_DLP_COOKIES_FROM_BROWSER")

fmt=$'%(id)s\t%(duration)s\t%(view_count)s\t%(channel)s\t%(title)s'
# --flat-playlist keeps it to a single search request (no per-video extraction),
# which is faster and far less likely to trip rate limiting / bot detection.
uvx yt-dlp@latest --flat-playlist --skip-download --no-warnings --ignore-errors \
  --retries 3 --extractor-retries 3 \
  ${cookies[@]+"${cookies[@]}"} \
  --print "$fmt" "ytsearch${max}:${q}"
