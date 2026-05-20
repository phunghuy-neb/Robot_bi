"""
wakeword_router.py — Integration shim between WakeWordService and main.py.

Thin adapter that maps voice-loop lifecycle events to state machine transitions.
Keeps main.py clean — it only calls 4 methods:

    router.wait_for_wakeword(timeout)  → bool  block until "Bi ơi" or timeout
    router.on_stt_start()                       LISTENING → PROCESSING
    router.on_reply_done()                      PROCESSING → COOLDOWN → IDLE
    router.on_error()                           any state  → IDLE (emergency reset)

Integration in main.py run():

    # Guard at top of voice loop (before ear.listen()):
    if self._wakeword and self._wakeword.is_enabled():
        if not self._wakeword.wait_for_wakeword(timeout=30.0):
            continue
        self._wakeword.on_stt_start()

    user_text = self.ear.listen()
    ...

    # After audio_queue.join() (reply fully delivered):
    if self._wakeword and self._wakeword.is_enabled():
        self._wakeword.on_reply_done()

    # In except Exception block:
    if self._wakeword and self._wakeword.is_enabled():
        self._wakeword.on_error()
"""

import logging

from src.wakeword.wakeword_service import WakeWordService, WakeWordState

logger = logging.getLogger(__name__)


class WakeWordRouter:
    """
    Thin shim that translates main.py lifecycle events to WakeWordService calls.
    """

    def __init__(self, service: WakeWordService):
        self._service = service

    def start(self) -> None:
        """Start background audio listener (call once at app startup)."""
        self._service.start()

    def stop(self) -> None:
        """Stop audio listener (call on app shutdown)."""
        self._service.stop()

    def is_enabled(self) -> bool:
        """True when wake word gate is active (WAKEWORD_ENABLED=true)."""
        return self._service.is_enabled()

    def wait_for_wakeword(self, timeout: float = 30.0) -> bool:
        """
        Block until "Bi ơi" is detected or timeout.

        Returns True if wake word detected (state → LISTENING).
        Returns False on timeout — caller should continue the loop.
        """
        return self._service.wait_for_detection(timeout=timeout)

    def on_stt_start(self) -> None:
        """
        Call when STT is about to open the microphone.
        Transitions LISTENING → PROCESSING (blocks further detections).
        """
        self._service.set_state(WakeWordState.PROCESSING)

    def on_reply_done(self) -> None:
        """
        Call when TTS reply is fully delivered (audio_queue.join() done).
        Triggers COOLDOWN → auto-IDLE + restarts AudioListener.
        """
        self._service.enter_cooldown()

    def on_error(self) -> None:
        """
        Call on pipeline exception.
        Emergency-resets to IDLE and restarts AudioListener.
        """
        self._service.reset_to_idle()

    def get_state(self) -> WakeWordState:
        """Current state (useful for logging / debug)."""
        return self._service.get_state()
