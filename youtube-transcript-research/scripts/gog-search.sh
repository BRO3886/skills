#!/usr/bin/env bash
# Search YouTube via gog (YouTube Data API, OAuth) for relevance ranking, then
# enrich each hit with yt-dlp for duration + views (scrape — no extra API calls).
# Only the gog search call consumes Data API quota; metadata is free via yt-dlp.
# Prints one TSV row per result, in gog's relevance order. Columns:
#   video_id <TAB> duration_seconds <TAB> view_count <TAB> channel <TAB> title
# Missing fields print as "NA". Drop shorts later by filtering duration < 180.
# Usage: gog-search.sh "<query>" [max=15]
#
# Required env:
#   GOG_ACCOUNT=you@example.com          # the OAuth'd Google account gog should use
# Optional env:
#   YT_DLP_COOKIES_FROM_BROWSER=chrome   # pass browser cookies to dodge bot walls
#                                        # on the yt-dlp enrichment (datacenter/CI IPs)
set -euo pipefail

q="${1:-}"
max="${2:-15}"
if [[ -z "$q" || "$q" == "-h" || "$q" == "--help" ]]; then
  echo "Usage: gog-search.sh \"<query>\" [max]   (requires GOG_ACCOUNT=<email>)"
  echo "Prints TSV: video_id<TAB>duration_seconds<TAB>view_count<TAB>channel<TAB>title"
  [[ -z "$q" ]] && exit 1 || exit 0
fi

acct="${GOG_ACCOUNT:-}"
if [[ -z "$acct" ]]; then
  echo "error: set GOG_ACCOUNT=<email> (the OAuth'd account gog should search with)" >&2
  exit 1
fi
if ! command -v gog >/dev/null 2>&1; then
  echo "error: gog not found on PATH — install it or use the yt-dlp-only skill instead" >&2
  exit 1
fi

# gog plain output: a header row, then 'video<TAB>ID<TAB>TITLE<TAB>CHANNEL<TAB>PUBLISHED'
# rows, then a trailing '# Next page:' line. Keep only video rows, take the ID,
# preserve gog's relevance order.
ids=$(gog yt search ls "$q" --account "$acct" --type video --max "$max" -p 2>/dev/null \
      | awk -F'\t' 'NR>1 && $1=="video" {print $2}')
if [[ -z "$ids" ]]; then
  exit 0
fi

# Enrich via yt-dlp (scrape, no API quota), preserving gog's order. Build URLs
# from the bare IDs and emit the full TSV contract incl. channel + duration.
urls=()
while IFS= read -r id; do
  [[ -n "$id" ]] && urls+=("https://youtu.be/$id")
done <<< "$ids"

cookies=()
[[ -n "${YT_DLP_COOKIES_FROM_BROWSER:-}" ]] && cookies=(--cookies-from-browser "$YT_DLP_COOKIES_FROM_BROWSER")

fmt=$'%(id)s\t%(duration)s\t%(view_count)s\t%(channel)s\t%(title)s'
uvx yt-dlp@latest --skip-download --no-warnings --ignore-errors \
  --retries 3 --extractor-retries 3 --sleep-requests 1 \
  ${cookies[@]+"${cookies[@]}"} \
  --print "$fmt" "${urls[@]}"
