# 2026-04-30 — Review Round 5 Security Fixes

## Scope

- Fix Critical + High security issues from review round 5.
- Keep existing protected behavior unchanged.
- Add Group 50 verification tests.

## Changes

- `src/infrastructure/database/db.py`: added `ALLOWED_CLEANUP_TABLES` validation before dynamic cleanup table deletes in `delete_family_record()`.
- `src/ai/ai_engine.py`: removed Gemini API key from request URL and sent it through `x-goog-api-key`; added `_groq_lock` for Groq fail streak/cooldown globals.
- `src/infrastructure/auth/auth.py`: no code change; verified argon2-cffi expects `verify(hash, password)`, matching existing `verify_password(plain, hashed)`.
- `src/api/routers/auth_router.py`: changed PIN comparison to `hmac.compare_digest()` and added guarded JSON parsing that returns 422 on malformed JSON.
- `src/main.py`: changed assistant persistence condition to `sanitized_reply`, dispatches RAG extraction before closing the session, and reuses one `pygame.time.Clock()` in the audio worker loop.
- `src/api/routers/analytics_router.py`: made count conversion NULL-safe.
- `src/safety/safety_filter.py`: replaced regex word boundaries with Unicode-aware lookaround boundaries.
- `src/api/routers/conversation_router.py`: fixed homework conversation `total` to use a COUNT query instead of current page length.
- `tests/run_tests.py`: added Group 50 with 9 security/quality verification tests.

## Verification

- After Critical 1: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Critical 2: `python3 tests/run_tests.py` -> 329/329 PASS.
- Critical 3 argon2 check: `verify(hash, pass)` OK; reversed order failed as expected; no code change.
- After High 1: `python3 tests/run_tests.py` -> 329/329 PASS.
- After High 2: `python3 tests/run_tests.py` -> 329/329 PASS.
- After High 3: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 1: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 2: `python3 tests/run_tests.py` -> 329/329 PASS.
- Medium 3 regex check: `khiêu dâm` matched with Unicode-aware boundary.
- After Medium 3: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 4: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 5: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Group 50: `python3 tests/run_tests.py` -> 338/338 PASS.
