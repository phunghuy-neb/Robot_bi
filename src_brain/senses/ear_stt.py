"""
ear_stt.py — Robot Bi: Speech-to-Text (Offline)
================================================
Dùng faster-whisper (Whisper small, int8) để nhận dạng giọng nói tiếng Việt
hoàn toàn offline, không cần internet.

Interface công khai:
    class EarSTT:
        listen() -> str   # Trả về text đã nhận dạng, hoặc "" nếu không nghe được
"""

import os
_hf_cache_dir = os.path.abspath("src_brain/senses/.hf_cache")
os.makedirs(_hf_cache_dir, exist_ok=True)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_CACHE"] = _hf_cache_dir
os.environ["HF_HOME"] = _hf_cache_dir
os.environ["HUGGINGFACE_HUB_CACHE"] = _hf_cache_dir
os.environ["SENTENCE_TRANSFORMERS_HOME"] = _hf_cache_dir
import logging
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Optional

# Fix encoding cho console Windows (cp1252 không hỗ trợ tiếng Việt)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import io
import math
import struct as _struct
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)

# ── Cấu hình ─────────────────────────────────────────────────────────────────
WHISPER_MODEL    = "large-v2"  # Độ chính xác cao nhất cho tiếng Việt (~1.5GB)
SAMPLE_RATE      = 16000      # Whisper yêu cầu 16kHz
CHANNELS         = 1          # Mono
DTYPE            = "float32"
CHUNK_MS         = 50         # Đọc mic mỗi 50ms
SPEECH_THRESH    = 0.015      # RMS để phát hiện có tiếng nói
SILENCE_THRESH   = 0.008      # RMS để phát hiện im lặng
SILENCE_LIMIT_MS = 1500       # Im lặng 1.5s → coi là kết thúc câu
MAX_SECONDS      = 20         # Timeout tối đa
PRE_BUFFER_MS    = 300        # Giữ 300ms âm thanh trước khi bắt đầu ghi

# Tính toán số chunk
_CHUNK_FRAMES   = int(SAMPLE_RATE * CHUNK_MS / 1000)       # 800 frames
_PRE_BUF_CHUNKS = int(PRE_BUFFER_MS / CHUNK_MS)            # 6 chunks
_SILENCE_CHUNKS = int(SILENCE_LIMIT_MS / CHUNK_MS)         # 30 chunks
_MAX_CHUNKS     = int(MAX_SECONDS * 1000 / CHUNK_MS)       # 400 chunks

_TEMP_DIR = Path(tempfile.gettempdir())

MIC_DEVICE = 1  # Microphone Array (Realtek) — Windows device index


# ── Audio feedback beep (100ms 880Hz 44100Hz mono 16-bit PCM WAV) ─────────────
def _make_beep_wav() -> bytes:
    sr, n = 44100, 4410
    pcm = _struct.pack(f'<{n}h', *(int(0.3 * math.sin(2 * math.pi * 880 * i / sr) * 32767) for i in range(n)))
    buf = io.BytesIO()
    buf.write(b'RIFF'); buf.write(_struct.pack('<I', 36 + len(pcm))); buf.write(b'WAVE')
    buf.write(b'fmt '); buf.write(_struct.pack('<I', 16)); buf.write(_struct.pack('<HHIIHH', 1, 1, sr, sr * 2, 2, 16))
    buf.write(b'data'); buf.write(_struct.pack('<I', len(pcm))); buf.write(pcm)
    return buf.getvalue()

BEEP_WAV_BYTES: bytes = _make_beep_wav()

# ── Wake-word configuration ───────────────────────────────────────────────────
# STUB: Set True khi có openWakeWord model "bi_oi" (SRS 3.1).
# Khi False (hiện tại), main_loop.py bỏ qua wake-word và gọi listen() trực tiếp.
WAKEWORD_ENABLED = False
WAKEWORD_THRESHOLD = float(os.getenv("WAKEWORD_THRESHOLD", "0.5"))
WAKEWORD_PHRASE  = "bi ơi"  # Phrase cần phát hiện

# ── Singleton WhisperModel (lazy load) ───────────────────────────────────────
_whisper_instance = None
_wakeword_model = None
_wakeword_import_warning_logged = False


def _get_whisper_model():
    """Load WhisperModel lần đầu, tái dùng các lần sau."""
    global _whisper_instance
    if _whisper_instance is None:
        from faster_whisper import WhisperModel
        logger.info("[Bi - Tai] Đang tải Whisper model '%s'... (lần đầu, có thể mất 30-60s)", WHISPER_MODEL)
        try:
            _whisper_instance = WhisperModel(
                WHISPER_MODEL,
                device="cuda",
                compute_type="float16",
            )
            logger.info("[Bi - Tai] Whisper large-v2 chạy trên GPU (CUDA float16)")
        except Exception:
            _whisper_instance = WhisperModel(
                os.getenv("WHISPER_CPU_MODEL", "medium"),
                device="cpu",
                compute_type="int8",
            )
            logger.info(
                "[Bi - Tai] CPU mode: dung Whisper %s (thay vi large-v2) de giam do tre",
                os.getenv("WHISPER_CPU_MODEL", "medium"),
            )
            logger.info("[Bi - Tai] Whisper chạy trên CPU (laptop mode)")
    return _whisper_instance


def _normalize_input_channels(device_info) -> int:
    """Trả về số input channels hợp lệ của thiết bị."""
    try:
        channels = int(device_info.get("max_input_channels", 0))
    except (TypeError, ValueError, AttributeError):
        return 0
    return max(0, channels)


# ═════════════════════════════════════════════════════════════════════════════
class EarSTT:
    """Tai nghe của Robot Bi — nhận dạng giọng nói offline bằng faster-whisper."""

    def __init__(self):
        self.mic_device = MIC_DEVICE
        self.mic_channels = CHANNELS
        self.mic_name = "Silent mode"
        self.silent_mode = False
        self._mic_error_logged = False
        self._probe_microphone()

        # Trigger lazy load ngay khi khởi tạo để không bị lag lần đầu nghe
        try:
            _get_whisper_model()
        except Exception as e:
            logger.warning("[Bi - Tai] Cảnh báo: không load được Whisper model: %s", e)

    def _probe_microphone(self) -> None:
        """Tìm cấu hình microphone có thể mở được mà không làm crash pipeline."""
        logger.info("[Bi - Tai] Đang tìm microphone...")

        try:
            devices = sd.query_devices()
        except Exception as e:
            self._enable_silent_mode(f"không thể liệt kê thiết bị âm thanh: {e}")
            return

        preferred_indexes = []
        if 0 <= MIC_DEVICE < len(devices):
            preferred_indexes.append(MIC_DEVICE)
        preferred_indexes.extend(
            index for index, info in enumerate(devices)
            if _normalize_input_channels(info) > 0 and index not in preferred_indexes
        )

        for index in preferred_indexes:
            device_info = devices[index]
            max_input_channels = _normalize_input_channels(device_info)
            if max_input_channels <= 0:
                continue

            for channels in (1, 2):
                if channels > max_input_channels:
                    continue
                try:
                    stream = sd.InputStream(
                        samplerate=SAMPLE_RATE,
                        channels=channels,
                        dtype=DTYPE,
                        blocksize=_CHUNK_FRAMES,
                        device=index,
                    )
                    stream.close()
                    self.mic_device = index
                    self.mic_channels = channels
                    self.mic_name = str(device_info.get("name", f"Device {index}"))
                    self.silent_mode = False
                    logger.info("[Bi - Tai] Sử dụng microphone index %d: %s", index, self.mic_name)
                    return
                except Exception:
                    continue

        self._enable_silent_mode()

    def _enable_silent_mode(self, reason: Optional[str] = None) -> None:
        """Fallback an toàn khi không có microphone nào dùng được."""
        self.silent_mode = True
        self.mic_name = "Silent mode"
        if reason and not self._mic_error_logged:
            logger.warning("[Bi - Tai] Cảnh báo: %s", reason)
            self._mic_error_logged = True
        logger.warning("[Bi - Tai] Không tìm thấy microphone hợp lệ, chuyển sang chế độ im lặng")

    def _create_input_stream(self, blocksize: int):
        """Tạo InputStream theo microphone đã probe; nếu fail thì chuyển silent mode."""
        if self.silent_mode:
            return None

        try:
            return sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=self.mic_channels,
                dtype=DTYPE,
                blocksize=blocksize,
                device=self.mic_device,
            )
        except Exception as e:
            if not self._mic_error_logged:
                logger.warning("[Bi - Tai] Cảnh báo: không mở được microphone đã chọn: %s", e)
                self._mic_error_logged = True
            self._enable_silent_mode()
            return None

    def _play_beep(self) -> None:
        """Play 100ms 880Hz beep on Channel(6) when speech threshold is crossed."""
        try:
            import pygame
            ch = pygame.mixer.Channel(6)
            sound = pygame.mixer.Sound(io.BytesIO(BEEP_WAV_BYTES))
            ch.set_volume(0.4)
            ch.play(sound)
        except Exception:
            pass

    def listen(self) -> str:
        """
        Ghi âm từ microphone và nhận dạng giọng nói tiếng Việt.

        Luồng hoạt động:
          1. Mở sounddevice InputStream (16kHz, mono, float32)
          2. Duy trì pre-buffer 300ms bằng deque
          3. Khi RMS > SPEECH_THRESH → bắt đầu ghi audio vào buffer chính
          4. Khi RMS < SILENCE_THRESH liên tục 1.5s → dừng ghi
          5. Timeout sau MAX_SECONDS giây
          6. Lưu buffer ra file WAV tạm → Whisper transcribe → xóa file
          7. Trả về text, hoặc "" nếu không nhận dạng được

        Returns:
            str: Văn bản nhận dạng được (lowercase), hoặc "" nếu thất bại.
        """
        model = _get_whisper_model()
        if model is None:
            return ""
        if self.silent_mode:
            return ""

        logger.debug("[Bi - Tai] Đang lắng nghe... (tối đa %ds)", MAX_SECONDS)

        pre_buffer: deque = deque(maxlen=_PRE_BUF_CHUNKS)
        audio_buffer = []
        silent_chunks = 0
        speech_started = False
        tmp_wav: Optional[Path] = None

        try:
            stream = self._create_input_stream(_CHUNK_FRAMES)
            if stream is None:
                return ""
            stream.start()

            try:
                for _ in range(_MAX_CHUNKS):
                    chunk, overflowed = stream.read(_CHUNK_FRAMES)
                    rms = float(np.sqrt(np.mean(chunk ** 2)))

                    if not speech_started:
                        pre_buffer.append(chunk.copy())
                        if rms >= SPEECH_THRESH:
                            speech_started = True
                            self._play_beep()
                            audio_buffer.extend(list(pre_buffer))
                            logger.debug("[Bi - Tai] Phát hiện tiếng nói, đang ghi...")
                        continue

                    audio_buffer.append(chunk.copy())

                    if rms < SILENCE_THRESH:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks >= _SILENCE_CHUNKS:
                        break  # Im lặng 1.5s → kết thúc câu
            finally:
                stream.stop()
                stream.close()

            if not audio_buffer:
                return ""

            audio_array = np.concatenate(audio_buffer).flatten()
            if float(np.sqrt(np.mean(audio_array ** 2))) < 0.001:
                return ""

            # ── Ghi WAV tạm và transcribe ────────────────────────────────────
            tmp_fd, tmp_str = tempfile.mkstemp(suffix=".wav", dir=_TEMP_DIR)
            os.close(tmp_fd)
            tmp_wav = Path(tmp_str)
            sf.write(str(tmp_wav), audio_array, SAMPLE_RATE, subtype="PCM_16")

            segments, _ = model.transcribe(
                str(tmp_wav),
                language="vi",
                beam_size=5,                   # Tăng từ 1 lên 5 — chính xác hơn
                initial_prompt="Bi là robot. Xin chào Bi. Hôm nay trời đẹp.",  # Giúp Whisper nhận đúng tên Bi
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()

            if text:
                logger.info('[Bi - Tai] Nhận dạng: "%s"', text)
                return text.lower()
            return ""

        except sd.PortAudioError as e:
            logger.warning("[Bi - Tai] Cảnh báo: Lỗi microphone (PortAudio): %s", e)
            return ""
        except Exception as e:
            logger.warning("[Bi - Tai] Cảnh báo: Lỗi không mong đợi: %s: %s", type(e).__name__, e)
            return ""
        finally:
            if tmp_wav and tmp_wav.exists():
                try:
                    tmp_wav.unlink()
                except OSError:
                    pass



# ── Test độc lập ─────────────────────────────────────────────────────────────
def _listen_for_wakeword_impl(self, timeout: float = 30.0) -> bool:
        """
        Listen for the wake-word within the timeout window.

        For development/testing, openWakeWord is initialized with `wakeword_models=[]`
        so it uses the built-in "hey_jarvis" model as a proxy until a custom
        "bi_oi" model is available.
        """
        global WAKEWORD_ENABLED, _wakeword_model, _wakeword_import_warning_logged

        if not WAKEWORD_ENABLED:
            return False

        try:
            from openwakeword.model import Model
        except Exception as e:
            if not _wakeword_import_warning_logged:
                logger.warning("[Bi - Tai] Warning wake-word: openwakeword import failed: %s", e)
                _wakeword_import_warning_logged = True
            WAKEWORD_ENABLED = False
            return False

        if self.silent_mode:
            return False

        if _wakeword_model is None:
            _wakeword_model = Model(wakeword_models=[])

        chunk_frames = int(SAMPLE_RATE * 0.08)
        deadline = time.monotonic() + max(0.0, timeout)

        logger.debug('[Bi - Tai] Chờ wake-word "%s"... (timeout=%gs)', WAKEWORD_PHRASE, timeout)

        try:
            stream = self._create_input_stream(chunk_frames)
            if stream is None:
                return False
            stream.start()
            try:
                while time.monotonic() < deadline:
                    try:
                        from src_brain.network.api_server import is_mom_talking
                    except Exception:
                        is_mom_talking = None

                    if is_mom_talking is not None and is_mom_talking():
                        pause_started = time.monotonic()
                        while is_mom_talking():
                            time.sleep(0.05)
                        deadline += time.monotonic() - pause_started
                        continue

                    chunk, _ = stream.read(chunk_frames)
                    scores = _wakeword_model.predict(np.asarray(chunk, dtype=np.float32).flatten())
                    if any(float(score) > WAKEWORD_THRESHOLD for score in scores.values()):
                        self._play_beep()
                        return True
            finally:
                stream.stop()
                stream.close()
        except Exception as e:
            logger.warning("[Bi - Tai] Cảnh báo wake-word: %s", e)
            return False

        return False

EarSTT.listen_for_wakeword = _listen_for_wakeword_impl

if __name__ == "__main__":
    ear = EarSTT()
    print("Nói gì đó để test (Ctrl+C để thoát)...")
    while True:
        result = ear.listen()
        if result:
            print(f"[Kết quả] '{result}'")
