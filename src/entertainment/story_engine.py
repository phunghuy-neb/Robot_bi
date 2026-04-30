"""Story engine for local and personalized children stories."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class StoryEngine:
    """Load, select and lightly personalize stories for Robot Bi."""

    def __init__(self, resources_dir: str = "resources/stories"):
        """Khoi tao story engine voi thu muc resources."""
        self.resources_dir = Path(resources_dir)

    def _load_all(self) -> list[dict]:
        """Load tat ca story JSON files."""
        try:
            stories = []
            for path in self.resources_dir.glob("*/*.json"):
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                for story in data.get("stories", []):
                    if isinstance(story, dict):
                        stories.append(dict(story))
            return stories
        except Exception:
            logger.exception("[StoryEngine] load stories failed")
            return []

    def get_story_list(self, category: str | None = None) -> list[dict]:
        """Tra ve danh sach story, co the filter theo category."""
        try:
            stories = self._load_all()
            if category:
                stories = [story for story in stories if story.get("category") == category]
            return [
                {
                    "id": story.get("id"),
                    "title": story.get("title"),
                    "category": story.get("category"),
                    "age_min": story.get("age_min"),
                    "age_max": story.get("age_max"),
                    "duration_min": story.get("duration_min"),
                }
                for story in stories
            ]
        except Exception:
            logger.exception("[StoryEngine] get_story_list failed")
            return []

    def _story_by_id(self, story_id: str) -> dict:
        """Find story by id."""
        try:
            for story in self._load_all():
                if story.get("id") == story_id:
                    return story
            return {}
        except Exception:
            logger.exception("[StoryEngine] _story_by_id failed")
            return {}

    def tell_story(
        self,
        story_id: str | None = None,
        custom_request: str | None = None,
        character_name: str | None = None,
    ) -> dict:
        """
        Ke chuyen.

        Neu story_id co san thi load tu resources. Neu custom_request thi tao
        fallback cuc bo an toan neu LLM khong san sang.
        """
        try:
            story = self._story_by_id(story_id) if story_id else {}
            if not story and custom_request:
                content = (
                    f"Ngay xua co mot ban nho ten {character_name or 'Bi'} rat ham hoc. "
                    f"Ban ay muon nghe cau chuyen ve {custom_request}. "
                    "Sau mot hanh trinh nho, ban hoc duoc rang long tot va su kien tri "
                    "giup moi viec tro nen dep hon."
                )
                story = {
                    "id": "custom",
                    "title": "Cau Chuyen Rieng Cua Be",
                    "category": "custom",
                    "duration_min": 3,
                    "content": content,
                    "moral": "Kien tri va tot bung la dieu dang quy.",
                }
            if not story:
                bedtime = self.get_bedtime_story()
                story = bedtime if bedtime else {}

            if character_name and story.get("content"):
                content = str(story["content"]).replace("Bi", character_name)
            else:
                content = str(story.get("content", ""))
            return {
                "title": story.get("title", ""),
                "content": content,
                "duration_estimate": int(story.get("duration_min", 3)),
                "moral": story.get("moral", ""),
            }
        except Exception:
            logger.exception("[StoryEngine] tell_story failed")
            return {"title": "", "content": "", "duration_estimate": 0, "moral": ""}

    def tell_personalized_story(self, child_name: str, interests: list[str]) -> dict:
        """ Dùng LLM tạo truyện có: 
        - Nhân vật chính tên = child_name 
        - Chủ đề dựa trên interests (từ RAG memory) 
        - Độ dài ~5 phút đọc 
        - Kết thúc có moral lesson 
        - Phù hợp tuổi 5-12
        System prompt đặc biệt để LLM tạo truyện
        ngắn gọn, sinh động, có tên bé trong đó.
        """
        try:
            from src.ai.ai_engine import stream_chat
            topic = ", ".join(interests or ["khám phá thế giới"])
            prompt = (
                f"Bạn là người kể chuyện cho trẻ em. Hãy kể một câu chuyện ngắn gọn (khoảng 3-5 phút đọc). "
                f"Nhân vật chính là bé tên là {child_name}. "
                f"Chủ đề câu chuyện liên quan đến: {topic}. "
                f"Câu chuyện phải sinh động, phù hợp cho trẻ 5-12 tuổi và kết thúc bằng một bài học đạo đức rõ ràng. "
                f"Chỉ trả về nội dung câu chuyện, không thêm giải thích gì khác."
            )
            messages = [{"role": "user", "content": prompt}]
            
            content = ""
            for token in stream_chat(messages):
                content += token
                
            return {
                "title": f"Chuyến phiêu lưu của {child_name}",
                "content": content.strip(),
                "duration_estimate": 5,
                "moral": "Bài học từ câu chuyện"
            }
        except Exception:
            logger.exception("[StoryEngine] tell_personalized_story failed")
            return {"title": "", "content": "", "duration_estimate": 0, "moral": ""}

    def get_bedtime_story(self) -> dict:
        """Tra ve story ngan, nhe nhang cho gio ngu."""
        try:
            bedtime = [story for story in self._load_all() if story.get("category") == "bedtime"]
            story = bedtime[0] if bedtime else {}
            if not story:
                return {}
            return {
                "title": story.get("title", ""),
                "content": story.get("content", ""),
                "duration_estimate": int(story.get("duration_min", 3)),
                "moral": story.get("moral", ""),
            }
        except Exception:
            logger.exception("[StoryEngine] get_bedtime_story failed")
            return {}
