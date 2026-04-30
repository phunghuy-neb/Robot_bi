"""
EmotionAnalyzer - Tong hop cam xuc be tu text, giong noi va tuong tac.

Module nay dung keyword matching va heuristic cuc nhe, khong goi LLM.
Emotion logs duoc scope theo family_id trong SQLite.
"""

from __future__ import annotations

import logging
import os
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)


class Emotion(str, Enum):
    """Tap emotion duoc Robot Bi ho tro."""

    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"
    EXCITED = "excited"
    STRESSED = "stressed"
    ANGRY = "angry"


_KEYWORDS = {
    Emotion.HAPPY: ["vui", "thich", "hay qua", "tuyet", "cuoi", "hanh phuc", "yay"],
    Emotion.SAD: ["buon", "khoc", "chan", "co don", "met moi", "that vong"],
    Emotion.EXCITED: ["hao hung", "phan khich", "da qua", "wow", "nhanh len", "tuyet voi"],
    Emotion.STRESSED: ["lo", "cang thang", "ap luc", "so qua", "kho qua", "khong lam duoc"],
    Emotion.ANGRY: ["gian", "tuc", "buc", "khong thich", "ghet", "ca nay"],
}


def _emotion_bucket(value: str) -> str:
    """Map raw emotions to the four buckets used by the parent chart."""
    if value in {Emotion.HAPPY.value, Emotion.EXCITED.value}:
        return "happy"
    if value == Emotion.SAD.value:
        return "sad"
    if value in {Emotion.STRESSED.value, Emotion.ANGRY.value, "stress"}:
        return "stressed"
    return "neutral"


def _breakdown_percent(rows) -> dict:
    """Return percent breakdown for happy/neutral/sad/stressed."""
    if not rows:
        return {"happy": 0, "neutral": 100, "sad": 0, "stressed": 0}
    counts = Counter(_emotion_bucket(row["emotion"]) for row in rows)
    total = max(1, sum(counts.values()))
    return {
        "happy": round(counts.get("happy", 0) * 100 / total),
        "neutral": round(counts.get("neutral", 0) * 100 / total),
        "sad": round(counts.get("sad", 0) * 100 / total),
        "stressed": round(counts.get("stressed", 0) * 100 / total),
    }


def _normalize_text(text: str) -> str:
    """Lowercase va bo dau tieng Viet de keyword matching on dinh."""
    try:
        lowered = (text or "").strip().lower()
        decomposed = unicodedata.normalize("NFD", lowered)
        return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    except Exception:
        logger.exception("[EmotionAnalyzer] normalize text failed")
        return ""


class EmotionAnalyzer:
    """Phan tich va luu lich su cam xuc theo family."""

    def __init__(self, family_id: str | None = None):
        """Khoi tao analyzer va dam bao schema phu da san sang."""
        self.family_id = family_id or os.getenv("FAMILY_ID", "default")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Tao bang emotion_logs neu chua ton tai."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS emotion_logs (
                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        family_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        emotion TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        source TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_emotion_logs_family_time
                    ON emotion_logs (family_id, timestamp)
                    """
                )
                conn.commit()
        except Exception:
            logger.exception("[EmotionAnalyzer] Khong the tao schema emotion_logs")

    def analyze_text(self, text: str) -> tuple[Emotion, float]:
        """
        Phan tich cam xuc tu text bang keyword matching.

        Returns tuple `(emotion, confidence)` voi confidence 0-1.
        """
        try:
            normalized = _normalize_text(text)
            if not normalized:
                return Emotion.NEUTRAL, 0.5

            scores: dict[Emotion, int] = {}
            for emotion, words in _KEYWORDS.items():
                scores[emotion] = sum(1 for word in words if word in normalized)
            best, count = max(scores.items(), key=lambda item: item[1])
            if count <= 0:
                return Emotion.NEUTRAL, 0.55
            confidence = min(0.95, 0.6 + count * 0.15)
            return best, confidence
        except Exception:
            logger.exception("[EmotionAnalyzer] analyze_text failed")
            return Emotion.NEUTRAL, 0.0

    def analyze_voice_features(self, energy: float, pitch: float) -> Emotion:
        """Phan tich cam xuc tu dac trung nang luong va pitch cua giong noi."""
        try:
            energy = float(energy)
            pitch = float(pitch)
            if energy >= 0.75 and pitch >= 0.65:
                return Emotion.EXCITED
            if energy >= 0.7 and pitch < 0.45:
                return Emotion.ANGRY
            if energy <= 0.25 and pitch <= 0.45:
                return Emotion.SAD
            if energy >= 0.55 and pitch >= 0.5:
                return Emotion.HAPPY
            return Emotion.NEUTRAL
        except Exception:
            logger.exception("[EmotionAnalyzer] analyze_voice_features failed")
            return Emotion.NEUTRAL

    def get_combined_emotion(
        self,
        text: str | None = None,
        voice_energy: float | None = None,
        voice_pitch: float | None = None,
    ) -> dict:
        """Tong hop text va giong noi thanh dict `{emotion, confidence, sources}`."""
        try:
            sources = []
            votes: list[tuple[Emotion, float]] = []
            if text is not None:
                emotion, confidence = self.analyze_text(text)
                votes.append((emotion, confidence))
                sources.append("text")
            if voice_energy is not None and voice_pitch is not None:
                voice_emotion = self.analyze_voice_features(voice_energy, voice_pitch)
                votes.append((voice_emotion, 0.65))
                sources.append("voice")

            if not votes:
                return {"emotion": Emotion.NEUTRAL.value, "confidence": 0.5, "sources": []}

            weighted: dict[Emotion, float] = {}
            for emotion, confidence in votes:
                weighted[emotion] = weighted.get(emotion, 0.0) + confidence
            best = max(weighted.items(), key=lambda item: item[1])[0]
            confidence = min(1.0, weighted[best] / max(1, len(votes)))
            return {"emotion": best.value, "confidence": round(confidence, 3), "sources": sources}
        except Exception:
            logger.exception("[EmotionAnalyzer] get_combined_emotion failed")
            return {"emotion": Emotion.NEUTRAL.value, "confidence": 0.0, "sources": []}

    def record_emotion(
        self,
        emotion: Emotion,
        confidence: float,
        family_id: str | None = None,
    ) -> None:
        """Luu emotion vao DB."""
        try:
            fid = family_id or self.family_id
            value = emotion.value if isinstance(emotion, Emotion) else str(emotion)
            conf = max(0.0, min(1.0, float(confidence)))
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO emotion_logs
                        (family_id, timestamp, emotion, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (fid, datetime.now(timezone.utc).isoformat(timespec="seconds"), value, conf, "combined"),
                )
                conn.commit()
        except Exception:
            logger.exception("[EmotionAnalyzer] record_emotion failed")

    def get_today_summary(self, family_id: str) -> dict:
        """Tra ve cam xuc chu dao hom nay."""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT emotion, confidence
                    FROM emotion_logs
                    WHERE family_id = ? AND date(timestamp) = ?
                    """,
                    (family_id, today),
                ).fetchall()
            if not rows:
                return {"date": today, "dominant": Emotion.NEUTRAL.value, "count": 0, "average_confidence": 0.0}
            counts = Counter(row["emotion"] for row in rows)
            dominant = counts.most_common(1)[0][0]
            avg = sum(float(row["confidence"]) for row in rows) / len(rows)
            return {"date": today, "dominant": dominant, "count": len(rows), "average_confidence": round(avg, 3)}
        except Exception:
            logger.exception("[EmotionAnalyzer] get_today_summary failed")
            return {"date": datetime.now(timezone.utc).date().isoformat(), "dominant": Emotion.NEUTRAL.value, "count": 0, "average_confidence": 0.0}

    def get_weekly_summary(self, family_id: str) -> list[dict]:
        """Tra ve summary cam xuc 7 ngay gan nhat."""
        try:
            today = datetime.now(timezone.utc).date()
            result = []
            with get_db_connection() as conn:
                for offset in range(6, -1, -1):
                    day = (today - timedelta(days=offset)).isoformat()
                    rows = conn.execute(
                        """
                        SELECT emotion, confidence
                        FROM emotion_logs
                        WHERE family_id = ? AND date(timestamp) = ?
                        """,
                        (family_id, day),
                    ).fetchall()
                    if rows:
                        counts = Counter(row["emotion"] for row in rows)
                        dominant = counts.most_common(1)[0][0]
                        avg = sum(float(row["confidence"]) for row in rows) / len(rows)
                    else:
                        dominant = Emotion.NEUTRAL.value
                        avg = 0.0
                    result.append({
                        "date": day,
                        "dominant": dominant,
                        "breakdown": _breakdown_percent(rows),
                        "count": len(rows),
                        "average_confidence": round(avg, 3),
                    })
            return result
        except Exception:
            logger.exception("[EmotionAnalyzer] get_weekly_summary failed")
            today = datetime.now(timezone.utc).date()
            return [
                {
                    "date": (today - timedelta(days=offset)).isoformat(),
                    "dominant": Emotion.NEUTRAL.value,
                    "breakdown": {"happy": 0, "neutral": 100, "sad": 0, "stressed": 0},
                    "count": 0,
                    "average_confidence": 0.0,
                }
                for offset in range(6, -1, -1)
            ]
