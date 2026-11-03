#!/usr/bin/env python3
"""examples/plaud_sync.py — Reference pipeline for syncing Plaud recordings.

Demonstrates polling audio recordings, downloading audio files, transcribing
via groq_transcribe.py, and tracking processed files in a local state JSON.

Note: Plaud's open API specifications and official tooling are evolving
(e.g., Plaud CLI / MCP at https://docs.plaud.ai). This script serves as a
reference automation template and should be adapted to your account setup.

Requirements:
    export PLAUD_ACCESS_TOKEN="your_plaud_access_token"
    export GROQ_API_KEY="gsk_..."

Usage:
    python3 examples/plaud_sync.py --dry-run
    python3 examples/plaud_sync.py --out-dir ./transcripts
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

PLAUD_API_BASE = "https://platform.plaud.ai/developer/api/open/third-party"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch_recordings(access_token, limit=20):
    url = f"{PLAUD_API_BASE}/file/list?page_size={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data.get("data_list") or data.get("file_list") or []


def main():
    parser = argparse.ArgumentParser(description="Sync Plaud recordings to Groq Whisper transcripts.")
    parser.add_argument("--out-dir", default="./transcripts", help="Directory for transcripts")
    parser.add_argument("--dry-run", action="store_true", help="List new recordings without transcribing")
    parser.add_argument("--language", default="ko", help="Whisper transcription language (default: ko)")
    parser.add_argument("--limit", type=int, default=10, help="Max files to process")
    args = parser.parse_args()

    token = os.environ.get("PLAUD_ACCESS_TOKEN")
    if not token:
        print("ERR: PLAUD_ACCESS_TOKEN environment variable not set.", file=sys.stderr)
        return 1

    if not os.environ.get("GROQ_API_KEY") and not args.dry_run:
        print("ERR: GROQ_API_KEY environment variable not set.", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    state_file = os.path.join(args.out_dir, ".sync_state.json")
    seen_ids = set()
    if os.path.exists(state_file):
        try:
            with open(state_file, encoding="utf-8") as f:
                seen_ids = set(json.load(f).get("processed", []))
        except Exception:
            pass

    print(f"Fetching recordings from Plaud API...")
    try:
        files = fetch_recordings(token, limit=args.limit)
    except Exception as e:
        print(f"ERR: Failed to fetch recordings: {e}", file=sys.stderr)
        return 1

    new_files = [f for f in files if f.get("id") not in seen_ids]
    print(f"Total found: {len(files)}, New un-synced: {len(new_files)}")

    if args.dry_run:
        for f in new_files:
            print(f"  [dry-run] Would sync: {f.get('name') or f.get('id')} ({f.get('duration', 0)}s)")
        return 0

    processed_count = 0
    for f in new_files:
        fid = f.get("id")
        fname = f.get("name") or fid
        audio_url = f.get("download_url") or f.get("url")
        if not audio_url:
            continue

        print(f"→ Downloading: {fname}...")
        tmp_audio = os.path.join(args.out_dir, f"{fid}.mp3")
        try:
            req = urllib.request.Request(audio_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp, open(tmp_audio, "wb") as out_f:
                out_f.write(resp.read())
        except Exception as e:
            print(f"  ERR: Download failed for {fname}: {e}", file=sys.stderr)
            continue

        out_txt = os.path.join(args.out_dir, f"{fname}.txt")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "groq_transcribe.py")
        print(f"→ Transcribing with groq_transcribe.py...")
        ret = subprocess.run([
            sys.executable,
            os.path.abspath(script),
            tmp_audio,
            out_txt,
            f"--language={args.language}"
        ])

        if os.path.exists(tmp_audio):
            try:
                os.remove(tmp_audio)
            except OSError:
                pass

        if ret.returncode == 0:
            seen_ids.add(fid)
            processed_count += 1
            print(f"  ✓ Saved: {out_txt}")
        else:
            print(f"  ✗ Transcription failed for {fname}", file=sys.stderr)

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"processed": list(seen_ids), "updated_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)

    print(f"Done. Successfully processed {processed_count} recording(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
