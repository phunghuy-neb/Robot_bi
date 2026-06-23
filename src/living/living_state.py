"""
Living State Engine — Bi's inner life state machine.

State is computed lazily from timestamps. No threads, no DB.
Integration: call on_interaction_start() at turn start, on_reply_done() after reply.
Inject get_state_context_hint() into system prompt before stream_chat().
"""
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Idle decay thresholds — all measured as cumulative seconds from _last_interaction_at.
# Timeline: ACTIVE_HAPPY (0–20 min) → IDLE_CURIOUS (20–40 min) → IDLE_SLEEPY (40–60 min)
#           → POUTING (60–120 min) → MISSING_KID (120+ min)
_HAPPY_TO_CURIOUS_SECS   = 20 * 60   # 20 min total idle → lose happy glow
_CURIOUS_TO_SLEEPY_SECS  = 40 * 60   # 40 min total idle (20 min in IDLE_CURIOUS) → sleepy
_SLEEPY_TO_POUTING_SECS  = 60 * 60   # 60 min total idle (20 min in IDLE_SLEEPY) → pouting
_POUTING_TO_MISSING_SECS = 120 * 60  # 120 min total idle → missing kid


class BiState(Enum):
    IDLE_CURIOUS   = "idle_curious"
    IDLE_SLEEPY    = "idle_sleepy"
    ACTIVE_HAPPY   = "active_happy"
    ACTIVE_ENGAGED = "active_engaged"
    POUTING        = "pouting"
    THINKING       = "thinking"
    MISSING_KID    = "missing_kid"


# Short Vietnamese hints injected into system prompt
_STATE_CONTEXT: dict[BiState, str] = {
    BiState.IDLE_CURIOUS:   "Bi đang tò mò, sẵn sàng trò chuyện.",
    BiState.IDLE_SLEEPY:    "Bi đang hơi buồn ngủ, trả lời nhẹ nhàng và ngắn hơn bình thường.",
    BiState.ACTIVE_HAPPY:   "Bi đang rất vui và phấn khởi sau cuộc trò chuyện vừa rồi.",
    BiState.ACTIVE_ENGAGED: "Bi đang tập trung lắng nghe bé.",
    BiState.POUTING:        "Bi đang hờn nhẹ vì bé bỏ đi lâu. Hờn dỗi tự nhiên, KHÔNG nói câu khiến bé thấy có lỗi.",
    BiState.THINKING:       "Bi đang suy nghĩ kỹ trước khi trả lời.",
    BiState.MISSING_KID:    "Bi nhớ bé rất nhiều. Rất vui khi bé quay lại — ấm áp và chào đón, không trách móc.",
}


class LivingStateEngine:
    """
    Runtime-only state machine for Bi's inner life.
    Idle-decay transitions are evaluated lazily on get_state() — no background thread needed.
    """

    def __init__(self):
        self._state: BiState = BiState.IDLE_CURIOUS
        self._previous_state: BiState = BiState.IDLE_CURIOUS
        self._last_interaction_at: float = time.time()

    # ── Event hooks called by main.py ─────────────────────────────────────────

    def on_interaction_start(self) -> None:
        """Call at the start of each user turn (voice or text)."""
        prev = self.get_state()
        self._previous_state = prev
        self._state = BiState.ACTIVE_ENGAGED
        self._last_interaction_at = time.time()
        logger.debug("[LivingState] %s → ACTIVE_ENGAGED", prev.value)

    def on_thinking_start(self) -> None:
        """Call just before stream_chat() to signal Bi is thinking."""
        self._state = BiState.THINKING
        logger.debug("[LivingState] → THINKING")

    def on_reply_done(self) -> None:
        """Call after TTS/text reply is fully delivered."""
        prev = self._state
        self._state = BiState.ACTIVE_HAPPY
        self._previous_state = BiState.ACTIVE_HAPPY
        self._last_interaction_at = time.time()
        logger.debug("[LivingState] %s → ACTIVE_HAPPY", prev.value)

    def on_turn_aborted(self) -> None:
        """Call when a turn starts but no reply is delivered."""
        prev = self._state
        self._state = self._previous_state
        self._last_interaction_at = time.time()
        logger.debug("[LivingState] %s → %s (aborted)", prev.value, self._state.value)

    # ── State query ───────────────────────────────────────────────────────────

    def get_state(self) -> BiState:
        """Return current state, applying idle-decay transitions lazily."""
        # Active states are not subject to idle decay
        if self._state in (BiState.ACTIVE_ENGAGED, BiState.THINKING):
            return self._state

        idle = time.time() - self._last_interaction_at

        if self._state == BiState.ACTIVE_HAPPY:
            if idle < _HAPPY_TO_CURIOUS_SECS:
                return BiState.ACTIVE_HAPPY
            self._state = BiState.IDLE_CURIOUS

        if self._state == BiState.IDLE_CURIOUS:
            if idle >= _SLEEPY_TO_POUTING_SECS:
                self._state = BiState.POUTING
            elif idle >= _CURIOUS_TO_SLEEPY_SECS:
                self._state = BiState.IDLE_SLEEPY
            return self._state

        if self._state == BiState.IDLE_SLEEPY:
            if idle >= _SLEEPY_TO_POUTING_SECS:
                self._state = BiState.POUTING
            return self._state

        if self._state == BiState.POUTING:
            if idle >= _POUTING_TO_MISSING_SECS:
                self._state = BiState.MISSING_KID
            return self._state

        return self._state

    def get_state_name(self) -> str:
        """Return state value string (e.g. 'idle_curious')."""
        return self.get_state().value

    def get_state_context_hint(self) -> str:
        """Short Vietnamese hint to append to system prompt before LLM call."""
        return _STATE_CONTEXT[self.get_state()]
