"""
Proactive Behaviors Engine - gentle child-present idle prompts.

Runtime-only: no DB, no threads. Caller owns presence detection and TTS.
Guardrails: requires recent child presence, rate-limited, blocked during
homework sessions and sleep hours (22:00-07:00).
"""
import datetime
import logging
import random
import time

from src.living.living_state import BiState

logger = logging.getLogger(__name__)

_SILENCE_TRIGGER_SECS = 10 * 60
_RATE_LIMIT_SECS = 30 * 60

_TEXTS: tuple[str, ...] = (
    "Be oi, hom nay co chuyen gi hay khong?",
    "Bi thay be dang yen lang. Minh noi chuyen mot chut khong?",
    "Be muon choi nhe mot tro, hay nghi tiep cung duoc nha.",
)


def _is_sleep_hours(hour: int) -> bool:
    return hour >= 22 or hour < 7


class ProactiveBehaviorsEngine:
    """
    Runtime-only proactive prompt gate.

    The engine tracks the last user interaction and last proactive prompt.
    It never detects presence by itself; main.py passes child_present=True
    based on camera/vision signals.
    """

    def __init__(
        self,
        silence_secs: int = _SILENCE_TRIGGER_SECS,
        rate_limit_secs: int = _RATE_LIMIT_SECS,
    ):
        self._silence_secs = silence_secs
        self._rate_limit_secs = rate_limit_secs
        now = time.time()
        self._last_interaction_at: float = now
        self._last_fired_at: float = now - rate_limit_secs

    def on_interaction(self, *, now: float | None = None) -> None:
        """Record a child/user interaction and reset the silence timer."""
        self._last_interaction_at = time.time() if now is None else now

    def maybe_trigger(
        self,
        state: BiState,
        *,
        child_present: bool,
        is_homework: bool = False,
        hour: int | None = None,
        now: float | None = None,
    ) -> str | None:
        """Return a proactive phrase if all guardrails pass, else None."""
        current = time.time() if now is None else now
        if not child_present:
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
