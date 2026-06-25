"""
test_web_search_live.py — Test thực tế WebSearchEngine với API key thật.
Chạy: python tests/test_web_search_live.py
Không cần khởi động robot, không cần pygame/whisper/TTS.
"""

import sys
import os

# Thêm root vào path để import src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env thủ công — không cần python-dotenv
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from src.web_search.search_engine import WebSearchEngine

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg): print(f"{GREEN}✓{RESET} {msg}")
def fail(msg): print(f"{RED}✗{RESET} {msg}")
def info(msg): print(f"{YELLOW}→{RESET} {msg}")


def main():
    print(f"\n{BOLD}=== Web Search Live Test ==={RESET}\n")

    engine = WebSearchEngine()

    # --- Kiểm tra cấu hình ---
    print(f"{BOLD}[1] Cấu hình API keys{RESET}")
    if engine._has_tavily:
        ok(f"Tavily key: ...{engine._tavily_key[-6:]}")
    else:
        fail("Tavily key chưa set — thêm TAVILY_API_KEY vào .env")

    if engine._has_brave:
        ok(f"Brave key: ...{engine._brave_key[-6:]}")
    else:
        info("Brave key không có — chỉ dùng Tavily (bình thường)")

    if not engine.enabled:
        fail("Không có provider nào — dừng test")
        return

    print()

    # --- Test trigger detection ---
    print(f"{BOLD}[2] Nhận diện câu hỏi cần search{RESET}")
    cases = [
        ("hôm nay thời tiết thế nào", True),
        ("tin tức mới nhất là gì", True),
        ("giá bitcoin bây giờ bao nhiêu", True),
        ("what is the latest news", True),
        ("2 cộng 2 bằng mấy", False),
        ("kể chuyện ngủ ngon cho bé", False),
        ("học bảng cửu chương", False),
    ]
    for q, expected in cases:
        result = engine.needs_search(q)
        if result == expected:
            ok(f'"{q}" → {"search" if result else "no search"}')
        else:
            fail(f'"{q}" → expected {"search" if expected else "no search"}, got {"search" if result else "no search"}')

    print()

    # --- Test search thật ---
    print(f"{BOLD}[3] Gọi API thật{RESET}")
    test_queries = [
        "thời tiết Hà Nội hôm nay",
        "tin tức mới nhất Việt Nam",
        "giá vàng hôm nay",
    ]

    for q in test_queries:
        info(f'Search: "{q}"')
        try:
            result = engine.search(q)
            if result and len(result) > 50:
                preview = result[:120].replace("\n", " ")
                ok(f"Kết quả ({len(result)} ký tự): {preview}...")
            elif result:
                ok(f"Kết quả ngắn: {result}")
            else:
                fail("Không có kết quả")
        except Exception as e:
            fail(f"Lỗi: {e}")
        print()


if __name__ == "__main__":
    main()
