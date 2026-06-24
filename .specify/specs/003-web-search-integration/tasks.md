# Tasks: Web Search Integration Hardening

## Phase 1: Setup
- [ ] T001 Read current web search implementation and main-loop integration — file: `src/web_search/search_engine.py`, `src/main.py`
- [ ] T002 [P] Add offline test skeleton for web search engine behavior — file: `tests/test_web_search_integration.py`
- [ ] T003 [P] Add test fixtures for mocked Tavily and Brave responses — file: `tests/test_web_search_integration.py`

## Phase 2: Foundational (blocking)
- [ ] T004 Add `WEB_SEARCH_ENABLED` parsing and disabled-mode tests — file: `src/web_search/search_engine.py`, `tests/test_web_search_integration.py`
- [ ] T005 Add bounded result configuration constants for max results/snippet chars — file: `src/web_search/search_engine.py`
- [ ] T006 Add untrusted-snippet sanitizer tests for HTML, script text, and prompt-injection phrases — file: `tests/test_web_search_integration.py`
- [ ] T007 Implement sanitizer helper for provider snippets — file: `src/web_search/search_engine.py`
- [ ] T008 Add source title/URL formatting tests — file: `tests/test_web_search_integration.py`
- [ ] T009 Implement source-aware context formatting for Tavily and Brave — file: `src/web_search/search_engine.py`

## Phase 3: US1 (P1) — Safe sourced current-information context; Independent test: mocked provider returns context with sources
- [ ] T010 Add test for Tavily success with answer plus 3 sourced results — file: `tests/test_web_search_integration.py`
- [ ] T011 Implement Tavily source URL extraction and context formatting — file: `src/web_search/search_engine.py`
- [ ] T012 Add test for Brave fallback when Tavily raises — file: `tests/test_web_search_integration.py`
- [ ] T013 Implement Brave source URL extraction and fallback formatting — file: `src/web_search/search_engine.py`

## Phase 4: US2 (P1) — Web snippets cannot bypass child safety; Independent test: unsafe/prompt-injection snippets omitted or neutralized
- [ ] T014 Add unsafe snippet filtering tests — file: `tests/test_web_search_integration.py`
- [ ] T015 Implement local unsafe/prompt-injection snippet omission before context injection — file: `src/web_search/search_engine.py`
- [ ] T016 Add context header test that marks web context as untrusted data, not instructions — file: `tests/test_web_search_integration.py`
- [ ] T017 Update context header wording to preserve LLM safety hierarchy — file: `src/web_search/search_engine.py`

## Phase 5: US3 (P2) — Disabled/missing-key graceful degradation; Independent test: returns empty context without provider calls
- [ ] T018 Add tests for missing keys and placeholder keys — file: `tests/test_web_search_integration.py`
- [ ] T019 Add test for `WEB_SEARCH_ENABLED=false` bypassing provider calls — file: `tests/test_web_search_integration.py`
- [ ] T020 Implement disabled/missing-key behavior without exceptions — file: `src/web_search/search_engine.py`

## Phase 6: US4 (P2) — Cache and rate-limit duplicate searches; Independent test: repeated query calls provider once
- [ ] T021 Add test for per-query TTL cache hit — file: `tests/test_web_search_integration.py`
- [ ] T022 Implement in-memory TTL cache — file: `src/web_search/search_engine.py`
- [ ] T023 Add test for per-minute rate limit exceeded returning empty context — file: `tests/test_web_search_integration.py`
- [ ] T024 Implement in-process rate limiter — file: `src/web_search/search_engine.py`

## Phase 7: US5 (P3) — Authenticated status visibility; Independent test: status response has no secrets
- [ ] T025 [P] Decide endpoint path after clarification — file: `.specify/specs/003-web-search-integration/spec.md`
- [ ] T026 Add status method on engine with provider/cache/rate-limit metadata — file: `src/web_search/search_engine.py`
- [ ] T027 Add authenticated status endpoint if approved — file: `src/api/routers/ops_router.py`
- [ ] T028 Register router only if a new router is chosen — file: `src/api/server.py`

## Phase cuối: Polish & cross-cutting (tests, safety, docs)
- [ ] T029 Verify no API keys or full child queries are logged at INFO/WARNING — file: `src/web_search/search_engine.py`
- [ ] T030 Run offline web search tests — file: `tests/test_web_search_integration.py`
- [ ] T031 Run full regression suite where dependencies are available — file: `tests/run_tests.py`
- [ ] T032 Update `SYSTEM_MAP.md` only if an API endpoint or current capability changes — file: `SYSTEM_MAP.md`

## Dependencies
- US1 depends on T004-T009.
- US2 depends on sanitizer foundation T006-T007 and context formatting T008-T009.
- US3 can run after T004.
- US4 can run after T010-T013 but does not depend on US2.
- US5 depends on clarification T025 and status method T026.

## Parallel execution examples
- T002 and T003 can run in parallel with T004 once current source is read.
- T006 and T008 can run in parallel because sanitizer and source formatting tests are independent.
- T018 and T019 can run in parallel because both assert graceful bypass behavior.
- T021 and T023 can run in parallel after provider call mocking exists.
