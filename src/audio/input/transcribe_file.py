"""
transcribe_file.py — Robot Bi: STT cho FILE âm thanh (không dùng micro)
======================================================================
Dùng cho luồng web (vd nộp bài TOEIC Speaking): nhận 1 file audio đã ghi và
trả về transcript. KHÁC `ear_stt.py` (chuyên capture micro trực tiếp) —
module này KHÔNG import sounddevice nên nhẹ và an toàn để dùng trong API server.

Giữ đúng Protected Fix: tự dò GPU (CUDA float16) → fallback CPU
(`WHISPER_CPU_MODEL`, mặc định `medium`, int8). Model load lazy + tái dùng.
"""

import logging
import os

logger = logging.getLogger(__name__)

WHISPER_MODEL = "large-v2"  # khớp ear_stt: độ chính xác cao nhất cho GPU
_model = None


def _get_model():
    """Load WhisperModel 1 lần, tái dùng. GPU trước, fallback CPU."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        try:
            _model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="float16")
            logger.info("[STT-File] Whisper large-v2 trên GPU (CUDA float16)")
        except Exception:
            cpu_model = os.getenv("WHISPER_CPU_MODEL", "medium")
            _model = WhisperModel(cpu_model, device="cpu", compute_type="int8")
            logger.info("[STT-File] CPU mode: Whisper %s (int8)", cpu_model)
    return _model


def transcribe_file(path: str, language: str | None = None) -> str:
    """Transcribe file audio → text. language=None để Whisper tự dò.
    Không bao giờ raise ra ngoài — lỗi → chuỗi rỗng."""
    try:
        model = _get_model()
        segments, _info = model.transcribe(path, language=language, beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:  # model/file/format lỗi không được phá endpoint
        logger.warning("[STT-File] transcribe lỗi: %s", e)
        return ""
