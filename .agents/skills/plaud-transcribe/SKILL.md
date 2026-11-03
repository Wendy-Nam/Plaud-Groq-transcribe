---
name: plaud-transcribe
description: Transcribe Plaud voice recorder audio (MP3/M4A/WAV) into Korean text with Groq Whisper using groq_transcribe.py. Use when someone hands over a Plaud recording or a meeting/coaching/interview audio file, asks to "전사", "녹음을 텍스트로", "받아쓰기", "transcribe this recording", or when a previous transcription came back empty, failed, was rejected with HTTP 400/403, or the file is over 24 MB and needs splitting first.
license: MIT
compatibility: Python 3.8+ standard library only (no pip install). Requires GROQ_API_KEY in the environment. ffmpeg is required only when the audio exceeds 24 MB.
---

# Plaud → text

One job: turn a local audio file into a plain-text transcript.

```
audio file → groq_transcribe.py → transcripts/<basename>.txt
```

The script is 74 lines and does exactly one HTTP POST to Groq. Everything it does not handle is in this skill.

## Non-negotiable checks

1. **`GROQ_API_KEY` must be set.** Without it the script exits 1 with `ERR: GROQ_API_KEY 환경변수 없음`. Never print the key.
2. **The script exits `0` even when Groq fails.** `transcribe()` catches `HTTPError` and generic exceptions, prints the message, and returns `None`; `__main__` never calls `sys.exit(1)`. **Never trust the exit code.** Verify the output file instead.
3. **`language` is hard-coded to `"ko"`** and the CLI does not expose it. Korean audio is the happy path.
4. **`Content-Type` is hard-coded to `audio/mpeg`** for every upload, whatever the real container is. Prefer `.mp3`; convert anything else first.

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

Groq rejects uploads above 25 MB. Split at 20 minutes, which is what the README recommends and what keeps each part well under the limit:

```bash
mkdir -p chunks
ffmpeg -hide_banner -loglevel error -i "$AUDIO" -c copy -f segment -segment_time 1200 \
  chunks/part_%03d.mp3
ls chunks
```

Transcribe the parts in name order and join them, so timestamps inside each part do not reorder the story:

```bash
for f in chunks/part_*.mp3; do
  python3 groq_transcribe.py "$f" "transcripts/$(basename "${f%.mp3}").txt"
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

Success prints `전사 성공: N자` and `저장: <path>`. If the file is missing or empty, the run failed even when the exit code was `0` and even if the console looked calm. Report the real failure; do not summarise a transcript that does not exist.

### 5. Report

Give the user the output path, the character count, and the model used. Do not paste the whole transcript into chat unless asked — point at the file.

## Failure modes

| Symptom | Cause | Action |
| --- | --- | --- |
| Console shows `HTTP 400` / `HTTP 403`, exit code `0` | Bad upload or rejected request; script swallows it | Read the printed body, fix the cause, re-run, re-verify the file |
| `HTTP 403` with `error code: 1010` | Cloudflare blocking a default `urllib` User-Agent | The script already sends a browser UA; do not remove or shorten that header |
| `file is empty` in the response | Groq transient degradation, or the chunk is too large | Wait 1–2 min, retry; if it repeats, split into smaller chunks (10–15 min), max 3 attempts |
| `ERR: 오디오 없음` | Path wrong | Resolve the absolute path, check `ls` |
| Empty transcript file, no error | Wrong `language`, silent audio, or a non-Korean recording decoded as Korean | Confirm the recording is actually Korean and audible; see below |
| `HTTP 413` / size error | Over the upload limit | Split at step 2, do not retry the same file |

## Non-Korean audio

The CLI cannot pass `language`, but the function can. Do not edit the script — call it:

```bash
python3 -c "import groq_transcribe as g; g.transcribe('audio.mp3', 'transcripts/audio.txt', language='en')"
```

Any other language code works the same way (`ja`, `zh`, `es`, …). Say plainly that the CLI path is Korean-only and that this is the workaround.

## Scope

- This skill transcribes an audio file that already exists on disk. Downloading from Plaud, OAuth token refresh, Drive upload, and scheduling are out of scope — the upstream README covers the manual path for those.
- Do not add dependencies to `groq_transcribe.py`. If a task needs chunking or upload, do it in the shell around the script, not inside it.
