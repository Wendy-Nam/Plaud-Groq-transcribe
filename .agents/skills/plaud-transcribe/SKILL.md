---
name: plaud-transcribe
description: Transcribe Plaud voice recorder audio (MP3/M4A/WAV) into Korean text with Groq Whisper using groq_transcribe.py. Use when someone hands over a Plaud recording or a meeting/coaching/interview audio file, asks to "전사", "녹음을 텍스트로", "받아쓰기", "transcribe this recording", or when a previous transcription came back empty, failed, was rejected with HTTP 400/403, or the file is over 24 MB and needs splitting first.
compatibility: Python 3.8+ standard library only (no pip install). Requires GROQ_API_KEY in the environment. ffmpeg is required only when the audio exceeds 24 MB.
---

# Plaud → text

One job: turn a local audio file into a plain-text transcript.

```
audio file → groq_transcribe.py → transcripts/<basename>.txt
```

The script is 119 lines and does exactly one HTTP POST to Groq. Everything it does not handle is in this skill.

## Non-negotiable checks

1. **`GROQ_API_KEY` must be set.** Without it the script exits 1 with `ERR: GROQ_API_KEY 환경변수 없음`. Never print the key.
2. **Exit code is meaningful now.** `transcribe()` returns `None` on HTTP errors, oversize input, and empty results, and `__main__` ends with `sys.exit(0 if text is not None else 1)`. A non-zero exit means nothing was written.
3. **`language` defaults to `ko` but is overridable**: `--language=en`, `--language=ja`, or `GROQ_LANGUAGE` in the environment. `--language=` (empty) omits the field so Groq auto-detects.
4. **`Content-Type` follows the file extension** (`CONTENT_TYPES` in the script covers mp3/m4a/wav/ogg/flac/webm), so there is no need to convert containers before upload. Still verify the output file: a `0` exit only means a non-empty string came back.

## Workflow

### 1. Verify the input

```bash
ls -l "$AUDIO"
head -c3 "$AUDIO"        # ID3 for mp3; "<?x" or "<Er" means a broken download
```

If it starts with `<`, the file is an XML error body from a poisoned presigned URL, not audio. Re-download:

```bash
curl -sL -o out.mp3 "$(cat url.txt)"    # keep the URL in a file, never paste a 1,700-char URL into code
head -c3 out.mp3
```

### 2. Split anything over 24 MB

Groq rejects uploads above 25 MB. Split at 15 minutes (900 s), which stays inside the 10–15 minute window the failure table below recommends:

```bash
EXT="${AUDIO##*.}"
mkdir -p chunks
ffmpeg -hide_banner -loglevel error -i "$AUDIO" -c copy -f segment -segment_time 900 \
  "chunks/part_%03d.$EXT"
ls chunks
```

Keep the source extension with `-c copy`. Asking the segment muxer for `.mp3` output while copying an AAC/Opus/Vorbis stream fails with `Exactly one MP3 audio stream is required`; leave the container alone and the uploaded `Content-Type` still matches.

Transcribe the parts in name order and join them, so timestamps inside each part do not reorder the story:

```bash
for f in chunks/part_*."$EXT"; do
  python3 groq_transcribe.py "$f" "transcripts/$(basename "${f%.$EXT}").txt"
done
cat transcripts/part_*.txt > "transcripts/<basename>.txt"
rm -rf chunks
```

### 3. Transcribe

```bash
python3 groq_transcribe.py meeting.mp3                      # fast model, transcripts/meeting.txt
python3 groq_transcribe.py lecture.mp3 out/lecture.txt whisper-large-v3   # accuracy first
```

### 4. Verify — mandatory

```bash
test -s "transcripts/meeting.txt" && wc -m < "transcripts/meeting.txt"
```

Success prints `전사 성공: N자` and `저장: <path>` and exits `0`. A non-zero exit already means nothing was written, but check the file anyway (a stale transcript from an earlier run can sit at the same path). Report the real failure; do not summarise a transcript that does not exist.

### 5. Report

Give the user the output path, the character count, and the model used. Do not paste the whole transcript into chat unless asked — point at the file.

## Failure modes

| Symptom | Cause | Action |
| --- | --- | --- |
| Console shows `HTTP 400` / `HTTP 403`, non-zero exit | Bad upload or rejected request | Read the printed body, fix the cause, re-run, re-verify the file |
| `HTTP 403` with `error code: 1010` | Cloudflare blocking a default `urllib` User-Agent | The script already sends a browser UA; do not remove or shorten that header |
| `file is empty` in the response | Groq transient degradation, or the chunk is too large | Wait 1–2 min, retry; if it repeats, split into smaller chunks (10–15 min), max 3 attempts |
| `ERR: 오디오 없음` | Path wrong | Resolve the absolute path, check `ls` |
| Empty transcript file, no error | Wrong `language`, silent audio, or a non-Korean recording decoded as Korean | Confirm the recording is actually Korean and audible; see below |
| `HTTP 413` / size error | Over the upload limit | Split at step 2, do not retry the same file |

## Non-Korean audio

Pass the flag:

```bash
python3 groq_transcribe.py audio.m4a transcripts/audio.txt --language=en
```

Any language code works the same way (`ja`, `zh`, `es`, …). Omitting the flag means Korean; `--language=` means auto-detect.

## Scope

- This skill transcribes an audio file that already exists on disk. Downloading from Plaud, OAuth token refresh, Drive upload, and scheduling are out of scope — the upstream README covers the manual path for those.
- Do not add dependencies to `groq_transcribe.py`. If a task needs chunking or upload, do it in the shell around the script, not inside it.
