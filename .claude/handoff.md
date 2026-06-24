# Handoff - Robot Bi

> Current-state handoff only. Historical details belong in `changelog/`.
> Older "Last Completed Task" entries (pre-2026-06-24) archived in `changelog/2026-06-24-handoff-archive.md`.

## In Progress / Stopped Here

> THE resume anchor. When opening a new chat, read this first. Keep it honest and short:
> what is mid-flight, where it stopped, what is next. Clear it when the work lands.
> One opener covers everything: "Đọc PROJECT.md và .claude/handoff.md rồi tiếp tục."
> If a Spec Kit feature is active, the **Active spec** line below points to its folder —
> reading this file then leads straight to `tasks.md` (the real progress tracker).

- **Active branch**: `003-web-search-integration`.
- **Active spec**: none yet. When a Spec Kit feature is running, set this to its path,
  e.g. `.specify/specs/004-toeic-sw/` — read its `tasks.md` and continue from the first
  unticked task. (Spec Kit `.specify/` structure is created on the first `/speckit-specify`.)
- **OpenCode repo cleanup (DONE, 2026-06-24)**: verified `opencode.json`,
  `scripts/setup_opencode_bluesminds.sh`, and `scripts/test_bluesminds_api.sh` are absent
  from both `HEAD` and the working tree. Aider's temporary commit `31495c9` is not an
  ancestor of the active branch. The remaining OpenCode binary is outside the repo at
  `~/.nvm/versions/node/v22.19.0/bin/opencode` and was intentionally left untouched.
- **AI prompt-quality pass (opencode, REVIEWED OK — UNCOMMITTED, awaiting user go-ahead):**
  `src/ai/prompts.py`, `persona_manager.py`, `role_manager.py` edited by opencode to add
  age-tiering (5-6 / 7-9 / 10-12), clearer kid examples, and stronger TEACHER pedagogy
  (4-step flow). Verified by gatekeeper: scope clean (no Protected files touched), all
  exported names intact, `MAIN_SYSTEM_PROMPT is FRIEND_PROMPT`, `PROMPT_VERSION` bumped
  v1.0→v1.1, FRIEND/TEACHER stayed no-diacritics, PARENT_* stayed diacritics, all core
  guardrails (no auto-naming child, distress-first, danger refusal, lang-match) retained,
  imports clean. **NEXT**: commit these 3 files ONLY (do NOT bundle the pre-existing dirty
  `.gitignore`), then record commit id here. Not yet committed because pending user approval.
- **Learning Hub Phase 3 — HSG/exam packs (strategy: one subject deep at a time):**
  - DONE + committed (`20b6042`): `resources/learning/math_exam.json` — Toán fully covered, 6 papers / 42 questions (exam_grade6, exam_grade10, exam_thpt, hsg_school, hsg_district, hsg_province). 0 bad answers, unique paper_ids.
  - DONE + committed (`4771802`): `resources/learning/vietnamese_exam.json` — Tiếng Việt, 6 papers / 42 questions (same 6 tracks; subject='vietnamese'; comp_level set for hsg_*). Hand-authored language-focused MCQ (chính tả, từ loại, từ láy/ghép, biện pháp tu từ, thành phần câu, phong cách ngôn ngữ, hàm ý…). Validated: 0 bad answers, unique paper_ids.
  - DONE + committed (`21ed9e2`): `resources/learning/literature_exam.json` — Ngữ văn, 6 papers / 42 questions (same 6 tracks; subject='literature'; comp_level set for hsg_*). Hand-authored văn học MCQ (tác giả–tác phẩm, thể loại, nội dung/nghệ thuật, giá trị nhân đạo, phong cách, từ dân gian tiểu học → THPT/HSG). Validated: 0 bad answers, unique paper_ids.
  - DONE + committed (`abadc5d`): `resources/learning/english_exam.json` — Tiếng Anh, 6 papers / 42 questions (same 6 tracks; subject='en'; comp_level set for hsg_*). MCQ ngữ pháp/từ vựng có question_vi + giải thích tiếng Việt (tenses, conditionals, passive, đảo ngữ, phrasal verbs, idioms… từ tiểu học → HSG). Validated: 0 bad answers, unique paper_ids.
  - DONE + committed (`03152cb`): `resources/learning/science_exam.json` — Khoa học, 6 papers / 42 questions (subject='science'). KHTN tổng hợp. Validated 0 bad, unique ids.
  - DONE + committed (`005e111`): `resources/learning/physics_exam.json` — Vật lý, 6 papers / 42 questions (subject='physics'). Validated 0 bad, unique ids.
  - DONE + committed (`5c6ce1d`): `resources/learning/chemistry_exam.json` — Hóa học, 6 papers / 42 questions (subject='chemistry'). Validated 0 bad, unique ids.
  - DONE + committed (`238518c`): `resources/learning/biology_exam.json` — Sinh học, 6 papers / 42 questions (subject='biology'). Validated 0 bad, unique ids.
  - DONE + committed (`71cf079`): `resources/learning/history_exam.json` — Lịch sử, 6 papers / 42 questions (subject='history'). Validated 0 bad, unique ids.
  - DONE + committed (`eceb9c4`): `resources/learning/geography_exam.json` — Địa lý, 6 papers / 42 questions (subject='geography'). Validated 0 bad, unique ids.
  - DONE + committed (`2c51b57`): `resources/learning/civics_exam.json` — GDCD, 6 papers / 42 questions (subject='civics'). Validated 0 bad, unique ids.
  - DONE + committed (`0b25fbc`): `resources/learning/informatics_exam.json` — Tin học, 6 papers / 42 questions (subject='informatics'). Validated 0 bad, unique ids.
  - DONE + committed (`715ac47`): `resources/learning/programming_exam.json` — Lập trình, 6 papers / 42 questions (subject='programming'). Validated 0 bad, unique ids.
  - DONE + committed (`c9a8dd7`): `resources/learning/logic_exam.json` — Tư duy logic, 6 papers / 42 questions (subject='logic'). Validated 0 bad, unique ids.
  - DONE + committed (`3500576`): `resources/learning/economics_exam.json` — Kinh tế học, 6 papers / 42 questions (subject='economics'). Validated 0 bad, unique ids.
  - DONE + committed (`9d55009`): `resources/learning/health_exam.json` — Dinh dưỡng & Sức khỏe, 6 papers / 42 questions (subject='health'). Validated 0 bad, unique ids.
  - DONE + committed (`25131a0`): `resources/learning/life_skills_exam.json` — Kỹ năng sống, 6 papers / 42 questions (subject='life_skills'). Validated 0 bad, unique ids.
  - DONE + committed (`7575c24`): `resources/learning/music_exam.json` — Âm nhạc, 6 papers / 42 questions (subject='music'). Validated 0 bad, unique ids.
  - DONE + committed (`220c45f`): `resources/learning/art_exam.json` — Mỹ thuật, 6 papers / 42 questions (subject='art'). Validated 0 bad, unique ids.
  - DONE (uncommitted, 2026-06-24): `resources/learning/chinese_exam.json` — Tiếng Trung, 6 papers / 42 questions (subject='chinese'; comp_level set for hsg_*). Tracks dùng làm bậc sơ→nâng cao: chào hỏi, số đếm, chữ Hán cơ bản, pinyin/thanh điệu, ngữ pháp S-V-O, HSK, phồn/giản thể… Validated: 0 bad answers, unique paper_ids. Aggregate now: 24 subjects / 208 papers / 1502 questions / 0 invalid. **Ready to commit.**
  - **NEXT STEP (đang chạy tự động sau 07:15)**: 20 môn xong. Còn lại nếu còn quota: japanese, korean. Cùng pattern. Helper ở scratchpad (`build_exam_common.py`).
  - Pattern: new per-subject file `resources/learning/<subject>_exam.json`; `subject` field groups it (e.g. "vietnamese"/"literature"/"en"); unique paper_ids; tracks = exam_grade6/exam_grade10/exam_thpt/hsg_school/hsg_district/hsg_province (set `comp_level` for HSG). Seed = `_seed_learning_packs` (idempotent). ALWAYS validate answer∈options before committing (script in `changelog/`-style one-liner used 2026-06-24).
- **Tooling installed 2026-06-24** (separate from product code): codegraph MCP (local code knowledge graph; `.mcp.json` + `.codegraph/` index, telemetry off, loads on next Claude Code restart); new skills `taste-skill` (`design-taste-frontend`), `pdf`, `xlsx`; PROJECT.md UI-skill routing rule. Pre-existing dirty files (`speckit-git-*`, `settings.local.json`, `ui-ux-pro-max/scripts/search.py`) left untouched.
- **Next thread (not started)**: Learning Hub Phase 3 / remaining packs — `toeic_sw` (Speaking/Writing, needs free-text/STT grading) and HSG / exam-track papers (`hsg_*`, `exam_grade6/10`). Produce via the batch-generate pipeline (needs LLM keys) or hand-authoring. Curriculum blueprint already lists the topics.

## Current State

- `PROJECT.md` is the source of truth for rules, protected fixes, workflow, and AI context policy.
- Current source root is `src/`; `src_brain/` is deprecated and must not be used.
- Main entry point: `src/main.py`.
- API server: `src/api/server.py`.
- Parent App: `frontend/parent_app/`.
- Robot Display: `frontend/robot_display/`.
- Motor firmware: `firmware/Robot_BI/Robot_BI.ino`.
- ESP32-S3 audio hardware test: `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`.
- ESP32-S3 speaker-only test: `firmware/ESP32S3_Speaker_Test/ESP32S3_Speaker_Test.ino`.
- Runtime DB: `runtime/robot_bi.db`.
- Generated agent docs: `CLAUDE.md` and `AGENTS.md`, regenerated with `python sync.py` after `PROJECT.md` changes.
- Current test command: `python tests/run_tests.py`.
- Spec Kit skills live in `.claude/skills/speckit-*/` (embedded templates, not the `specify` CLI). `speckit-converge` added 2026-06-24 to match upstream v0.11.x.

## Last Completed Task

- 2026-06-24: **Learning Hub Phase 2 — content packs + batch AI generation** (branch `003-web-search-integration`):
  - `resources/learning/*.json` (16 packs): real curriculum-accurate MCQ content (English, Math, Science/Physics/Chemistry/Biology, IELTS, TOEIC L&R, Tiếng Việt, Ngữ văn, History/Geography/Civics, Chinese/Japanese/Korean). Every `answer` is exactly one of its `options` (validated).
  - `src/infrastructure/database/db.py`: `_seed_learning_packs(conn)` loads all `resources/learning/*.json` into `question_bank` (status='published', source='pack') + assembles `exam_papers`; skips any question whose answer ∉ options; idempotent. Called from `init_db()` after `_seed_exam_content`. **Pack JSON schema is documented in the function docstring.**
  - `src/api/routers/exam_router.py`: added `CURRICULUM_BLUEPRINT` (subject→topics map), `GET /api/learning/curriculum`, and `POST /api/learning/admin/generate-batch` (loops single-generate per topic into review queue; honors SKIP_LLM; bounded ≤200 questions/batch).
  - **2026-06-24 follow-up (same branch)**: added 8 more subject packs — `informatics`, `programming`, `music`, `art`, `economics`, `health`, `life_skills`, `logic` (each 3 exams). Added their SUBJECT_LABELS + CURRICULUM_BLUEPRINT entries in `exam_router.py`. Total published now: **24 subjects / 91 papers / 677 questions / 0 invalid answers**.
  - `tests/run_tests.py`: Group 80 thresholds set (≥85 papers, ≥640 questions, ≥22 subjects) and required-subject list extended.
  - **How to add content**: drop a new `resources/learning/<subject>.json` following the schema → it auto-seeds on next `init_db()`. The AI pipeline (`generate` / `generate-batch`) writes to `question_bank` status='review' → admin publishes.
  - **Still not packed**: `toeic_sw` (Phase 3 territory) and dedicated HSG/exam-track papers (`hsg_*`, `exam_grade6/10`). See In Progress above.

- 2026-06-24: **Learning Hub Phase 1 — exam system + AI question-bank pipeline** (branch `003-web-search-integration`, commit `a0943a9`):
  - `src/infrastructure/database/db.py`: Added 4 tables in `init_db()` — `question_bank`, `exam_papers`, `exam_paper_questions`, `exam_sessions` (+ indexes). New `_seed_exam_content(conn)` is idempotent (`INSERT OR IGNORE`) and seeds 3 starter papers.
  - `src/api/routers/exam_router.py` (NEW): `GET /api/learning/subjects`, `/api/learning/tracks` (11 tracks: practice / hsg_* / exam_* / ielts / toeic_lr / toeic_sw); `GET /api/learning/exams`, `GET /api/learning/exams/{paper_id}` (**answers + explanations hidden**), `POST /api/learning/exams/{paper_id}/submit` (auto-grade MCQ, store `exam_sessions`, return report w/ explanations + pass/fail), `GET /api/learning/exams/sessions[/{id}]`. Admin (is_admin via `require_admin`): `POST /api/learning/admin/generate` (LLM via `stream_chat`, honors `SKIP_LLM`), `GET /api/learning/admin/review`, `POST /api/learning/admin/review/{question_id}`, `POST /api/learning/admin/exams`.
  - **Route-order gotcha**: `/api/learning/exams/sessions` is declared BEFORE `/api/learning/exams/{paper_id}` so it is not shadowed. Test 79.7 guards this.
  - `src/api/server.py`: registered `exam_router`.
  - `frontend/parent_app/src/services/api.js`: added `getExamSubjects/getExamTracks/getExams/getExam/submitExam/getExamSessions/getExamSession` + admin helpers.
  - `frontend/parent_app/src/pages/LearningHubPage.jsx`: added `ModeToggle` (📚 Học theo chủ đề / 📝 Làm đề & Thi thử); track catalog → exam list → playing (timer + nav dots) → graded result. Vite build OK.
  - `tests/run_tests.py`: added Group 79 (9 tests).
  - **User-approved scope**: full subject catalog across ages 3–18 incl. Chinese/Japanese/Korean + Ngữ văn. Phase 3 = IELTS/TOEIC Speaking via Robot Bi STT.

> Older completed work (frontend wiring/polish, DeepSeek V3, Stage 1.5 body expression + web search,
> audit sprints, ESP32-S3 tests, Sprints 1.1–1.4) → `changelog/2026-06-24-handoff-archive.md` and
> the dated `changelog/*.md` files.

## Stage Status

- Parent App Backend Phase 3: COMPLETE.
- Stage 0: complete.
- Stage 1 software: complete through Sprint 1.4 hardening.
- Stage 1 manual validation: robot audio is blocked until the ESP32-S3 microphone hardware test passes and production audio transport is implemented.
- Stage 1.5 body expression: software landed (`movement_emotion.py`); pending real motor-hardware validation.
- Learning Hub: Phase 1 + Phase 2 complete (24 subjects). Phase 3 (Speaking/Writing + HSG/exam packs) not started.
- Stage 2 Special Memories: not started.

## Known Issues / Deferred Work

- Wake word disabled by default (`WAKEWORD_ENABLED=false`). Training pipeline exists, but real mic validation and trained custom model are pending.
- `edge-tts` primary TTS requires internet; pyttsx3 fallback remains local.
- ESP32-S3 mic/speaker hardware test exists; production network audio transport and display firmware do not.
- `follow_me.py`, `dock_charger.py`, `face_recognizer.py`, `fall_detector.py` are stubs/placeholders.
- Motor firmware has hardcoded IP `192.168.40.107:8443`; deployment-specific change needed.
- Cloudflare quick tunnel URL can change after restart unless a named tunnel is configured.
- Parent App radio/videos/games/system logs use mock fallbacks; several settings save buttons remain stubs.
- Provider quota can throttle Cerebras/Groq; fallback chain handled observed quota 429 warnings during tests.
- Current machine has no camera; this is supported and no longer blocks proactive behavior.
- Windows microphone diagnostics apply only to optional PC-connected microphones, not the two INMP441 modules on the robot.
- Learning Hub `toeic_sw` + HSG/exam-track papers not yet produced (need LLM keys or authoring).

## Next Recommended Action

1. **Learning Hub Phase 3 / remaining packs**: produce `toeic_sw` and `hsg_*` / `exam_grade6/10` papers via the batch-generate pipeline (needs LLM keys) or hand-authoring; topics already in `CURRICULUM_BLUEPRINT`.
2. Commit the current `.claude/skills/` tooling edits (incl. new `speckit-converge`) if satisfied.
3. Hardware track (independent): upload `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`, verify the beep/record/playback cycle, then implement ESP32-S3 network audio transport.
4. Do not start Stage 2 automatically.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched (Learning Hub Phase 1–2)

- `src/infrastructure/database/db.py`
- `src/api/routers/exam_router.py`
- `src/api/server.py`
- `resources/learning/*.json` (24 subject packs)
- `frontend/parent_app/src/services/api.js`
- `frontend/parent_app/src/pages/LearningHubPage.jsx`
- `tests/run_tests.py` (Groups 79 + 80)

## Files Recently Touched (Tooling — 2026-06-24)

- `.claude/skills/speckit-converge/SKILL.md` (new) — committed `0cc1c18`
- `.claude/skills/taste-skill/` (new, `design-taste-frontend`)
- `.claude/skills/pdf/`, `.claude/skills/xlsx/` (new, from anthropics/skills — proprietary license; scripts need Python deps NOT yet installed)
- `.claude/skills/karpathy-guidelines/` (new, MIT, SKILL.md only — behavioral guidelines: simplicity-first + surgical changes; additive, partial overlap with `robot-bi-dev`)
- `.mcp.json` (new, codegraph MCP server), `.gitignore` (+`.codegraph/`)
- `.claude/settings.json` (new) + `.claude/hooks/handoff-reminder.sh` (new) — Stop hook enforcing Rule 9: reminds to update handoff when src/frontend/resources/firmware changed but handoff.md wasn't. Read-only, self-clearing. **Needs `/hooks` reload or restart to activate** (project settings.json didn't exist at session start).
- `PROJECT.md` (UI-skill routing rule) → regenerated `CLAUDE.md` / `AGENTS.md` via `python3 sync.py`
- `changelog/2026-06-24-handoff-archive.md` (new) — committed `0cc1c18`
- `.claude/handoff.md`
