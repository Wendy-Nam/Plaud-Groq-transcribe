#!/usr/bin/env bash
# Split a long recording into Groq-sized chunks and transcribe each one.
#
#   ./examples/split-and-transcribe.sh ~/audio/board-meeting.mp3
#   ./examples/split-and-transcribe.sh ~/audio/interview.m4a --language=en
#
# Requires: ffmpeg, GROQ_API_KEY, and groq_transcribe.py in the repo root.
# Chunks and partial transcripts land in transcripts/<name>/ next to the output.
set -euo pipefail

if [ $# -lt 1 ]; then
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi

AUDIO="$1"; shift
[ -f "$AUDIO" ] || { echo "ERR: no such file: $AUDIO" >&2; exit 1; }
[ -n "${GROQ_API_KEY:-}" ] || { echo "ERR: GROQ_API_KEY is not set" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ERR: ffmpeg not found" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="$(basename "${AUDIO%.*}")"
WORK="transcripts/$NAME"
mkdir -p "$WORK"

# 24MB at Plaud's ~0.23MB/min is well over an hour, so 20 minutes per chunk is
# the safe default that also keeps each request comfortably under the limit.
SEGMENT="${SEGMENT_SECONDS:-1200}"

echo "splitting $AUDIO into ${SEGMENT}s chunks -> $WORK"
ffmpeg -y -loglevel error -i "$AUDIO" -c copy \
  -segment_time "$SEGMENT" -f segment "$WORK/chunk_%03d.mp3"

shopt -s nullglob
chunks=("$WORK"/chunk_*.mp3)
[ ${#chunks[@]} -gt 0 ] || { echo "ERR: ffmpeg produced no chunks" >&2; exit 1; }

merged="$WORK/$NAME.txt"
: > "$merged"
failed=0
for chunk in "${chunks[@]}"; do
  echo "→ $(basename "$chunk")"
  if python3 "$ROOT/groq_transcribe.py" "$chunk" "$chunk.txt" "$@" >>"$WORK/run.log" 2>&1; then
    [ -s "$chunk.txt" ] && { cat "$chunk.txt" >> "$merged"; printf '\n\n' >> "$merged"; }
  else
    echo "  failed, see $WORK/run.log" >&2
    failed=$((failed + 1))
  fi
done

chars=$(wc -m < "$merged" | tr -d ' ')
echo "done: $merged ($chars chars, $failed failed chunk(s))"
[ "$failed" -eq 0 ] || exit 1
