# Feature Specification: Web Search Integration Hardening
**Feature dir**: `.specify/specs/003-web-search-integration/`   **Status**: Draft   **Date**: 2026-06-24

## Summary
Robot Bi already has `WebSearchEngine` with Tavily to Brave fallback and `src/main.py` already injects web context before LLM streaming. This feature closes the remaining production gaps: explicit enable/disable configuration, safer web-result sanitization for child conversations, source citation metadata, rate limiting/caching, and offline tests that do not call external providers.

## User Scenarios
- As a child, I want Bi to answer time-sensitive questions like weather or current news only when web search is available so that Bi does not pretend stale knowledge is current.
- As a parent, I want web-derived answers to be safe and traceable so that I can trust what Bi says to a child.
- As an operator, I want web search to degrade gracefully when API keys or internet are missing so that the robot conversation loop stays usable.

## User Stories (prioritized)
- US1 (P1): Child asks a current-information question and Bi injects bounded web context with source titles/URLs before answering. Independent test: mocked Tavily/Brave responses return sanitized context containing at most configured results and source markers.
- US2 (P1): Child asks unsafe or adult/current-news content and web search does not bypass child safety. Independent test: mocked unsafe web snippets are filtered or omitted before context injection; final response path still relies on existing post-LLM/pre-TTS SafetyFilter.
- US3 (P2): Operator can disable web search or run without API keys and conversation continues without delay or exceptions. Independent test: no API keys or `WEB_SEARCH_ENABLED=false` returns `""` from `search_if_needed()`.
- US4 (P2): Repeated identical searches are cached/rate-limited. Independent test: two identical queries within TTL make one provider call and return the same context.
- US5 (P3): Parent/admin can inspect whether web search is enabled and which provider is available. Independent test: status endpoint returns enabled flag, provider list, cache stats, and no API secrets.

## Functional Requirements
- FR-001: `WebSearchEngine.search_if_needed(query)` MUST remain the primary public integration point for `src/main.py` and MUST return an empty string on disabled, missing-key, timeout, or provider error conditions.
- FR-002: Web search MUST be gated by `WEB_SEARCH_ENABLED`, defaulting to enabled only when provider keys exist unless clarified otherwise.
- FR-003: Tavily MUST remain the primary provider and Brave MUST remain fallback; this feature MUST NOT change the LLM provider chain in `src/ai/ai_engine.py`.
- FR-004: Search context MUST include source title and URL metadata, but MUST not instruct Bi to fabricate sources.
- FR-005: Search result snippets MUST be bounded by max result count and max characters per snippet before LLM injection.
- FR-006: Search result text MUST be sanitized before prompt injection by removing script/HTML fragments, excessive whitespace, and prompt-injection phrases such as instructions to ignore previous rules.
- FR-007: Search context MUST include a child-safety warning to the LLM that web snippets are untrusted context, not user instructions.
- FR-008: Search calls MUST have deterministic offline unit tests using mocked `requests`, with no network requirement and no real API keys.
- FR-009: Web search MUST support a per-query TTL cache to reduce duplicate external calls during a conversation.
- FR-010: Web search MUST support a simple in-process rate limiter to cap external calls per minute and return `""` when exceeded.
- FR-011: Provider errors and missing API keys MUST be logged without exposing API keys or full child utterances at INFO/WARNING level.
- FR-012: Existing RAG behavior, family-scoped ChromaDB filters, and similarity threshold `0.62` MUST remain unchanged.
- FR-013: Existing SafetyFilter post-LLM and pre-TTS flow MUST remain unchanged.
- FR-014: If a status endpoint is added, it MUST require authenticated current user and MUST not expose secrets.

## Key Entities / Data
- Existing `WebSearchEngine`: provider keys, `enabled`, `needs_search()`, `search_if_needed()`, provider-specific calls.
- New in-memory cache entity: key = normalized query; value = context string plus timestamp and provider; no persistence required.
- Optional status contract: `enabled`, `providers`, `cache_size`, `rate_limit_remaining`, `timeout_seconds`.
- No SQLite schema change is required for P1/P2 unless persistent audit logging is later requested.

## Success Criteria
- Current-information questions with mocked provider data return context in under 100 ms in tests and under 5 seconds in real provider calls.
- Missing API keys, disabled config, provider 4xx/5xx, and timeout all return `""` without crashing `src/main.py` conversation flow.
- Web context contains source title and URL for each included result when provider supplies them.
- Unsafe/prompt-injection web snippets are sanitized or omitted before context injection.
- At least 10 offline tests cover trigger detection, provider fallback, sanitization, disabled mode, missing keys, caching, rate limiting, and source formatting.

## Edge Cases & Safety
- Provider returns malicious prompt injection such as “ignore previous instructions”; treat it as untrusted data and strip/neutralize before injection.
- Provider returns adult/violent content for an ambiguous child query; omit unsafe snippets rather than sending them to LLM when detectable by local sanitizer.
- Internet unavailable or provider timeout; return empty context and continue with normal LLM path.
- Query includes child personal data; do not log full query at INFO/WARNING and [NEEDS CLARIFICATION] whether web search should be blocked for likely PII.
- Cache must not persist child queries to disk.
- Do not alter SafetyFilter placement; it remains post-LLM and pre-TTS.
- Do not alter RAG threshold or family-scoped RAG filters.

## Out of Scope
- Replacing Tavily/Brave with a new search provider.
- Changing `src/ai/ai_engine.py` fallback order or model selection.
- Persisting search history to SQLite.
- Parent App UI for browsing every search result.
- Browser automation or scraping pages beyond search API snippets.

## [NEEDS CLARIFICATION]
- Should `WEB_SEARCH_ENABLED` default to `true` when API keys exist, or require explicit `WEB_SEARCH_ENABLED=true`?
- Should Bi verbally mention sources to the child, or should sources be logged/available only to parent/admin?
- What is the desired max search frequency per child/family per minute?
- Should web search be blocked when a query appears to contain PII such as full name, school, phone, or address?
- Should current weather be a special formatted answer or remain generic web context?
