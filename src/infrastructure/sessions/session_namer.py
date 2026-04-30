"""
session_namer.py - Generate short conversation titles for Robot Bi sessions.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def _fallback_title(user_text: str) -> str:
    fallback = (user_text or "").strip()[:30].strip()
    return fallback or "Cuoc tro chuyen"


def _generate_session_title(user_text: str) -> str:
    prompt = (
        "Tom tat cau hoi sau thanh 3-5 tu tieng Viet ngan gon, khong dau cham cuoi.\n"
        f"Cau hoi: {user_text}\n"
        "Chi tra loi ten chu de, khong giai thich."
    )
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_api_key or groq_api_key.startswith("DIEN_"):
        return _fallback_title(user_text)

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 20,
        "temperature": 0.3,
        "stream": False,
    }

    try:
        response = requests.post(
            _GROQ_URL,
            headers=headers,
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        title = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        title = title.rstrip(".").strip()
        return title or _fallback_title(user_text)
    except Exception:
        return _fallback_title(user_text)
