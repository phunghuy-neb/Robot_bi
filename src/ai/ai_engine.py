"""
core_ai.py — Robot Bi AI Core
Fallback chain: Cerebras → Groq → Sambanova → Gemini → Cloudflare Workers AI
- Cerebras Llama 3.3 70B: primary, ~450 token/s, ít bị rate-limit nhất
- Groq Llama 3.3 70B: secondary, ~400 token/s, có cooldown riêng
- Sambanova Llama 3.3 70B: fallback
- Gemini 2.0 Flash: fallback, ổn định cao
- Cloudflare Workers AI: last resort (non-streaming)
"""

import logging
import os
import json
import time
import threading
import requests
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

# Load config.json
_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"
try:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
        _CONFIG = json.load(_f)
except FileNotFoundError:
    _CONFIG = {
        "groq_model": "llama-3.3-70b-versatile",
        "gemini_model": "gemini-2.0-flash",
        "max_history_turns": 10,
        "groq_cooldown_seconds": 60,
    }

# API Keys từ .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")

# Endpoints
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_CONFIG['gemini_model']}:streamGenerateContent"
)
_CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
_SAMBANOVA_URL = "https://api.sambanova.ai/v1/chat/completions"

# Trạng thái quota nội bộ
_groq_fail_streak = 0
_groq_cooldown_until = 0.0
_groq_lock = threading.Lock()
_GROQ_COOLDOWN = _CONFIG.get("groq_cooldown_seconds", 60)


def _get_system_prompt() -> str:
    """Lấy system prompt từ prompts.py và thêm rule ngôn ngữ."""
    try:
        from src.ai.prompts import MAIN_SYSTEM_PROMPT
        base = MAIN_SYSTEM_PROMPT
    except ImportError:
        try:
            from src.ai import prompts
            base = prompts.MAIN_SYSTEM_PROMPT
        except ImportError:
            base = (
                "Bạn là Bi, một robot gia sư thông minh và gần gũi. "
                "Bạn xưng là 'Bi' và gọi người dùng là 'bạn' hoặc 'em'. "
                "Luôn trả lời ngắn gọn 3-4 câu, vui vẻ, dễ hiểu."
            )

    language_rule = (
        "\n\nNGÔN NGỮ PHẢN HỒI — BẮT BUỘC TUÂN THỦ:\n"
        "- Phát hiện ngôn ngữ bé đang dùng trong tin nhắn cuối.\n"
        "- Trả lời TOÀN BỘ bằng đúng ngôn ngữ đó. KHÔNG trộn ngôn ngữ khác.\n"
        "- Bé nói tiếng Việt → trả lời 100% tiếng Việt.\n"
        "- Bé nói tiếng Anh → trả lời 100% tiếng Anh.\n"
        "- Ngoại lệ duy nhất: bé chủ động yêu cầu kết hợp 2 ngôn ngữ.\n"
        "- TUYỆT ĐỐI không tự ý thêm tiếng Trung hoặc ngôn ngữ không được yêu cầu.\n"
        "- Câu trả lời ngắn gọn, tự nhiên, phù hợp trẻ em."
    )
    return base + language_rule


def _get_error_response() -> str:
    """Lấy ERROR_RESPONSE từ prompts.py, fallback về chuỗi mặc định."""
    try:
        from src.ai.prompts import ERROR_RESPONSE
        return ERROR_RESPONSE
    except ImportError:
        pass
    try:
        from src.ai import prompts
        return prompts.ERROR_RESPONSE
    except (ImportError, AttributeError):
        return "Xin lỗi bé, Bi đang gặp sự cố kết nối. Bé thử lại sau một chút nhé!"


def _stream_openai_compat(
    url: str, api_key: str, model: str, messages: list, system_prompt: str, provider: str
) -> Generator[str, None, None]:
    """Gọi bất kỳ OpenAI-compatible streaming endpoint."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 512,
        "temperature": 0.7,
        "stream": True,
    }
    resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=20)
    if resp.status_code == 429:
        raise RuntimeError(f"{provider} quota exceeded (429)")
    if resp.status_code != 200:
        raise RuntimeError(f"{provider} HTTP {resp.status_code}: {resp.text[:200]}")

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield delta
        except (json.JSONDecodeError, KeyError, IndexError):
            continue


def _stream_groq(messages: list, system_prompt: str) -> Generator[str, None, None]:
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("DIEN_"):
        raise ValueError("GROQ_API_KEY chưa được cấu hình trong .env")
    yield from _stream_openai_compat(
        _GROQ_URL, GROQ_API_KEY, _CONFIG["groq_model"], messages, system_prompt, "Groq"
    )


def _stream_gemini(messages: list, system_prompt: str) -> Generator[str, None, None]:
    """Gọi Gemini API, stream từng token."""
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("DIEN_"):
        raise RuntimeError("GEMINI_API_KEY chưa được cấu hình trong .env")

    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7},
    }
    url = f"{_GEMINI_URL}?alt=sse"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=20)

    if resp.status_code == 429:
        raise RuntimeError("Gemini quota exceeded (429)")
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not line.startswith("data: "):
            continue
        data = line[6:]
        try:
            chunk = json.loads(data)
            parts = (
                chunk.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            for part in parts:
                text = part.get("text", "")
                if text:
                    yield text
        except (json.JSONDecodeError, KeyError, IndexError):
            continue


def _stream_cerebras(messages: list, system_prompt: str) -> Generator[str, None, None]:
    if not CEREBRAS_API_KEY or CEREBRAS_API_KEY.startswith("DIEN_"):
        raise RuntimeError("CEREBRAS_API_KEY chưa được cấu hình trong .env")
    yield from _stream_openai_compat(
        _CEREBRAS_URL, CEREBRAS_API_KEY, "llama-3.3-70b", messages, system_prompt, "Cerebras"
    )


def _stream_sambanova(messages: list, system_prompt: str) -> Generator[str, None, None]:
    if not SAMBANOVA_API_KEY or SAMBANOVA_API_KEY.startswith("DIEN_"):
        raise RuntimeError("SAMBANOVA_API_KEY chưa được cấu hình trong .env")
    yield from _stream_openai_compat(
        _SAMBANOVA_URL, SAMBANOVA_API_KEY, "llama-3.3-70b", messages, system_prompt, "Sambanova"
    )


def _stream_cloudflare(messages: list, system_prompt: str) -> Generator[str, None, None]:
    """Gọi Cloudflare Workers AI (non-streaming, yield toàn bộ response)."""
    if not CLOUDFLARE_API_KEY or CLOUDFLARE_ACCOUNT_ID:
        pass  # will check below
    if not CLOUDFLARE_API_KEY or CLOUDFLARE_API_KEY.startswith("DIEN_"):
        raise RuntimeError("CLOUDFLARE_API_KEY chưa được cấu hình trong .env")
    if not CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_ACCOUNT_ID.startswith("DIEN_"):
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID chưa được cấu hình trong .env")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}"
        "/ai/run/@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    )
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 512,
        "temperature": 0.7,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 429:
        raise RuntimeError("Cloudflare quota exceeded (429)")
    if resp.status_code != 200:
        raise RuntimeError(f"Cloudflare HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    text = data.get("result", {}).get("response", "")
    if not text:
        raise RuntimeError("Cloudflare returned empty response")
    yield text


def stream_chat(messages: list) -> Generator[str, None, None]:
    """
    Public API — gọi hàm này từ main_loop.py.
    Fallback chain: Cerebras → Groq → Sambanova → Gemini → Cloudflare → thông báo lỗi.

    Args:
        messages: list of {"role": "user"|"assistant", "content": str}
    """
    global _groq_fail_streak, _groq_cooldown_until

    # Trim history để tiết kiệm token
    max_turns = _CONFIG.get("max_history_turns", 10)
    if len(messages) > max_turns * 2:
        messages = messages[-(max_turns * 2):]

    system_prompt = _get_system_prompt()
    now = time.time()

    # --- Cerebras (primary — nhanh ngang Groq, ít bị rate-limit hơn) ---
    try:
        logger.debug("[Bi - Não] Cerebras (Llama 70B)...")
        yield from _stream_cerebras(messages, system_prompt)
        return
    except Exception as e:
        logger.warning("[Bi - Não] Cerebras lỗi (%s) — chuyển Groq", e)

    # --- Groq (secondary — có cooldown riêng để tránh spam khi hết quota) ---
    with _groq_lock:
        groq_cooldown_until = _groq_cooldown_until

    if now > groq_cooldown_until:
        try:
            logger.debug("[Bi - Não] Groq (Llama 70B)...")
            yield from _stream_groq(messages, system_prompt)
            with _groq_lock:
                _groq_fail_streak = 0
            return
        except Exception as e:
            cooldown_started = False
            with _groq_lock:
                _groq_fail_streak += 1
                if _groq_fail_streak >= 3:
                    _groq_cooldown_until = now + _GROQ_COOLDOWN
                    _groq_fail_streak = 0
                    cooldown_started = True
            logger.warning("[Bi - Não] Groq lỗi (%s) — chuyển Sambanova", e)
            if cooldown_started:
                logger.warning("[Bi - Não] Groq tạm dừng %ss", _GROQ_COOLDOWN)

    # --- Sambanova ---
    try:
        logger.debug("[Bi - Não] Sambanova (Llama 70B)...")
        yield from _stream_sambanova(messages, system_prompt)
        return
    except Exception as e:
        logger.warning("[Bi - Não] Sambanova lỗi (%s) — chuyển Gemini", e)

    # --- Gemini ---
    try:
        logger.debug("[Bi - Não] Gemini 2.0 Flash...")
        yield from _stream_gemini(messages, system_prompt)
        return
    except Exception as e:
        logger.warning("[Bi - Não] Gemini lỗi (%s) — chuyển Cloudflare", e)

    # --- Cloudflare Workers AI (last resort) ---
    try:
        logger.debug("[Bi - Não] Cloudflare Workers AI...")
        yield from _stream_cloudflare(messages, system_prompt)
        return
    except Exception as e:
        logger.warning("[Bi - Não] Cloudflare lỗi (%s) — tất cả provider fail", e)

    # --- Tất cả fail ---
    yield _get_error_response()


# ── Backward-compat class — giữ để không break main_loop.py ──────────────────

class BiAI:
    """
    Backward-compat wrapper. main_loop.py dùng BiAI().stream_chat(user_text).
    Nội bộ gọi stream_chat() module-level và duy trì history.
    """

    def __init__(self) -> None:
        self.history: list = []
        self.total_turns: int = 0

    def stream_chat(self, user_input: str, history: list = None) -> Generator[str, None, None]:
        """
        Stream phản hồi từ AI.

        Args:
            user_input: Văn bản câu hỏi của người dùng.
            history: Nếu truyền vào thì dùng history này (không cập nhật nội bộ).
                     Nếu None thì dùng và cập nhật self.history.
        """
        if history is not None:
            msgs = list(history)
        else:
            msgs = list(self.history)
        msgs.append({"role": "user", "content": user_input})

        full_reply = ""
        for token in stream_chat(msgs):
            full_reply += token
            yield token

        # Cập nhật history nội bộ khi không có history bên ngoài truyền vào
        if history is None and full_reply:
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": full_reply.strip()})
            max_turns = _CONFIG.get("max_history_turns", 10)
            if len(self.history) > max_turns * 2:
                self.history = self.history[-(max_turns * 2):]
            self.total_turns += 1

    def reset_history(self) -> None:
        """Xóa toàn bộ lịch sử hội thoại."""
        self.history.clear()


# ── Test độc lập ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  TEST core_ai.py — Full Fallback Chain")
    print("=" * 60)
    print(f"  Groq model    : {_CONFIG['groq_model']}")
    print(f"  Gemini model  : {_CONFIG['gemini_model']}")
    print(f"  GROQ_API_KEY  : {'OK' if GROQ_API_KEY and not GROQ_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}")
    print(f"  GEMINI_API_KEY: {'OK' if GEMINI_API_KEY and not GEMINI_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}")
    print(f"  CEREBRAS_API_KEY : {'OK' if CEREBRAS_API_KEY and not CEREBRAS_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}")
    print(f"  SAMBANOVA_API_KEY: {'OK' if SAMBANOVA_API_KEY and not SAMBANOVA_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}")
    print(f"  CLOUDFLARE_API_KEY: {'OK' if CLOUDFLARE_API_KEY and not CLOUDFLARE_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}\n")

    bi = BiAI()
    test_questions = [
        "Xin chào Bi!",
        "Tại sao bầu trời màu xanh?",
    ]

    for q in test_questions:
        print(f"\nBan: {q}")
        print("Bi: ", end="", flush=True)
        for token in bi.stream_chat(q):
            print(token, end="", flush=True)
        print()

    print(f"\nTest hoàn thành — {bi.total_turns} lượt hội thoại.")
