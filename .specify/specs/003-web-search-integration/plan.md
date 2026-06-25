# Implementation Plan: Web Search Integration Hardening

## Technical Context
- Python/FastAPI backend, source root `src/`.
- Existing web search module: `src/web_search/search_engine.py` with Tavily primary and Brave fallback via `requests`.
- Existing integration: `src/main.py` creates `WebSearchEngine()` and injects `web_context` alongside RAG before `self.brain.stream_chat(...)` in both text and voice paths.
- Current LLM stack remains the project-defined 5-provider chain in `src/ai/ai_engine.py`; this plan does not modify it.
- Tests should be stdlib/unittest-style or existing `tests/run_tests.py` group additions if implementation owner chooses, but must not require internet/API keys.

## Constitution / Protected-Fixes Check
- Do not modify LLM provider order: Cerebras -> Groq -> Sambanova -> Gemini -> Cloudflare Workers AI.
- Do not modify `src/ai/ai_engine.py` unless absolutely necessary for context wording; current plan avoids it.
- Do not alter SafetyFilter placement; web context hardening is pre-LLM defense-in-depth only.
- Do not alter RAG threshold `0.62`, deduplication, or family-scoped ChromaDB filters.
- Do not change SQLite DB path `runtime/robot_bi.db`.
- Do not log secrets or full child utterances at INFO/WARNING.

## Architecture & Affected Files
- MODIFY `src/web_search/search_engine.py`: add config flag, sanitizer, source formatting, cache, rate limiter, status method, and safer logging.
- MODIFY `src/api/routers/ops_router.py` or NEW `src/api/routers/web_search_router.py`: optional authenticated status endpoint if product owner wants visibility.
- MODIFY `src/api/server.py`: only if adding a new router; avoid otherwise.
- MODIFY `tests/run_tests.py` or NEW `tests/test_web_search_integration.py`: offline tests with mocked `requests`; implementation owner should choose based on current test policy.
- Do not modify `src/main.py` unless the final context contract changes from a plain string to structured metadata.

## Data / Schema changes
- No SQLite schema change for P1/P2.
- In-memory cache only: dictionary keyed by normalized query with TTL and provider metadata.
- [NEEDS CLARIFICATION] Persistent search audit would require a new family-scoped table, but this is out of scope for the hardening pass.

## API / Contracts
- Existing internal contract: `WebSearchEngine.search_if_needed(query: str) -> str` remains unchanged.
- Optional endpoint: `GET /api/web-search/status` or `GET /api/status/web-search`.
- Optional response shape:
```json
{
  "enabled": true,
  "providers": ["tavily", "brave"],
  "timeout_seconds": 5,
  "cache_size": 3,
  "rate_limit": {"max_per_minute": 10, "remaining": 8}
}
```
- Endpoint must require `get_current_user`; response must not include API key values.

## Phases
- Phase 0 research: Confirm current web search behavior, trigger list, main-loop integration points, and provider response formats.
- Phase 1 design: Define sanitizer rules, source formatting, env names, cache/rate limit defaults, and optional status endpoint path.
- Phase 2 implementation-ready: Add tests first around `WebSearchEngine`, then implement small isolated changes in `search_engine.py`, then optional status endpoint.
- Phase 3 verification: Run offline web search tests and full `python tests/run_tests.py` where dependencies are available.

## Risks & Open Questions
- Search snippets are untrusted and may contain prompt injection.
- Over-triggering web search may send unnecessary child queries to third-party providers.
- Under-triggering may leave current events unanswered.
- Cache is process-local and resets on restart.
- [NEEDS CLARIFICATION] Source citation behavior for child-facing voice responses.
- [NEEDS CLARIFICATION] Whether likely-PII queries should be blocked from web search.
