<p align="center">
  <img src="assets/hero.svg" alt="Plaud to Groq Whisper: voice in, text out" width="100%">
</p>

# Plaud-Groq-Transcribe

<p align="left">
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.8%2B-3776AB.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/PRs-welcome-ff69b4.svg" alt="PRs welcome">
</p>

**Automatically transcribe Plaud voice recordings using Groq Whisper.** Turn meetings, coaching sessions, and interviews into text — free, Korean-friendly, and production-tested.

> This repository is the **generalized (de-personalized) version**. Personal data (emails, accounts, internal paths) has been removed.

---

## Why use this

- **Free** — Runs on Groq's free tier (`whisper-large-v3`). No OpenAI or per-audio cost.
- **Korean-accurate** — Sets `language="ko"` for accurate transcription of Korean meetings, coaching, and interviews.
- **Simple** — Pure Python standard library (no `requests` needed). One-line setup.
- **Battle-tested workarounds included** — handles presigned-URL poisoning, Cloudflare blocking, and file-size limits that most tutorials skip.
- **Extensible** — auto-splits >25MB audio and can upload results to Google Drive.

In short: **a "record → text, instantly" meeting/coaching/interview log tool.**

---

## Pipeline

```mermaid
flowchart LR
    A["Plaud recorder<br/>list_files"] --> B["presigned URL<br/>1,700+ chars"]
    B --> C["MP3 on disk<br/>head -c3 = ID3"]
    C --> D{"File over 24 MB?"}
    D -- no --> E["groq_transcribe.py"]
    D -- yes --> S["ffmpeg -c copy<br/>-segment_time 1200"]
    S --> E
    E --> F["Groq Whisper<br/>whisper-large-v3-turbo"]
    F --> G["transcripts/*.txt"]
    G -. optional .-> H["Google Drive"]
```

Everything that can break between those two points is listed under [Pitfalls & solutions](#pitfalls--solutions-production-tested).

---

## Install

```bash
# Groq API key (free tier: console.groq.com)
export GROQ_API_KEY="gsk_..."
```

Works with the Python standard library — no extra package install required (`requests` is optional).

---

## Usage & examples

### Prepare
```bash
mkdir -p transcripts    # optional — the script creates it automatically
```

### Transcribe one file (default = fast model)
```bash
python3 groq_transcribe.py meeting.mp3
# → transcripts/meeting.txt  (finishes in ~1–2 min)
```

### Accuracy-first + custom output path
```bash
python3 groq_transcribe.py lecture.mp3 ./out/lecture.txt whisper-large-v3
```

### Example run (real input/output)

Input: `/audio/coaching1.mp3` (4.6MB / 14 min)

```bash
python3 groq_transcribe.py /audio/coaching1.mp3
```

Console output:
```
오디오 크기: 4600000 bytes
전사 성공: 12,340자
저장: transcripts/coaching1.txt
```

Resulting `transcripts/coaching1.txt` (excerpt):

```
안녕하세요, 오늘 코칭 세션의 목표는...
```

---

## Pitfalls & solutions (production-tested)

### 1. Presigned-URL poisoning — the most common failure cause
Plaud presigned URLs are **1,700+ characters** (mostly the `X-Amz-Security-Token`). If you hand-paste the URL into code, even one mistyped character triggers **HTTP 400/403**.

**Fix**:
1. Save the URL to a file (e.g. `url.txt`).
2. Download with `curl -sL -o out.mp3 "$(cat url.txt)"`.
3. Verify with `head -c3 out.mp3` → `ID3` is good; `<?xml`/`<Error>` means corrupted URL.

### 2. Groq `file is empty` (intermittent)
Caused by Groq session degradation or files >15MB.
→ Wait 1–2 min and retry; split files >15MB into 10–15 min chunks; max 3 attempts.

### 3. Groq 403 `error code: 1010` = Cloudflare UA block
The audio-upload endpoint blocks the default `urllib` User-Agent. → Set a browser User-Agent header (bundled in this script).

### 4. 25MB Groq limit
Plaud codec ≈ 0.23MB/min → ~109 min/file cap.
→ Split into 20-min chunks with `ffmpeg -c copy -segment_time 1200`.

---

## License
MIT

## Disclaimer
Built for personal use. Not an official Plaud or Groq product.