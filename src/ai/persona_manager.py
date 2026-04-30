"""
PersonaManager - Quan ly ten, gioi tinh, giong noi va tinh cach robot Bi.

Tinh cach trong module nay duoc dung de bo sung system prompt cho LLM.
Du lieu duoc scope theo family_id va luu dang JSON trong SQLite.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any

from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)

DEFAULT_PERSONA = {
    "name": "Bi",
    "gender": "neutral",
    "voice": "vi-VN-HoaiMyNeural",
    "personality": {
        "playfulness": 70,
        "extraversion": 60,
        "energy": 65,
    },
    "language": "vi",
}

_VALID_GENDERS = {"male", "female", "neutral"}
_VALID_LANGUAGES = {"vi", "en", "ja", "ko", "zh", "fr", "de", "es"}
_PERSONALITY_KEYS = {"playfulness", "extraversion", "energy"}


class PersonaManager:
    """Quan ly persona cua robot Bi theo tung family."""

    def __init__(self, family_id: str | None = None):
        """Khoi tao manager va load persona tu DB neu da co."""
        self.family_id = family_id or os.getenv("FAMILY_ID", "default")
        self._persona = copy.deepcopy(DEFAULT_PERSONA)
        self._ensure_schema()
        self._load()

    def _ensure_schema(self) -> None:
        """Tao bang persona neu chua ton tai."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS persona (
                        family_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        updated_at TEXT DEFAULT (datetime('now'))
                    )
                    """
                )
                conn.commit()
        except Exception:
            logger.exception("[PersonaManager] Khong the tao schema persona")

    def _load(self) -> None:
        """Load persona tu DB theo family_id."""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT data FROM persona WHERE family_id = ?",
                    (self.family_id,),
                ).fetchone()
            if not row:
                return

            loaded = json.loads(row["data"])
            if isinstance(loaded, dict):
                merged = copy.deepcopy(DEFAULT_PERSONA)
                merged.update({k: v for k, v in loaded.items() if k != "personality"})
                merged["personality"].update(loaded.get("personality", {}))
                if self._validate(merged):
                    self._persona = merged
        except Exception:
            logger.exception("[PersonaManager] Khong the load persona")

    def _validate(self, persona: dict[str, Any]) -> bool:
        """Validate persona truoc khi luu hoac ap dung."""
        try:
            name = persona.get("name")
            voice = persona.get("voice")
            gender = persona.get("gender")
            language = persona.get("language")
            personality = persona.get("personality")

            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 40:
                return False
            if gender not in _VALID_GENDERS:
                return False
            if not isinstance(voice, str) or not voice.strip() or len(voice.strip()) > 80:
                return False
            if language not in _VALID_LANGUAGES:
                return False
            if not isinstance(personality, dict):
                return False
            for key in _PERSONALITY_KEYS:
                value = personality.get(key)
                if not isinstance(value, int) or value < 0 or value > 100:
                    return False
            return True
        except Exception:
            logger.exception("[PersonaManager] Loi validate persona")
            return False

    def _merge_updates(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Gop updates vao persona hien tai ma khong lam mat default keys."""
        merged = copy.deepcopy(self._persona)
        for key, value in updates.items():
            if key == "personality" and isinstance(value, dict):
                merged["personality"].update(value)
            elif key in DEFAULT_PERSONA:
                merged[key] = value
        return merged

    def save(self, updates: dict) -> bool:
        """Luu cap nhat persona. Validate truoc khi save."""
        try:
            if not isinstance(updates, dict):
                return False
            merged = self._merge_updates(updates)
            if not self._validate(merged):
                logger.warning("[PersonaManager] Reject persona update khong hop le")
                return False

            data = json.dumps(merged, ensure_ascii=False)
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO persona (family_id, data, updated_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(family_id) DO UPDATE SET
                        data = excluded.data,
                        updated_at = excluded.updated_at
                    """,
                    (self.family_id, data),
                )
                conn.commit()
            self._persona = merged
            return True
        except Exception:
            logger.exception("[PersonaManager] Khong the save persona")
            return False

    def get_persona(self) -> dict:
        """Tra ve persona hien tai."""
        try:
            return copy.deepcopy(self._persona)
        except Exception:
            logger.exception("[PersonaManager] Khong the copy persona")
            return copy.deepcopy(DEFAULT_PERSONA)

    def get_system_prompt_modifier(self) -> str:
        """Tao doan text bo sung system prompt dua tren tinh cach."""
        try:
            p = self._persona["personality"]
            traits = []
            traits.append("vui ve, hoi nghich ngom" if p["playfulness"] >= 70 else "diem dam, nghiem tuc vua phai")
            traits.append("chu dong bat chuyen" if p["extraversion"] >= 60 else "nhe nhang va biet lang nghe")
            traits.append("nang dong" if p["energy"] >= 65 else "binh tinh")
            name = self.get_name()
            language = "Tieng Viet" if self._persona.get("language") == "vi" else self._persona.get("language", "vi")
            return (
                f"Robot ten la {name}. Hay tra loi bang {language}, "
                f"phong cach {', '.join(traits)}, phu hop tre em 5-12 tuoi."
            )
        except Exception:
            logger.exception("[PersonaManager] Khong the tao prompt modifier")
            return "Hay tra loi than thien, an toan va phu hop tre em 5-12 tuoi."

    def get_voice_id(self) -> str:
        """Tra ve voice ID cho TTS."""
        try:
            voice = self._persona.get("voice") or DEFAULT_PERSONA["voice"]
            return str(voice)
        except Exception:
            logger.exception("[PersonaManager] Khong the lay voice")
            return DEFAULT_PERSONA["voice"]

    def get_name(self) -> str:
        """Tra ve ten robot."""
        try:
            name = self._persona.get("name") or DEFAULT_PERSONA["name"]
            return str(name)
        except Exception:
            logger.exception("[PersonaManager] Khong the lay ten robot")
            return DEFAULT_PERSONA["name"]
