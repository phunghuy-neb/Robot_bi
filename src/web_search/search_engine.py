"""
search_engine.py — Robot Bi: Web Search (Tavily → Brave fallback)
=================================================================
Phát hiện câu hỏi cần thông tin hiện tại → search → trả về context string
sẵn sàng inject vào LLM prompt.

Graceful degradation: không có API key hoặc call fail → trả về "".
Không block reply — gọi trước LLM stream, timeout 5 giây.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 5  # giây

# Từ khoá kích hoạt web search — câu hỏi cần thông tin hiện tại
_TRIGGERS_VI = [
    "tin tức", "tin mới", "mới nhất", "hôm nay", "hôm qua", "ngày mai",
    "tuần này", "tuần tới", "tháng này", "tháng tới", "năm nay",
    "hiện tại", "bây giờ", "hiện nay", "gần đây", "vừa mới",
    "đang xảy ra", "đang diễn ra", "đang có", "mới có",
    "giá", "tỷ giá", "thời tiết", "nhiệt độ", "dự báo thời tiết",
    "kết quả", "tỷ số", "bầu cử", "dịch bệnh", "covid",
    "chứng khoán", "bitcoin", "crypto", "tiền điện tử",
    "cập nhật", "phiên bản mới", "ra mắt",
    "ai đang", "ai là tổng thống", "ai được",
    "sự kiện", "ngày lễ",
]

_TRIGGERS_EN = [
    "news", "today", "yesterday", "tomorrow",
    "this week", "this month", "this year", "last week",
    "current", "currently", "right now", "latest", "recent",
    "just happened", "breaking", "update",
    "weather", "temperature", "forecast",
    "price", "stock", "crypto", "bitcoin",
    "election", "who is president", "who won",
    "new version", "release",
]


class WebSearchEngine:
    """
    Tra cứu web khi phát hiện câu hỏi cần thông tin hiện tại.
    Tavily → Brave → "" (graceful fallback).
    """

    def __init__(self) -> None:
        self._tavily_key = os.getenv("TAVILY_API_KEY", "")
        self._brave_key = os.getenv("BRAVE_API_KEY", "")
        self._has_tavily = bool(
            self._tavily_key and not self._tavily_key.startswith("DIEN_")
            and self._tavily_key != "your_tavily_api_key_here"
        )
        self._has_brave = bool(
            self._brave_key and not self._brave_key.startswith("DIEN_")
            and self._brave_key != "your_brave_api_key_here"
        )
        if not self._has_tavily and not self._has_brave:
            logger.info("[WebSearch] Không có API key — web search disabled")
        else:
            providers = []
            if self._has_tavily:
                providers.append("Tavily")
            if self._has_brave:
                providers.append("Brave")
            logger.info("[WebSearch] Active providers: %s", ", ".join(providers))

    @property
    def enabled(self) -> bool:
        return self._has_tavily or self._has_brave

    def needs_search(self, query: str) -> bool:
        """Phát hiện nhanh xem câu hỏi có cần search web không."""
        if not query or len(query.strip()) < 5:
            return False
        q = query.lower()
        for kw in _TRIGGERS_VI:
            if kw in q:
                return True
        for kw in _TRIGGERS_EN:
            if kw in q:
                return True
        return False

    def search_if_needed(self, query: str) -> str:
        """
        Kiểm tra câu hỏi, search nếu cần.
        Returns: context string inject vào LLM prompt, hoặc "".
        """
        if not self.enabled or not self.needs_search(query):
            return ""
        result = self.search(query)
        return result

    def search(self, query: str) -> str:
        """Search web: Tavily trước, Brave làm fallback."""
        if self._has_tavily:
            try:
                result = self._tavily_search(query)
                if result:
                    logger.debug("[WebSearch] Tavily OK, %d ký tự", len(result))
                    return result
            except Exception as e:
                logger.warning("[WebSearch] Tavily lỗi (%s) — chuyển Brave", e)

        if self._has_brave:
            try:
                result = self._brave_search(query)
                if result:
                    logger.debug("[WebSearch] Brave OK, %d ký tự", len(result))
                    return result
            except Exception as e:
                logger.warning("[WebSearch] Brave lỗi (%s) — không có search context", e)

        return ""

    def _tavily_search(self, query: str) -> str:
        """Gọi Tavily Search API — trả về context string."""
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self._tavily_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 3,
                "include_answer": True,
                "include_raw_content": False,
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        data = resp.json()

        parts = []
        answer = (data.get("answer") or "").strip()
        if answer:
            parts.append(f"Tóm tắt: {answer}")

        for r in data.get("results", [])[:3]:
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "").strip()[:300]
            if title and content:
                parts.append(f"- {title}: {content}")

        if not parts:
            return ""

        return (
            "[Thông tin web tìm được — dùng tự nhiên nếu liên quan, không nhắc nguồn]\n"
            + "\n".join(parts)
        )

    def _brave_search(self, query: str) -> str:
        """Gọi Brave Search API — trả về context string."""
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self._brave_key,
            },
            params={"q": query, "count": 3, "text_decorations": False},
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")
        data = resp.json()

        parts = []
        for r in data.get("web", {}).get("results", [])[:3]:
            title = (r.get("title") or "").strip()
            desc = (r.get("description") or "").strip()[:300]
            if title and desc:
                parts.append(f"- {title}: {desc}")

        if not parts:
            return ""

        return (
            "[Thông tin web tìm được — dùng tự nhiên nếu liên quan, không nhắc nguồn]\n"
            + "\n".join(parts)
        )
