# AGENTS.md

Working notes for AI coding agents (Claude Code, Codex, OpenClaw, Hermes, Cursor…).
Humans are welcome to read it too: it is the shortest path to not breaking this repo.

## What this repository is

One small Python file that turns a Plaud recording into a text file via Groq Whisper, plus the
docs that explain the traps around it. Nothing else is required.

## Invariants — do not break these without saying so in the PR

1. **Standard library only.** No `requests`, no SDK, no framework. `urllib` is the whole dependency list.
2. **One core file.** `groq_transcribe.py` stays readable in one sitting. New behaviour belongs in
   the script only if it serves library-less users; otherwise it belongs in docs or `examples/`.
3. **Exit codes are an API.** `0` = transcript written, `1` = failure. Cron jobs, CI and agents
   branch on this. Never return `0` after printing an error.
4. **No secrets in the tree.** `GROQ_API_KEY` comes from the environment. Never write a key,
   a Plaud token, a presigned URL or a real transcript into a committed file.
5. **Audio and transcripts are local artifacts.** `*.mp3` and `transcripts/` are gitignored.
   Do not remove those rules to "make the example work".

## Layout

| Path | Role |
|---|---|
| `groq_transcribe.py` | the whole pipeline: multipart upload, error handling, size guard |
| `tests/` | stdlib `unittest`, network mocked with `unittest.mock` |
| `examples/` | synthetic sample output and the ffmpeg split helper |
| `README.md` / `README.ko.md` / `README.en.md` | English index / Korean guide / English guide |
| `.agents/skills/plaud-transcribe/` | Agent Skill other agents load to run this repo |

## Commands

```bash
# transcribe one file (Korean by default)
GROQ_API_KEY=... python3 groq_transcribe.py meeting.mp3

# other language, explicit model
GROQ_API_KEY=... python3 groq_transcribe.py interview.mp3 --language=en --model=whisper-large-v3

# tests — no network, no API key needed
python3 -m unittest discover -s tests -v
```

## Traps that are already handled — don't "clean them up"

- **Browser User-Agent header.** Without it Groq's edge returns `403 error code: 1010`. Looks
  redundant, isn't.
- **Reading the whole file into bytes before upload.** Fine at ≤24MB and keeps the multipart code
  short. Don't add streaming without a size test.
- **`Content-Type` derived from the extension.** Hard-coding `audio/mpeg` made wav/m4a uploads fail.

## Before opening a PR

- `python3 -m unittest discover -s tests` passes.
- Docs updated in **all three** READMEs (they are translations of each other, not drafts).
- Commit messages say what broke for a user, not which file you touched.
- Keep unrelated changes in separate commits — this repo is small enough that one revert should undo one idea.
