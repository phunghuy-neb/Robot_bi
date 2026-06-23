"""
Proactive Behaviors Engine - gentle child-present idle prompts.

Runtime-only: no DB, no threads. Voice interaction marks recent presence;
camera events may extend it when optional camera hardware is enabled.
Guardrails: rate-limited, blocked during homework and sleep hours (22:00-07:00).
"""
import datetime
import logging
import random
import time

from src.living.living_state import BiState

logger = logging.getLogger(__name__)

_SILENCE_TRIGGER_SECS = 10 * 60
_RATE_LIMIT_SECS = 30 * 60
_PRESENCE_WINDOW_SECS = 12 * 60

_TEXTS: tuple[str, ...] = (
    "Bé ơi, hôm nay có chuyện gì hay không?",
    "Bi thấy bé đang yên lặng. Mình nói chuyện một chút không?",
    "Bé muốn chơi nhẹ một trò, hay nghỉ tiếp cũng được nha.",
)


def _is_sleep_hours(hour: int) -> bool:
    return hour >= 22 or hour < 7


class ProactiveBehaviorsEngine:
    """
    Runtime-only proactive prompt gate.

    The engine tracks the last user interaction and last proactive prompt.
    A recognized interaction marks recent presence and resets silence.
    Optional camera/vision signals may extend presence without resetting silence.
    """

    def __init__(
        self,
        silence_secs: int = _SILENCE_TRIGGER_SECS,
        rate_limit_secs: int = _RATE_LIMIT_SECS,
        presence_secs: int = _PRESENCE_WINDOW_SECS,
    ):
        self._silence_secs = silence_secs
        self._rate_limit_secs = rate_limit_secs
        self._presence_secs = presence_secs
        now = time.time()
        self._last_interaction_at: float = now
        self._last_fired_at: float = float("-inf")
        self._present_until: float = 0.0

    def on_interaction(self, *, now: float | None = None) -> None:
        """Record an interaction, reset silence, and mark recent presence."""
        current = time.time() if now is None else now
        self._last_interaction_at = current
        self.on_presence(now=current)

    def on_presence(self, *, now: float | None = None) -> None:
        """Extend the recent-presence window without resetting silence."""
        current = time.time() if now is None else now
        self._present_until = max(
            self._present_until,
            current + self._presence_secs,
        )

    def is_recently_present(self, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        return current <= self._present_until

    def maybe_trigger(
        self,
        state: BiState,
        *,
        is_homework: bool = False,
        hour: int | None = None,
        now: float | None = None,
    ) -> str | None:
        """Return a proactive phrase if all guardrails pass, else None."""
        current = time.time() if now is None else now
        if not self.is_recently_present(now=current):
            return None
        if is_homework:
            return None
        if state in (BiState.ACTIVE_ENGAGED, BiState.THINKING):
            return None
        if hour is None:
            hour = datetime.datetime.now().hour
        if not 0 <= hour <= 23:
            raise ValueError(f"hour must be 0-23, got {hour!r}")
        if _is_sleep_hours(hour):
            return None
        if current - self._last_interaction_at < self._silence_secs:
            return None
        if current - self._last_fired_at < self._rate_limit_secs:
            return None

        self._last_fired_at = current
        phrase = random.choice(_TEXTS)
        logger.debug("[Proactive] fired state=%s", state.value)
        return phrase

    def seconds_until_silence_trigger(self, *, now: float | None = None) -> float:
        """Remaining seconds before no-voice threshold is reached."""
        current = time.time() if now is None else now
        return max(0.0, self._silence_secs - (current - self._last_interaction_at))

    def seconds_until_next(self, *, now: float | None = None) -> float:
        """Remaining proactive cooldown seconds (0.0 if ready)."""
        current = time.time() if now is None else now
        return max(0.0, self._rate_limit_secs - (current - self._last_fired_at))

    def seconds_until_presence_expires(self, *, now: float | None = None) -> float:
        current = time.time() if now is None else now
        return max(0.0, self._present_until - current)
