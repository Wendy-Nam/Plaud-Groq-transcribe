#!/usr/bin/env python3
"""Groq Whisper로 로컬 오디오 파일을 전사합니다.
Cloudflare UA 차단(403 error code 1010)을 회피하는 User-Agent를 포함합니다.

Usage:
    GROQ_API_KEY=... python3 groq_transcribe.py <audio_path> [out_path] [model]

Defaults:
    out_path = ./transcripts/<basename>.txt  (먼저 mkdir -p transcripts)
    model    = whisper-large-v3-turbo        (정확도 우선 시 whisper-large-v3)
"""
import os, sys, json, urllib.request, urllib.error

API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

def transcribe(audio_path, out_path=None, model="whisper-large-v3-turbo", language="ko"):
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise SystemExit("ERR: GROQ_API_KEY 환경변수 없음")
    if not os.path.exists(audio_path):
        raise SystemExit(f"ERR: 오디오 없음 {audio_path}")

    fbytes = open(audio_path, "rb").read()
    print(f"오디오 크기: {len(fbytes)} bytes")

    if out_path is None:
        base = os.path.splitext(os.path.basename(audio_path))[0]
        out_path = f"transcripts/{base}.txt"
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    boundary = "----groq" + str(os.getpid())
    body = b""
    fields = [("model", model), ("temperature", "0"),
              ("response_format", "json"), ("language", language)]
    for name, val in fields:
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode()
        body += val.encode() + b"\r\n"
    fname = os.path.basename(audio_path)
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fname}\"\r\n".encode()
    body += b"Content-Type: audio/mpeg\r\n\r\n" + fbytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        # 필수: 없으면 Cloudflare 403 error code 1010
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    }
    req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode("utf-8")
        text = json.loads(raw).get("text", "")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"전사 성공: {len(text)}자")
        print(f"저장: {out_path}")
        return text
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8')[:400]}")
        return None
    except Exception as e:
        print(f"실패: {type(e).__name__} {str(e)[:300]}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    transcribe(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
               sys.argv[3] if len(sys.argv) > 3 else "whisper-large-v3-turbo")
