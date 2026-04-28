"""
homework_classifier.py - Lightweight homework question detection.

Uses local keyword and regex matching only. No LLM call is made here.
"""

from __future__ import annotations

import re
import unicodedata


_HOMEWORK_PHRASES = (
    # Math
    "bang may",
    "tinh",
    "cong",
    "tru",
    "nhan",
    "chia",
    "phuong trinh",
    "hinh hoc",
    "dien tich",
    "chu vi",
    # Vietnamese / language arts
    "viet van",
    "dat cau",
    "phan tich",
    "tac gia",
    "bai tho",
    "doan van",
    # General study
    "bai tap",
    "bai ve nha",
    "homework",
    "hoc bai",
    "on tap",
    "kiem tra",
    "giai thich",
    "nghia la gi",
    "dinh nghia",
    # Science / explanation
    "tai sao",
    "nhu the nao",
    "nguyen nhan",
    "qua trinh",
    "hien tuong",
)


_HOMEWORK_REGEXES = (
    re.compile(r"(?<![a-z0-9])thi(?![a-z0-9])"),
)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized_text) is not None


def classify_homework(text: str) -> bool:
    """Return True when text looks like a homework or study question."""
    if not text or not text.strip():
        return False

    normalized = _normalize_text(text)
    if not normalized:
        return False

    if any(_contains_phrase(normalized, phrase) for phrase in _HOMEWORK_PHRASES):
        return True

    return any(pattern.search(normalized) for pattern in _HOMEWORK_REGEXES)
