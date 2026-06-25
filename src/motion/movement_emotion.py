"""
movement_emotion.py — Stage 1.5: Body Expression wire layer.

Maps BiState → motor movements and MomentId → gestures.
Non-blocking: all movements run in daemon threads.
Guards: sleep hours, rate-limit, motor simulation safe.
"""

import datetime
import logging
import threading
import time

from src.living.living_state import BiState
from src.living.micro_moments import MomentId
from src.motion.motor_controller import get_shared_motor

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECS = 5.0      # min seconds between movements
_SLEEP_START = 22
_SLEEP_END = 7


def _is_sleep_hours() -> bool:
    h = datetime.datetime.now().hour
    return h >= _SLEEP_START or h < _SLEEP_END


class MovementEmotionEngine:
    """
    Wire layer between living state / micro moments and MotorController.

    All movements fire in daemon threads so they never block the main loop.
    Simulation mode is transparent — the MotorController already logs commands.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_moved_at: float = 0.0
        self._moving: bool = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def on_state_change(self, state: BiState) -> None:
        """Call when LivingStateEngine transitions to a new state."""
        if not self._should_move():
            return
        move = _STATE_MOVES.get(state)
        if move:
            self._fire(move, label=f"state:{state.value}")

    def on_moment(self, moment: MomentId) -> None:
        """Call when MicroMomentsEngine fires a moment."""
        if not self._should_move():
            return
        move = _MOMENT_MOVES.get(moment)
        if move:
            self._fire(move, label=f"moment:{moment.value}")

    def on_pouting(self) -> None:
        """Call when Bi announces the pouting phrase — look away dramatically."""
        if not self._should_move():
            return
        self._fire(_pouting_move, label="pouting")

    def on_welcome_back(self) -> None:
        """Call when Bi greets the kid returning after long absence."""
        if not self._should_move():
            return
        self._fire(_welcome_back_move, label="welcome_back")

    # ── Internal ───────────────────────────────────────────────────────────────

    def _should_move(self) -> bool:
        if _is_sleep_hours():
            return False
        with self._lock:
            if self._moving:
                return False
            if time.time() - self._last_moved_at < _RATE_LIMIT_SECS:
                return False
        return True

    def _fire(self, move_fn, *, label: str) -> None:
        with self._lock:
            self._last_moved_at = time.time()
            self._moving = True

        def _run():
            try:
                motor = get_shared_motor()
                move_fn(motor)
                logger.debug("[BodyExpr] %s done", label)
            except Exception as e:
                logger.warning("[BodyExpr] %s failed: %s", label, e)
            finally:
                with self._lock:
                    self._moving = False

        t = threading.Thread(target=_run, daemon=True, name=f"body-{label}")
        t.start()


# ── Movement definitions ───────────────────────────────────────────────────────
# Each is a function(motor) that executes a short gesture sequence.
# All durations are short (≤2s total) to not disrupt conversation flow.

def _happy_wiggle(motor):
    """Quick left-right wiggle to express happiness."""
    motor.turn_left(20)
    time.sleep(0.3)
    motor.turn_right(40)
    time.sleep(0.3)
    motor.turn_left(20)
    time.sleep(0.2)
    motor.stop()


def _attentive_center(motor):
    """Face forward — attentive listening posture."""
    motor.stop()


def _thinking_sway(motor):
    """Gentle slow left-right sway while thinking."""
    motor.turn_left(10)
    time.sleep(0.5)
    motor.turn_right(20)
    time.sleep(0.5)
    motor.turn_left(10)
    time.sleep(0.3)
    motor.stop()


def _curious_look(motor):
    """Tilt head to one side — curious pose."""
    motor.turn_left(25)
    time.sleep(0.4)
    motor.stop()


def _sleepy_droop(motor):
    """Slow forward bob simulating drowsiness."""
    motor.forward(20, 300)
    time.sleep(0.4)
    motor.backward(20, 300)
    time.sleep(0.4)
    motor.stop()


def _pouting_move(motor):
    """Turn away — giận dỗi 'looking the other way'."""
    motor.turn_right(70)
    time.sleep(0.6)
    motor.stop()


def _missing_kid_scan(motor):
    """Slow scan left then right — looking for the kid."""
    motor.turn_left(45)
    time.sleep(0.8)
    motor.turn_right(90)
    time.sleep(0.8)
    motor.turn_left(45)
    time.sleep(0.5)
    motor.stop()


def _welcome_back_move(motor):
    """Spin with excitement when kid returns."""
    motor.spin(40, 600)
    time.sleep(0.7)
    motor.stop()


def _look_around_scan(motor):
    """LOOK_AROUND moment — wide scan left then right."""
    motor.turn_left(45)
    time.sleep(0.7)
    motor.turn_right(90)
    time.sleep(0.7)
    motor.turn_left(45)
    time.sleep(0.5)
    motor.stop()


def _yawn_move(motor):
    """Slow forward droop + pause — yawning."""
    motor.forward(15, 400)
    time.sleep(0.6)
    motor.backward(15, 400)
    time.sleep(0.5)
    motor.stop()


def _hum_sway(motor):
    """Gentle sway left-right for humming."""
    motor.turn_left(15)
    time.sleep(0.4)
    motor.turn_right(30)
    time.sleep(0.4)
    motor.turn_left(15)
    time.sleep(0.3)
    motor.stop()


def _surprise_prep(motor):
    """Small spin to signal 'I'm preparing something fun'."""
    motor.spin(30, 500)
    time.sleep(0.6)
    motor.stop()


def _share_fact_present(motor):
    """Face forward slightly tilted — presenting mode."""
    motor.turn_right(15)
    time.sleep(0.3)
    motor.turn_left(15)
    time.sleep(0.2)
    motor.stop()


# ── Mapping tables ─────────────────────────────────────────────────────────────

_STATE_MOVES = {
    BiState.ACTIVE_HAPPY:   _happy_wiggle,
    BiState.ACTIVE_ENGAGED: _attentive_center,
    BiState.THINKING:       _thinking_sway,
    BiState.IDLE_CURIOUS:   _curious_look,
    BiState.IDLE_SLEEPY:    _sleepy_droop,
    BiState.POUTING:        _pouting_move,
    BiState.MISSING_KID:    _missing_kid_scan,
}

_MOMENT_MOVES = {
    MomentId.LOOK_AROUND:      _look_around_scan,
    MomentId.YAWN:             _yawn_move,
    MomentId.HUM:              _hum_sway,
    MomentId.PREPARE_SURPRISE: _surprise_prep,
    MomentId.SHARE_FACT:       _share_fact_present,
    MomentId.SELF_TALK:        _hum_sway,
    MomentId.MUMBLE:           _curious_look,
    MomentId.TIME_REACTION:    _attentive_center,
}


# ── Shared singleton ───────────────────────────────────────────────────────────

_shared_engine: "MovementEmotionEngine | None" = None


def get_movement_engine() -> MovementEmotionEngine:
    global _shared_engine
    if _shared_engine is None:
        _shared_engine = MovementEmotionEngine()
    return _shared_engine
