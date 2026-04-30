"""Simulation-safe music player backend."""

from __future__ import annotations

import logging
import time

from src.entertainment.music_library import MusicLibrary

logger = logging.getLogger(__name__)


class MusicPlayer:
    """Dieu khien phat nhac o che do simulation neu chua co audio backend."""

    def __init__(self, library: MusicLibrary | None = None):
        """Khoi tao player voi volume mac dinh 60."""
        self.library = library or MusicLibrary()
        self.playing = False
        self.paused = False
        self.volume = 60
        self.track: dict | None = None
        self.started_at: float | None = None

    def play(self, track_id: str | None = None, category: str | None = None) -> dict:
        """Phat nhac. Returns `{status, track_info}`."""
        try:
            track = self.library.get_track(track_id) if track_id else {}
            if not track and category:
                playlist = self.library.get_playlist(category)
                track = playlist[0] if playlist else {}
            if not track:
                playlist = self.library.get_playlist("lullabies")
                track = playlist[0] if playlist else {}
            self.track = dict(track) if track else None
            self.playing = self.track is not None
            self.paused = False
            self.started_at = time.time() if self.playing else None
            if self.track:
                logger.info("[MusicPlayer] SIMULATION: play %s", self.track.get("id"))
            return {"status": "playing" if self.playing else "not_found", "track_info": self.track}
        except Exception:
            logger.exception("[MusicPlayer] play failed")
            return {"status": "error", "track_info": None}

    def stop(self) -> bool:
        """Dung phat nhac."""
        try:
            logger.info("[MusicPlayer] SIMULATION: stop")
            self.playing = False
            self.paused = False
            self.track = None
            self.started_at = None
            return True
        except Exception:
            logger.exception("[MusicPlayer] stop failed")
            return False

    def pause(self) -> bool:
        """Tam dung phat nhac."""
        try:
            if self.playing:
                logger.info("[MusicPlayer] SIMULATION: pause")
                self.paused = True
            return True
        except Exception:
            logger.exception("[MusicPlayer] pause failed")
            return False

    def resume(self) -> bool:
        """Tiep tuc phat nhac."""
        try:
            if self.playing:
                logger.info("[MusicPlayer] SIMULATION: resume")
                self.paused = False
            return True
        except Exception:
            logger.exception("[MusicPlayer] resume failed")
            return False

    def next_track(self) -> dict:
        """Chuyen sang track tiep theo."""
        logger.info("[MusicPlayer] SIMULATION: next track")
        return {"status": "ok", "action": "next"}

    def prev_track(self) -> dict:
        """Quay lai track truoc."""
        logger.info("[MusicPlayer] SIMULATION: previous track")
        return {"status": "ok", "action": "previous"}

    def toggle_shuffle(self) -> dict:
        """Bat/tat shuffle."""
        self._shuffle = not getattr(self, "_shuffle", False)
        logger.info("[MusicPlayer] SIMULATION: shuffle=%s", self._shuffle)
        return {"status": "ok", "shuffle": self._shuffle}

    def toggle_repeat(self) -> dict:
        """Bat/tat repeat."""
        self._repeat = not getattr(self, "_repeat", False)
        logger.info("[MusicPlayer] SIMULATION: repeat=%s", self._repeat)
        return {"status": "ok", "repeat": self._repeat}

    def set_volume(self, volume: int) -> bool:
        """Dat volume trong range 0-100."""
        try:
            level = int(volume)
            if level < 0 or level > 100:
                return False
            self.volume = level
            logger.info("[MusicPlayer] SIMULATION: volume=%d", level)
            return True
        except Exception:
            logger.exception("[MusicPlayer] set_volume failed")
            return False

    def play_lullaby(self, fade_duration_min: int = 15):
        """ Phát nhạc ru ngủ từ resources/music/lullabies/ 
        Giảm volume từ 80% → 0% trong fade_duration_min phút 
        Dùng threading.Timer để fade gradient 
        Tắt hẳn khi volume = 0 """
        try:
            self.set_volume(80)
            result = self.play(category="lullabies")
            if self.track is not None:
                self.track["fade_duration_min"] = max(1, int(fade_duration_min))
            
            total_steps = 10
            
            def _fade_step(current_vol, target_vol, steps_remaining):
                if steps_remaining <= 0 or current_vol <= 0:
                    self.stop()
                    return
                new_vol = current_vol - (current_vol / steps_remaining)
                self.set_volume(int(new_vol))
                import threading
                timer = threading.Timer(
                    fade_duration_min * 60 / total_steps,
                    _fade_step,
                    args=[new_vol, 0, steps_remaining - 1]
                )
                timer.daemon = True
                timer.start()

            _fade_step(80, 0, total_steps)
            
            return result
        except Exception:
            logger.exception("[MusicPlayer] play_lullaby failed")
            return {"status": "error", "track_info": None}

    def get_status(self) -> dict:
        """Returns `{playing, track, volume, position}`."""
        try:
            position = 0
            if self.playing and self.started_at is not None and not self.paused:
                position = int(time.time() - self.started_at)
            return {
                "playing": self.playing,
                "paused": self.paused,
                "track": self.track,
                "volume": self.volume,
                "position": position,
            }
        except Exception:
            logger.exception("[MusicPlayer] get_status failed")
            return {"playing": False, "paused": False, "track": None, "volume": self.volume, "position": 0}
