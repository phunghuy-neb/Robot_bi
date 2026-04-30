"""Local music playlist library for Robot Bi."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MusicLibrary:
    """Doc playlist music tu resources/music."""

    CATEGORIES = ["vietnamese", "english", "lullabies"]

    def __init__(self, resources_dir: str = "resources/music"):
        """Khoi tao library voi thu muc resources."""
        self.resources_dir = Path(resources_dir)

    def _load_category(self, category: str) -> dict:
        """Load mot playlist category."""
        try:
            if category not in self.CATEGORIES:
                return {"category": category, "tracks": []}
            path = self.resources_dir / category / "playlist.json"
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data.get("tracks"), list):
                return {"category": category, "tracks": []}
            return data
        except Exception:
            logger.exception("[MusicLibrary] Khong the load playlist %s", category)
            return {"category": category, "tracks": []}

    def get_playlist(self, category: str) -> list[dict]:
        """Tra ve danh sach tracks theo category."""
        try:
            return [dict(track) for track in self._load_category(category).get("tracks", [])]
        except Exception:
            logger.exception("[MusicLibrary] get_playlist failed")
            return []

    def search(self, query: str) -> list[dict]:
        """Tim track theo title, artist hoac language."""
        try:
            needle = (query or "").strip().lower()
            results = []
            for category in self.CATEGORIES:
                for track in self.get_playlist(category):
                    haystack = " ".join([
                        str(track.get("title", "")),
                        str(track.get("artist", "")),
                        str(track.get("language", "")),
                    ]).lower()
                    if not needle or needle in haystack:
                        results.append(track)
            return results
        except Exception:
            logger.exception("[MusicLibrary] search failed")
            return []

    def get_track(self, track_id: str) -> dict:
        """Lay track theo id."""
        try:
            for category in self.CATEGORIES:
                for track in self.get_playlist(category):
                    if track.get("id") == track_id:
                        return dict(track)
            return {}
        except Exception:
            logger.exception("[MusicLibrary] get_track failed")
            return {}

    def is_copyrighted(self, track_id: str) -> bool:
        """Tra ve True neu track can Premium/ban quyen."""
        try:
            track = self.get_track(track_id)
            return bool(track.get("copyright", False)) if track else False
        except Exception:
            logger.exception("[MusicLibrary] is_copyrighted failed")
            return False

    def get_local_tracks(self) -> list[dict]:
        """Tra ve tracks co file local ton tai trong resources/music."""
        try:
            tracks = []
            for category in self.CATEGORIES:
                for track in self.get_playlist(category):
                    file_name = track.get("file")
                    if file_name:
                        path = self.resources_dir / category / str(file_name)
                        if path.exists():
                            tracks.append(track)
            return tracks
        except Exception:
            logger.exception("[MusicLibrary] get_local_tracks failed")
            return []
