"""
cry_detector.py — Robot Bi: Phát hiện tiếng khóc trẻ em (SRS 3.4)
==================================================================
Implementation hai tầng:
  - Tầng 1 (primary):  YAMNet TFLite int8 — audio classification offline
  - Tầng 2 (fallback): Energy + ZCR based detection — không cần model

Chạy trong daemon thread riêng, KHÔNG block audio pipeline của robot.

Kích hoạt callback khi:
  - YAMNet confidence "crying" > 0.5, HOẶC
  - Energy cao + ZCR pattern khớp tiếng khóc (fallback)
"""

import threading
import time
import logging
import numpy as np
from pathlib import Path

from src.audio.input.microphone_utils import (
    CallbackMicrophoneStream,
    probe_input_device,
    resample_audio,
)

logger = logging.getLogger("cry_detector")
_yamnet_fallback_notice_printed = False
_mic_unavailable_notice_printed = False

# ── Cấu hình ─────────────────────────────────────────────────────────────────
SAMPLE_RATE        = 16000    # YAMNet yêu cầu 16kHz
CHUNK_SECONDS      = 0.96     # YAMNet window size
CHUNK_FRAMES       = int(SAMPLE_RATE * CHUNK_SECONDS)
YAMNET_THRESHOLD   = 0.50     # Confidence tối thiểu để báo khóc
ENERGY_THRESHOLD   = 0.08     # RMS threshold cho fallback
ZCR_THRESHOLD      = 0.15     # Zero-crossing rate threshold cho fallback
COOLDOWN_SECONDS   = 10.0     # Không báo lại trong 10 giây sau mỗi alert

# ── YAMNet class IDs liên quan đến tiếng khóc ────────────────────────────────
# YAMNet có 521 classes — các class liên quan đến crying (approximate indices):
_CRY_CLASS_INDICES = [20, 21, 22, 23]  # baby cry, infant cry, sobbing, whimper


class CryDetector:
    """
    Phát hiện tiếng khóc trẻ em qua microphone.

    Usage:
        detector = CryDetector(on_cry_callback=my_func)
        detector.start()
        # ... robot hoạt động ...
        detector.stop()
    """

    def __init__(
        self,
        on_cry_callback=None,
        mic_index: int = None,
        excluded_mic_indexes: set[int] | None = None,
    ):
        """
        Args:
            on_cry_callback: callable() — gọi khi phát hiện tiếng khóc
            mic_index: index microphone (None = mặc định)
            excluded_mic_indexes: microphone indexes reserved by STT/wake word
        """
        self.on_cry_callback = on_cry_callback
        self.mic_index = mic_index
        self.excluded_mic_indexes = set(excluded_mic_indexes or set())
        self.active_mic_index: int | None = None
        self.active_mic_name: str | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_alert_time: float = 0.0
        self._detections: int = 0

        # Load YAMNet model (lazy)
        self._interpreter = None
        self._yamnet_available = False
        self._try_load_yamnet()

    def _try_load_yamnet(self) -> None:
        """Thử load YAMNet TFLite model. Nếu fail → dùng fallback."""
        model_path = Path(__file__).parent / "models" / "yamnet.tflite"

        if not model_path.exists():
            logger.info(
                "[Bi - Tai khoc] YAMNet model khong tim thay tai %s — "
                "dung energy-based fallback. "
                "Download model: https://storage.googleapis.com/mediapipe-assets/yamnet.tflite",
                model_path,
            )
            self._yamnet_available = False
            return

        try:
            try:
                import tflite_runtime.interpreter as tflite
                self._interpreter = tflite.Interpreter(model_path=str(model_path))
            except ImportError:
                import tensorflow as tf
                self._interpreter = tf.lite.Interpreter(model_path=str(model_path))

            self._interpreter.allocate_tensors()
            self._yamnet_available = True
            logger.info("[Bi - Tai khoc] YAMNet TFLite model da san sang.")

        except Exception as e:
            self._log_yamnet_fallback_once()
            logger.debug("[Bi - Tai khoc] Khong load duoc YAMNet: %s", e)
            self._yamnet_available = False

    def _log_yamnet_fallback_once(self) -> None:
        global _yamnet_fallback_notice_printed
        if _yamnet_fallback_notice_printed:
            return
        logger.info("[CryDetector] YAMNet TFLite khong kha dung, dung energy fallback.")
        _yamnet_fallback_notice_printed = True

    def _handle_mic_unavailable_once(self, error: Exception) -> bool:
        """Log 1 lan khi khong co microphone hop le, roi dung detector."""
        global _mic_unavailable_notice_printed
        error_text = str(error)
        mic_error_markers = (
            "Error querying device",
            "Invalid device",
            "No input device",
            "Error opening InputStream",
            "PortAudioError",
        )
        if not any(marker in error_text for marker in mic_error_markers):
            return False
        if not _mic_unavailable_notice_printed:
            logger.info(
                "[Bi - Tai khoc] Khong tim thay microphone hop le (%s) - dung CryDetector.",
                error_text,
            )
            _mic_unavailable_notice_printed = True
        self._running = False
        return True

    def _yamnet_predict(self, audio: np.ndarray) -> float:
        """
        Chạy YAMNet inference, trả về max confidence của các cry classes.
        Returns: float 0.0–1.0
        """
        if not self._yamnet_available or self._interpreter is None:
            return 0.0

        try:
            input_details = self._interpreter.get_input_details()
            output_details = self._interpreter.get_output_details()

            # Normalize audio về [-1, 1]
            audio_norm = audio.astype(np.float32)
            max_val = np.max(np.abs(audio_norm))
            if max_val > 0:
                audio_norm = audio_norm / max_val

            self._interpreter.set_tensor(input_details[0]['index'], audio_norm)
            self._interpreter.invoke()

            scores = self._interpreter.get_tensor(output_details[0]['index'])
            # scores shape: (num_frames, 521)
            mean_scores = np.mean(scores, axis=0)

            cry_score = float(np.max(mean_scores[_CRY_CLASS_INDICES]))
            return cry_score

        except Exception as e:
            logger.debug("[Bi - Tai khoc] YAMNet inference loi: %s", e)
            return 0.0

    def _energy_based_detect(self, audio: np.ndarray) -> bool:
        """
        Fallback: Phát hiện tiếng khóc bằng energy + zero-crossing rate.
        Tiếng khóc có: energy cao + ZCR vừa phải + pattern biến đổi đều đặn.

        Returns: True nếu có khả năng tiếng khóc.
        """
        # RMS energy
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < ENERGY_THRESHOLD:
            return False

        # Zero-crossing rate
        zcr = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2)
        # Tiếng khóc: ZCR thường 0.05–0.25
        if not (0.05 <= zcr <= 0.30):
            return False

        # Kiểm tra pattern kéo dài (tiếng khóc liên tục, không bật/tắt đột ngột)
        # Chia audio thành 4 phần, kiểm tra energy khá đều nhau
        quarter = len(audio) // 4
        energies = [
            float(np.sqrt(np.mean(audio[i * quarter:(i + 1) * quarter] ** 2)))
            for i in range(4)
        ]
        mean_e = sum(energies) / len(energies)
        std_e = float(np.std(energies))
        energy_variance = std_e / (mean_e + 1e-8)
        if energy_variance > 0.8:  # Quá biến động → không phải tiếng khóc đều
            return False

        return True

    def _detection_loop(self) -> None:
        """Vòng lặp chính chạy trong daemon thread."""
        method = "YAMNet" if self._yamnet_available else "energy fallback"
        stream = None
        try:
            config = probe_input_device(
                preferred_index=self.mic_index,
                target_rate=SAMPLE_RATE,
                excluded_indexes=self.excluded_mic_indexes,
            )
            if config is None:
                self._handle_mic_unavailable_once(
                    RuntimeError("No input device available for CryDetector")
                )
                return

            self.active_mic_index = config.device_index
            self.active_mic_name = config.name
            stream = CallbackMicrophoneStream(
                config,
                chunk_ms=int(CHUNK_SECONDS * 1000),
            )
            stream.start()
            logger.info(
                "[Bi - Tai khoc] Bat dau lang nghe (%s, mic=%d, %d Hz)",
                method,
                config.device_index,
                config.sample_rate,
            )

            while self._running:
                audio = stream.read(timeout=2.0)
                audio = resample_audio(
                    audio,
                    config.sample_rate,
                    SAMPLE_RATE,
                )

                # Kiểm tra phát hiện
                is_crying = False
                if self._yamnet_available:
                    confidence = self._yamnet_predict(audio)
                    if confidence >= YAMNET_THRESHOLD:
                        is_crying = True
                        logger.info(
                            "[Bi - Tai khoc] YAMNet phat hien tieng khoc (confidence=%.2f)",
                            confidence,
                        )
                else:
                    is_crying = self._energy_based_detect(audio)
                    if is_crying:
                        logger.info("[Bi - Tai khoc] Energy-based phat hien tieng khoc")

                # Gọi callback nếu phát hiện, với cooldown
                now = time.time()
                if is_crying and (now - self._last_alert_time) >= COOLDOWN_SECONDS:
                    self._last_alert_time = now
                    self._detections += 1
                    logger.info(
                        "[Bi - Tai khoc] Phat hien tieng khoc! (lan %d)",
                        self._detections,
                    )
                    if self.on_cry_callback:
                        try:
                            threading.Thread(
                                target=self.on_cry_callback, daemon=True
                            ).start()
                        except Exception as e:
                            logger.error("[Bi - Tai khoc] callback loi: %s", e)

        except Exception as e:
            if not self._handle_mic_unavailable_once(e):
                logger.warning("[Bi - Tai khoc] Detection loop stopped: %s", e)
            self._running = False
        finally:
            if stream is not None:
                stream.stop()

    def start(self) -> None:
        """Bắt đầu detection trong daemon thread. Non-blocking."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._detection_loop, daemon=True, name="CryDetector"
        )
        self._thread.start()

    def stop(self) -> None:
        """Dừng daemon thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def get_stats(self) -> dict:
        return {
            "is_running": self.is_running(),
            "yamnet_available": self._yamnet_available,
            "total_detections": self._detections,
            "mic_index": self.active_mic_index,
            "mic_name": self.active_mic_name,
        }


# ── Test độc lập ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=== CryDetector standalone test ===")

    def on_cry():
        print(">>> CRY DETECTED! <<<")

    detector = CryDetector(on_cry_callback=on_cry)
    print(f"YAMNet available: {detector._yamnet_available}")
    print(f"Stats: {detector.get_stats()}")

    detector.start()
    print("Chay 5 giay... (thu noi/khoc to de test)")
    try:
        for i in range(5):
            time.sleep(1)
            print(f"[{i+1}s] stats: {detector.get_stats()}")
    except KeyboardInterrupt:
        pass
    detector.stop()
    print("Done:", detector.get_stats())
