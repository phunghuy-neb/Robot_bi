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
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Optional

# Fix encoding cho console Windows (cp1252 không hỗ trợ tiếng Việt)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import numpy as np
import sounddevice as sd
import soundfile as sf

# ── Cấu hình ─────────────────────────────────────────────────────────────────
WHISPER_MODEL    = "small"    # Cân bằng tốc độ/accuracy cho tiếng Việt (~244MB)
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

# ── Singleton WhisperModel (lazy load) ───────────────────────────────────────
_whisper_instance = None


def _get_whisper_model():
    """Load WhisperModel lần đầu, tái dùng các lần sau."""
    global _whisper_instance
    if _whisper_instance is None:
        from faster_whisper import WhisperModel
        print(f"[Bi - Tai] Đang tải Whisper model '{WHISPER_MODEL}'... (lần đầu, có thể mất 10-30s)")
        _whisper_instance = WhisperModel(
            WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )
        print("[Bi - Tai] Whisper model sẵn sàng.")
    return _whisper_instance


# ═════════════════════════════════════════════════════════════════════════════
class EarSTT:
    """Tai nghe của Robot Bi — nhận dạng giọng nói offline bằng faster-whisper."""

    def __init__(self):
        # Trigger lazy load ngay khi khởi tạo để không bị lag lần đầu nghe
        try:
            _get_whisper_model()
        except Exception as e:
            print(f"[Bi - Tai] Cảnh báo: không load được Whisper model: {e}")

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

        print(f"[Bi - Tai] Đang lắng nghe... (tối đa {MAX_SECONDS}s)")

        pre_buffer: deque = deque(maxlen=_PRE_BUF_CHUNKS)
        audio_buffer = []
        silent_chunks = 0
        speech_started = False
        tmp_wav: Optional[Path] = None

        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=_CHUNK_FRAMES,
            )
            stream.start()

            try:
                for _ in range(_MAX_CHUNKS):
                    chunk, overflowed = stream.read(_CHUNK_FRAMES)
                    rms = float(np.sqrt(np.mean(chunk ** 2)))

                    if not speech_started:
                        pre_buffer.append(chunk.copy())
                        if rms >= SPEECH_THRESH:
                            speech_started = True
                            audio_buffer.extend(list(pre_buffer))
                            print("[Bi - Tai] Phát hiện tiếng nói, đang ghi...")
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
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()

            if text:
                print(f'[Bi - Tai] Nhận dạng: "{text}"')
                return text.lower()
            return ""

        except sd.PortAudioError as e:
            print(f"[Bi - Tai] Cảnh báo: Lỗi microphone (PortAudio): {e}")
            return ""
        except Exception as e:
            print(f"[Bi - Tai] Cảnh báo: Lỗi không mong đợi: {type(e).__name__}: {e}")
            return ""
        finally:
            if tmp_wav and tmp_wav.exists():
                try:
                    tmp_wav.unlink()
                except OSError:
                    pass


# ── Test độc lập ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ear = EarSTT()
    print("Nói gì đó để test (Ctrl+C để thoát)...")
    while True:
        result = ear.listen()
        if result:
            print(f"[Kết quả] '{result}'")
