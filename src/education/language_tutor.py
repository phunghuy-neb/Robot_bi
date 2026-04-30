"""Language tutor helpers for basic lessons, translation and pronunciation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LanguageTutor:
    """Gia su ngon ngu cuc bo, khong phu thuoc LLM."""

    SUPPORTED_LANGUAGES = {
        "en": {"name": "Tieng Anh", "voice": "en-US-JennyNeural"},
        "ja": {"name": "Tieng Nhat", "voice": "ja-JP-NanamiNeural"},
        "ko": {"name": "Tieng Han", "voice": "ko-KR-SunHiNeural"},
        "zh": {"name": "Tieng Trung", "voice": "zh-CN-XiaoxiaoNeural"},
        "fr": {"name": "Tieng Phap", "voice": "fr-FR-DeniseNeural"},
    }

    _VI_EN = {
        "xin chao": "hello",
        "tam biet": "goodbye",
        "cam on": "thank you",
        "con meo": "cat",
        "con cho": "dog",
        "mau do": "red",
        "so mot": "one",
    }

    _GUIDES = {
        "en": {
            "cat": {"phonetic": "/kæt/", "syllables": ["cat"], "tips": "Mo mieng ngan, am cuoi /t/ gon."},
            "dog": {"phonetic": "/dɔːɡ/", "syllables": ["dog"], "tips": "Keo dai am /ɔː/ nhe."},
            "hello": {"phonetic": "/həˈloʊ/", "syllables": ["he", "llo"], "tips": "Nhan am thu hai."},
        }
    }

    def get_lesson(self, language: str, level: str) -> dict:
        """Tra ve bai hoc mau theo language va level."""
        try:
            info = self.SUPPORTED_LANGUAGES.get(language, self.SUPPORTED_LANGUAGES["en"])
            return {
                "language": language if language in self.SUPPORTED_LANGUAGES else "en",
                "language_name": info["name"],
                "level": level,
                "voice": info["voice"],
                "items": [
                    {"word": "hello", "meaning": "xin chao"},
                    {"word": "thank you", "meaning": "cam on"},
                    {"word": "goodbye", "meaning": "tam biet"},
                ],
            }
        except Exception:
            logger.exception("[LanguageTutor] get_lesson failed")
            return {"language": "en", "level": level, "items": []}

    def check_grammar(self, text: str, language: str) -> dict:
        """Kiem tra grammar bang rule cuc nhe."""
        try:
            stripped = (text or "").strip()
            issues = []
            if language == "en" and stripped:
                if stripped[0].islower():
                    issues.append("Cau tieng Anh nen viet hoa chu cai dau.")
                if stripped[-1] not in ".!?":
                    issues.append("Cau nen ket thuc bang dau cau.")
            return {"ok": len(issues) == 0, "issues": issues}
        except Exception:
            logger.exception("[LanguageTutor] check_grammar failed")
            return {"ok": False, "issues": ["Khong the kiem tra grammar."]}

    def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        """Dich mot so cum co ban bang tu dien cuc bo."""
        try:
            key = " ".join((text or "").strip().lower().split())
            if from_lang == "vi" and to_lang == "en":
                return self._VI_EN.get(key, text)
            if from_lang == "en" and to_lang == "vi":
                reverse = {value: key for key, value in self._VI_EN.items()}
                return reverse.get(key, text)
            return text
        except Exception:
            logger.exception("[LanguageTutor] translate failed")
            return text

    def get_pronunciation_guide(self, word: str, language: str) -> dict:
        """Tra ve huong dan phat am cho word."""
        try:
            normalized = (word or "").strip().lower()
            guide = self._GUIDES.get(language, {}).get(normalized)
            if guide is None:
                guide = {"phonetic": "", "syllables": [normalized] if normalized else [], "tips": "Nghe mau va lap lai cham."}
            return {"word": word, "language": language, **guide}
        except Exception:
            logger.exception("[LanguageTutor] get_pronunciation_guide failed")
            return {"word": word, "language": language, "phonetic": "", "syllables": [], "tips": ""}
