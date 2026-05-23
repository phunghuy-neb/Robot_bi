"""
Micro Moments Engine — Bi's spontaneous idle behaviors.

Fires short TTS phrases when Bi is idle, rate-limited to 1 per 15 minutes.
Guardrails: no moments during homework sessions or sleep hours (22:00–07:00).
Runtime-only: no DB, no threads. Caller drives timing via maybe_trigger().
"""
import time
import random
import logging
import datetime
from enum import Enum

from src.living.living_state import BiState

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECS = 15 * 60  # 15 minutes between micro moments


class MomentId(Enum):
    YAWN             = "yawn"
    MUMBLE           = "mumble"
    HUM              = "hum"
    LOOK_AROUND      = "look_around"
    SELF_TALK        = "self_talk"
    SHARE_FACT       = "share_fact"
    TIME_REACTION    = "time_reaction"
    PREPARE_SURPRISE = "prepare_surprise"


# States that allow each micro moment to fire
_MOMENT_STATES: dict[MomentId, set[BiState]] = {
    MomentId.YAWN:             {BiState.IDLE_SLEEPY},
    MomentId.MUMBLE:           {BiState.IDLE_CURIOUS, BiState.IDLE_SLEEPY},
    MomentId.HUM:              {BiState.ACTIVE_HAPPY, BiState.IDLE_CURIOUS},
    MomentId.LOOK_AROUND:      {BiState.IDLE_CURIOUS, BiState.MISSING_KID},
    MomentId.SELF_TALK:        {BiState.ACTIVE_HAPPY, BiState.IDLE_CURIOUS},
    MomentId.SHARE_FACT:       {BiState.IDLE_CURIOUS, BiState.MISSING_KID},
    MomentId.TIME_REACTION:    {BiState.IDLE_CURIOUS, BiState.IDLE_SLEEPY,
                                 BiState.ACTIVE_HAPPY, BiState.MISSING_KID},
    MomentId.PREPARE_SURPRISE: {BiState.IDLE_CURIOUS, BiState.ACTIVE_HAPPY},
}

# TTS texts keyed by moment value (TIME_REACTION uses time_<period> sub-keys)
_TEXTS: dict[str, list[str]] = {
    "yawn":             ["Bi ngáp một cái... ngủ quá!", "Aaah... hơi buồn ngủ mà!"],
    "mumble":           ["Hmm... hmm... hmm...", "Này, này... à..."],
    "hum":              ["La la la~", "Hm hm hm~"],
    "look_around":      ["Ủa... xung quanh có gì không nhỉ?", "Nhìn qua nhìn lại..."],
    "self_talk":        ["Hôm nay thật là một ngày hay nhỉ!", "Bi đang nghĩ... nghĩ... nghĩ~"],
    "share_fact":       [
        "Ê bạn ơi, cá ngủ mà không nhắm mắt đó!",
        "Bạn biết không, bạch tuộc có 3 trái tim!",
        "Con ong bay hơn 800 km mới làm được 1 lọ mật!",
    ],
    "time_morning":     ["Buổi sáng vui vẻ nha!", "Chào buổi sáng~"],
    "time_afternoon":   ["Buổi chiều nắng đẹp nhỉ!", "Chiều rồi, nghỉ ngơi chút nha~"],
    "time_evening":     ["Tối rồi, bé ơi~", "Ăn tối chưa bạn ơi?"],
    "time_night":       ["Muộn rồi đó, ngủ ngon nhé~", "Khuya rồi..."],
    "prepare_surprise": ["Bi đang nghĩ một câu đố vui cho bé...", "Để Bi nghĩ câu đố hay nào~"],
}


def _hour_to_period(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _is_sleep_hours(hour: int) -> bool:
    return hour >= 22 or hour < 7


def _pick_text(moment: MomentId, hour: int) -> str:
    key = moment.value
    if moment == MomentId.TIME_REACTION:
        key = f"time_{_hour_to_period(hour)}"
    options = _TEXTS.get(key, [])
    return random.choice(options) if options else ""


class MicroMomentsEngine:
    """
    Runtime-only micro behavior engine for Bi's spontaneous idle phrases.
    Caller polls maybe_trigger(); engine owns rate-limit and selection logic.
    No threads, no DB — completely stateless except for _last_fired_at.
    """

    def __init__(self, rate_limit_secs: int = _RATE_LIMIT_SECS):
        self._rate_limit_secs = rate_limit_secs
        self._last_fired_at: float = 0.0

    def maybe_trigger(
        self,
        state: BiState,
        *,
        is_homework: bool = False,
        hour: int | None = None,
    ) -> tuple[MomentId, str] | None:
        """
        Return (MomentId, tts_text) if a micro moment should fire now, else None.
        Caller is responsible for TTS playback. Updates _last_fired_at on hit.

        Args:
            state:       current BiState from LivingStateEngine.get_state()
            is_homework: True when child is in a homework/study session
            hour:        0–23 hour for sleep guardrail; defaults to current hour
        """
        if is_homework:
            return None
        if hour is None:
            hour = datetime.datetime.now().hour
        if not 0 <= hour <= 23:
            raise ValueError(f"hour must be 0–23, got {hour!r}")
        if _is_sleep_hours(hour):
            return None
        if time.time() - self._last_fired_at < self._rate_limit_secs:
            return None

        candidates = [m for m, states in _MOMENT_STATES.items() if state in states]
        if not candidates:
            return None

        moment = random.choice(candidates)
        text = _pick_text(moment, hour)
        if not text:
            return None

        self._last_fired_at = time.time()
        logger.debug("[MicroMoment] fired=%s state=%s", moment.value, state.value)
        return (moment, text)

    def seconds_until_next(self) -> float:
        """Remaining cooldown seconds (0.0 if ready to fire)."""
        return max(0.0, self._rate_limit_secs - (time.time() - self._last_fired_at))
