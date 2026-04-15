# AGENTS.md — Robot Bi (Codex CLI Project Instructions)

> Project: Robot Bi — AI tutor robot for children 5–12 years old  
> Updated: 2026-04-15  

## 1. Purpose

This repository contains **Robot Bi**, an AI tutor assistant for children aged 5–12, designed to run on **Windows PC/Laptop**.

Primary goals:
- natural Vietnamese tutoring interaction
- low-latency voice loop
- parent remote monitoring/control
- safe child-facing responses
- modular architecture for speech, vision, memory, and networking

## 2. Non-negotiable constraints

Follow these constraints unless the user explicitly asks to change them.

1. **Read `.claude/handoff.md` before making code changes.**
2. **Read the target file before editing it. Do not invent APIs, classes, or function names.**
3. **Main entry point is `src_brain/main_loop.py`.**
4. **LLM backend must go through `stream_chat(messages)` in `src_brain/ai_core/core_ai.py`.**
   - Primary: Groq
   - Fallback: Gemini
   - Do **not** reintroduce Ollama unless explicitly requested.
5. **Speech-to-text must remain based on `faster-whisper` in `ear_stt.py`.**
   - Auto-detect GPU/CPU
   - Do **not** switch to Google STT unless explicitly requested.
6. **Time-to-First-Audio must stay under 2 seconds when possible.**
   - Prefer streaming
   - Prefer queue-based audio playback
7. **Safety filter must run before any text is sent to TTS.**
8. **API keys must come from `.env`. Never hardcode secrets.**
9. **Do not commit `.env` or `ssl/`.**
10. **At the end of a coding session, update `.claude/handoff.md` with what changed, what remains, and any important caveats.**

## 3. Session workflow

This repository uses `.claude/handoff.md` as the **living session handoff log**.

Before making any code changes:
1. Read `.claude/handoff.md` fully to understand current project state, completed work, known issues, and the latest completed session.
2. Read the target file(s) before editing. Do not assume file contents from docs alone.
3. Make the smallest correct change that satisfies the request.

After completing any task:
1. Update `.claude/handoff.md` at the end of the file.
2. Record all of the following:
   - what was changed
   - which files were modified
   - what tests or checks were run
   - important technical decisions
   - remaining limitations, caveats, or next steps
3. Do not consider the task fully complete until `.claude/handoff.md` is updated.

## 4. Tech stack to preserve

Do not replace these technologies without explicit instruction.

| Layer | Current choice | Notes |
|---|---|---|
| LLM Primary | Groq `llama-3.3-70b-versatile` | fast primary model |
| LLM Fallback | Gemini `gemini-2.5-flash-lite` | fallback path |
| STT | `faster-whisper` | GPU: large-v2 float16 / CPU: small int8 |
| TTS | `edge-tts` + `pygame` | primary voice output |
| TTS Fallback | `pyttsx3` | offline fallback |
| Safety | regex + pattern matching | `safety_filter.py` |
| RAG | `chromadb` + `sentence-transformers` | multilingual retrieval |
| Vision | `opencv-python` | camera / motion / face |
| Cry Detection | YAMNet TFLite + energy fallback | see `cry_detector.py` |
| Network | `fastapi` + `uvicorn` + `websockets` | HTTPS on port 8443 |
| Tunnel | `cloudflared` | remote public access |
| Config | `.env` + `config.json` | settings + secrets |
| Runtime | Python 3.10+ | |

## 5. Repository map

```text
Robot_Bi_Project/
├── AGENTS.md                          ← Codex instructions
├── CLAUDE.md                          ← Claude-oriented project instructions
├── requirements.txt                   ← Keep synced with actual stack
├── config.json                        ← Robot configuration
├── .env                               ← API keys; never commit
├── generate_ssl.py                    ← Create SSL certificate
├── ssl/                               ← cert.pem + key.pem
├── run_tests.py                       ← Automated test runner
├── start_robot.bat                    ← Recommended Windows launcher
├── stress_test.py                     ← RAM / latency benchmark
├── HUONG_DAN_CHAY.md                  ← User run guide
├── .gitignore                         ← Must exclude .env, ssl/, __pycache__
├── docs/
│   ├── SRS_Robot_Bi.md
│   └── kehoach.md
├── .claude/
│   └── handoff.md                     ← Read before coding; update after coding
└── src_brain/
    ├── main_loop.py                   ← Main runtime entry point
    ├── train_text.py                  ← Text-only chat mode
    ├── ai_core/
    │   ├── core_ai.py                 ← `stream_chat(messages)` generator
    │   ├── safety_filter.py           ← SafetyFilter.check(text)
    │   └── prompts.py                 ← system / refusal / greeting prompts
    ├── senses/
    │   ├── ear_stt.py                 ← Speech-to-text
    │   ├── mouth_tts.py               ← Text-to-speech
    │   ├── eye_vision.py              ← Camera / face / motion logic
    │   ├── cry_detector.py            ← Cry detection
    │   └── models/                    ← YAMNet and related assets
    ├── network/
    │   ├── api_server.py              ← FastAPI HTTPS server + camera/audio APIs
    │   ├── notifier.py                ← Event notifications + WebSocket
    │   ├── task_manager.py            ← Tasks + rewards
    │   └── static/
    │       ├── index.html             ← Parent PWA app
    │       ├── manifest.json          ← PWA manifest
    │       ├── sw.js                  ← Service worker
    │       └── icon-192/512.png
    └── memory_rag/
        ├── rag_manager.py             ← RAG manager
        ├── bi_memory.json
        └── chroma_db/
```

## 6. Operating assumptions for Codex

When working in this repository:
- prefer **small, targeted edits** over broad rewrites
- preserve existing naming and architecture
- keep backward compatibility when practical
- do not refactor working modules just for style
- do not change libraries because of personal preference
- avoid adding infrastructure complexity unless the user asks
- preserve Windows usability
- treat latency, stability, and child safety as first-class requirements

## 7. Expected engineering priorities

Use this order of priority when tradeoffs appear:

1. correctness
2. child safety
3. low latency / responsiveness
4. compatibility with current architecture
5. maintainability
6. feature completeness

## 8. Known issues

| # | Issue | File | Severity |
|---|---|---|---|
| 1 | Wake-word "Bi ơi" is still a stub, not a real model | `ear_stt.py` | Low |
| 2 | Cry detector energy fallback is too sensitive | `cry_detector.py` | Low |
| 3 | Cloudflare URL changes after each restart | `api_server.py` | Low |
| 4 | iOS Safari needs HTTPS for parent mic | `index.html` | Fixed by HTTPS |
| 5 | Mobile may route robot audio to earpiece instead of speaker | `index.html` | In progress |
| 6 | YAMNet TFLite may fail to load if TensorFlow is missing | `cry_detector.py` | Low |

## 9. File-specific guidance

### `src_brain/ai_core/core_ai.py`
- This is the LLM integration center.
- Preserve the Groq-primary / Gemini-fallback design.
- Preserve streaming behavior.
- Avoid blocking response generation if a streaming path already exists.

### `src_brain/ai_core/safety_filter.py`
- Safety runs post-LLM and pre-TTS.
- Any response path that speaks aloud must pass through this filter.
- Be conservative with changes.

### `src_brain/senses/ear_stt.py`
- Preserve GPU/CPU auto-detection.
- Avoid regressions in Windows microphone handling.
- Do not silently increase latency.

### `src_brain/senses/mouth_tts.py`
- Primary: `edge-tts`
- Fallback: `pyttsx3`
- Keep playback robust under intermittent network conditions.

### `src_brain/network/api_server.py`
- HTTPS on port 8443 is intentional.
- Parent app compatibility matters.
- Cloudflare tunnel integration should remain functional.

### `src_brain/network/static/index.html`
- Parent-facing app.
- Features include status, chat, events, memory, tasks, roleplay, live camera, and direct parent mic.
- Be careful with mobile browser audio behavior.

### `src_brain/memory_rag/rag_manager.py`
- Preserve current memory behavior unless task explicitly targets memory semantics.
- Avoid destructive changes to stored memory format without migration logic.

## 10. Safe editing protocol

Before editing:
1. Read `.claude/handoff.md`
2. Read relevant source files
3. Identify the minimum viable change
4. Check whether the requested change touches latency, safety, or secrets

During editing:
1. Prefer local, reversible changes
2. Keep comments concise and useful
3. Avoid speculative abstractions
4. Do not invent tests that depend on unavailable hardware unless clearly marked/mocked

After editing:
1. Run the most relevant test(s)
2. Summarize exactly what changed
3. Note risks, assumptions, and unresolved issues
4. Update `.claude/handoff.md`

## 11. Testing guidance

Prefer running only the tests relevant to the modified area first, then broader tests if needed.

Common commands:

```bash
# First-time SSL setup
python generate_ssl.py

# Recommended launcher on Windows
start_robot.bat

# Direct run
python -m src_brain.main_loop

# Text-only chat mode
python src_brain/train_text.py

# Full automated tests
python run_tests.py

# Stress / latency checks
python stress_test.py

# Module-level checks
python src_brain/senses/ear_stt.py
python src_brain/senses/mouth_tts.py
python src_brain/ai_core/core_ai.py
python src_brain/memory_rag/rag_manager.py
```

Dependency install reference:

```bash
pip install requests python-dotenv faster-whisper edge-tts pygame \
    sounddevice numpy chromadb sentence-transformers pyttsx3 \
    opencv-python fastapi uvicorn websockets qrcode cryptography \
    --break-system-packages
```

Clear robot memory:

```bash
python -c "
from src_brain.memory_rag.rag_manager import RAGManager
RAGManager().clear_all_memories()
print('Đã xóa toàn bộ ký ức')
"
```

## 12. Runtime endpoints and access patterns

| Situation | URL | Notes |
|---|---|---|
| Same Wi‑Fi | `https://192.168.1.22:8443` | First use may require browser warning bypass |
| Remote / different network | `https://xxx.trycloudflare.com` | URL printed in terminal at startup |
| Local machine | `https://localhost:8443` | On robot host |

## 13. Config expectations

Current `config.json` pattern:

```json
{
  "robot_name": "Bi",
  "child_name": "",
  "language_mode": "auto",
  "english_practice_mode": false,
  "max_history_turns": 10,
  "primary_api": "groq",
  "groq_model": "llama-3.3-70b-versatile",
  "gemini_model": "gemini-2.5-flash-lite-preview-06-17",
  "groq_cooldown_seconds": 60,
  "daily_limit_warning": 13000
}
```

Respect this config-driven approach.
- Use `.env` for secrets
- Use `config.json` for behavior/settings
- Do not hardcode production values into source files

## 14. Session history summary

The project status inferred from current docs:
- core voice loop exists
- RAG exists
- camera exists
- safety filter exists
- TTS fallback exists
- cry detector exists
- notifier exists
- reward/task management exists
- PWA exists
- HTTPS exists
- Cloudflare tunnel exists
- Groq/Gemini migration is complete
- current automated test count is documented as **54+ PASS**

Treat the project as an already-working codebase that needs **careful improvement**, not a greenfield rewrite.

## 15. What Codex should avoid

Avoid these unless explicitly requested:
- replacing Groq/Gemini with a different LLM stack
- rearchitecting the app into a different framework
- removing Windows-first workflows
- introducing Docker-only assumptions for core local usage
- replacing `faster-whisper` with cloud STT
- bypassing the safety filter
- hardcoding keys or certificates
- changing large parts of the UI unrelated to the task
- broad renaming that breaks existing scripts/docs

## 16. Preferred response style when working on this repo

When reporting progress:
- explain what file(s) changed
- explain why
- state what was tested
- state what remains risky or unverified
- be explicit when hardware-dependent behavior could not be verified locally

## 17. Optional future structure improvements

These are not mandatory for every task, but are valid directions if the user asks for cleanup:
- add repository-local test grouping by subsystem
- add a dedicated troubleshooting doc for Windows audio/video issues
- add named Cloudflare tunnel support
- split parent app JavaScript into smaller modules if the front-end grows
- formalize migration notes for memory schema changes
