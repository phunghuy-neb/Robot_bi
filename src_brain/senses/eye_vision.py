"""
eye_vision.py — Module thị giác Robot Bi (Sprint 3)
Class EyeVision: motion detection (MOG2), face recognition (histogram fallback),
clip recording (pre/post buffer), graceful degradation khi không có camera.

SRS Reference: Phần 3.4 — Nhóm 4 Giám sát an ninh
"""

import sys
import cv2
import numpy as np
import os
import threading
import time
import logging
from collections import deque
from datetime import datetime
from pathlib import Path

# Fix encoding cho console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

logger = logging.getLogger(__name__)


class EyeVision:
    """
    Module thị giác của Robot Bi.
    Chạy trong daemon thread — không block voice I/O.

    Sự kiện phát sinh:
      - "motion"     : phát hiện chuyển động (contour area > 5000 px²)
      - "stranger"   : phát hiện khuôn mặt không khớp known_faces
      - "known_face" : nhận ra thành viên đã đăng ký (clip_path = tên người)
    """

    # Ngưỡng motion detection (px²)
    _MOTION_THRESHOLD = 5000
    # Nhận dạng face mỗi N frame (giảm CPU)
    _FACE_INTERVAL = 10
    # Pre-event buffer: 5 giây ở 20fps = 100 frame
    _PRE_BUFFER_SIZE = 100
    # Ghi thêm sau sự kiện: 10 giây ở 20fps = 200 frame
    _POST_EVENT_FRAMES = 200
    # Ngưỡng histogram similarity (0→1, cao hơn = giống hơn)
    _FACE_SIMILARITY_THRESHOLD = 0.5
    # Target frame size
    _FRAME_WIDTH = 640
    _FRAME_HEIGHT = 480

    def __init__(
        self,
        camera_index: int = 0,
        known_faces_dir: str = "src_brain/senses/vision_data/known_faces",
        clips_dir: str = "src_brain/senses/vision_data/clips",
        on_event_callback=None,
    ):
        """
        Args:
            camera_index: index camera (0 = mặc định). Index không tồn tại → graceful degrade.
            known_faces_dir: thư mục chứa ảnh thành viên (mỗi người 1 subfolder).
            clips_dir: thư mục lưu clip sự kiện MP4.
            on_event_callback: callable(event_type: str, clip_path: str | None).
        """
        self.camera_index = camera_index
        self.known_faces_dir = Path(known_faces_dir)
        self.clips_dir = Path(clips_dir)
        self.on_event_callback = on_event_callback

        # Tạo thư mục data nếu chưa có
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)

        # State
        self._running = False
        self._surveillance_mode = False
        self._thread: threading.Thread | None = None
        self._cap: cv2.VideoCapture | None = None

        # Stats
        self._frames_processed = 0
        self._events_detected = 0
        self._start_time: float | None = None

        # Face database: {name: [histogram, ...]}
        self._known_faces: dict[str, list] = {}
        self._face_cascade: cv2.CascadeClassifier | None = None
        self._load_face_resources()

        # MOG2 background subtractor
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )

        # Pre-event circular buffer
        self._pre_buffer: deque = deque(maxlen=self._PRE_BUFFER_SIZE)

        # Clip recording state
        self._recording = False
        self._post_frames_remaining = 0
        self._current_clip_frames: list = []
        self._current_event_type: str = ""

    # ─────────────────────────── Public API ────────────────────────────────

    def start(self) -> None:
        """Bắt đầu vòng lặp capture trong daemon thread. Non-blocking."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(
            target=self._vision_loop, daemon=True, name="EyeVision"
        )
        self._thread.start()
        logger.info("[Bi - Mắt] EyeVision started (camera_index=%d)", self.camera_index)

    def stop(self) -> None:
        """Dừng daemon thread, giải phóng camera."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
        logger.info("[Bi - Mắt] EyeVision stopped")

    def set_surveillance_mode(self, active: bool) -> None:
        """
        True: bật chế độ giám sát đầy đủ (motion + stranger detection + clip).
        False: tắt giám sát, chỉ giữ face detection cơ bản.
        """
        self._surveillance_mode = active
        status = "BẬT" if active else "TẮT"
        print(f"[Bi - Mắt] Chế độ giám sát: {status}")

    def register_face(self, name: str, image_path: str) -> bool:
        """
        Đăng ký khuôn mặt mới vào known_faces database.

        Args:
            name: tên người (sẽ tạo subfolder tương ứng).
            image_path: đường dẫn ảnh nguồn.

        Returns:
            True nếu đăng ký thành công.
        """
        try:
            src = Path(image_path)
            if not src.exists():
                logger.warning("[Bi - Mắt] Ảnh không tồn tại: %s", image_path)
                return False

            dest_dir = self.known_faces_dir / name
            dest_dir.mkdir(parents=True, exist_ok=True)
            # Đặt tên file theo số thứ tự
            existing = list(dest_dir.glob("*.jpg")) + list(dest_dir.glob("*.png"))
            dest_file = dest_dir / f"{len(existing) + 1:03d}.jpg"

            img = cv2.imread(str(src))
            if img is None:
                logger.warning("[Bi - Mắt] Không đọc được ảnh: %s", image_path)
                return False
            cv2.imwrite(str(dest_file), img)

            # Reload face database
            self._load_face_resources()
            print(f"[Bi - Mắt] Đã đăng ký khuôn mặt: {name}")
            return True

        except Exception as e:
            logger.error("[Bi - Mắt] register_face lỗi: %s", e)
            return False

    def get_stats(self) -> dict:
        """Trả về thống kê hoạt động."""
        uptime = (time.time() - self._start_time) if self._start_time else 0.0
        return {
            "frames_processed": self._frames_processed,
            "events_detected": self._events_detected,
            "uptime_seconds": round(uptime, 1),
            "known_faces_count": len(self._known_faces),
            "is_running": self._running,
            "surveillance_mode": self._surveillance_mode,
        }

    def is_running(self) -> bool:
        """Trả về True nếu daemon thread đang chạy."""
        return self._running and (
            self._thread is not None and self._thread.is_alive()
        )

    # ─────────────────────────── Internal ──────────────────────────────────

    def _load_face_resources(self) -> None:
        """Load Haar cascade và build face recognizer (LBPH primary, histogram fallback)."""
        # Load Haar cascade (built-in OpenCV)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        if self._face_cascade.empty():
            logger.warning("[Bi - Mat] Khong load duoc Haar cascade!")
            self._face_cascade = None

        # Reset recognizer state
        self._lbph_recognizer = None
        self._label_to_name: dict[int, str] = {}
        self._known_faces = {}       # histogram fallback: {name: [hist, ...]}

        if not self.known_faces_dir.exists():
            return

        # Thu thập ảnh + label cho LBPH
        faces_data: list[np.ndarray] = []
        labels: list[int] = []
        label_idx = 0
        hist_db: dict[str, list] = {}  # histogram fallback database

        for person_dir in sorted(self.known_faces_dir.iterdir()):
            if not person_dir.is_dir():
                continue
            name = person_dir.name
            img_files = sorted(person_dir.glob("*.jpg")) + sorted(
                person_dir.glob("*.png")
            )
            face_count = 0
            histograms = []
            for img_file in img_files:
                img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                resized = cv2.resize(img, (64, 64))
                faces_data.append(resized)
                labels.append(label_idx)
                # Cũng tính histogram để backup
                hist = self._compute_face_histogram(resized)
                if hist is not None:
                    histograms.append(hist)
                face_count += 1

            if face_count > 0:
                self._label_to_name[label_idx] = name
                label_idx += 1
                if histograms:
                    hist_db[name] = histograms
                logger.info(
                    "[Bi - Mat] Loaded %d anh cho: %s (label=%d)",
                    face_count, name, label_idx - 1,
                )

        # Thử train LBPH (yêu cầu cv2.face từ opencv-contrib-python)
        if faces_data:
            try:
                self._lbph_recognizer = cv2.face.LBPHFaceRecognizer_create()
                self._lbph_recognizer.train(faces_data, np.array(labels))
                print(
                    f"[Bi - Mat] LBPH trained voi {len(faces_data)} anh, "
                    f"{label_idx} nguoi"
                )
            except AttributeError:
                # cv2.face không available (opencv-python không có contrib)
                logger.info(
                    "[Bi - Mat] cv2.face khong co — dung histogram fallback"
                )
                self._lbph_recognizer = None
                self._known_faces = hist_db  # dùng histogram fallback

        if self._label_to_name or self._known_faces:
            names = list(self._label_to_name.values()) or list(self._known_faces.keys())
            print(f"[Bi - Mat] Face database: {names}")
        else:
            print("[Bi - Mat] Chua co khuon mat nao duoc dang ky")

    def _compute_face_histogram(self, gray_img: np.ndarray) -> np.ndarray | None:
        """Tính histogram chuẩn hóa của ảnh grayscale."""
        try:
            resized = cv2.resize(gray_img, (64, 64))
            hist = cv2.calcHist([resized], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            return hist
        except Exception:
            return None

    def _recognize_face(self, face_roi_gray: np.ndarray) -> tuple[str, float]:
        """
        Nhận diện khuôn mặt. Ưu tiên LBPH (cv2.face), fallback histogram.

        Returns:
            (name, confidence) — name="stranger" nếu không khớp.
        """
        resized = cv2.resize(face_roi_gray, (64, 64))

        # Tầng 1: LBPH (nếu available — cần opencv-contrib-python)
        if self._lbph_recognizer is not None and self._label_to_name:
            try:
                label, confidence = self._lbph_recognizer.predict(resized)
                # LBPH: confidence thấp hơn = giống hơn (distance metric)
                # Threshold: < 80 = nhận ra, >= 80 = stranger
                if confidence < 80:
                    name = self._label_to_name.get(label, "stranger")
                    similarity = max(0.0, (100.0 - confidence) / 100.0)
                    return name, similarity
                else:
                    return "stranger", 0.0
            except Exception as e:
                logger.debug("[Bi - Mat] LBPH predict loi: %s — fallback histogram", e)

        # Tầng 2: Histogram fallback
        if not self._known_faces:
            return "stranger", 0.0

        query_hist = self._compute_face_histogram(resized)
        if query_hist is None:
            return "stranger", 0.0

        best_name = "stranger"
        best_score = -1.0

        for name, histograms in self._known_faces.items():
            for ref_hist in histograms:
                score = cv2.compareHist(
                    query_hist, ref_hist, cv2.HISTCMP_CORREL
                )
                if score > best_score:
                    best_score = score
                    best_name = (
                        name if score >= self._FACE_SIMILARITY_THRESHOLD else "stranger"
                    )

        return best_name, best_score

    def _vision_loop(self) -> None:
        """Vòng lặp chính chạy trong daemon thread."""
        # Mở camera (CAP_DSHOW tránh log lỗi MSMF trên Windows)
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            logger.warning(
                "[Bi - Mắt] Không mở được camera (index=%d). "
                "EyeVision chạy ở chế độ no-camera.",
                self.camera_index,
            )
            print(
                f"[Bi - Mắt] ⚠️ Không tìm thấy camera (index={self.camera_index}). "
                "Bỏ qua vision."
            )
            self._running = False
            return

        # Cấu hình camera
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, 20)

        frame_count = 0
        writer: cv2.VideoWriter | None = None
        clip_path: str | None = None
        _last_frame_error_log = 0.0
        _FRAME_ERROR_LOG_INTERVAL = 10.0

        print(f"[Bi - Mắt] Camera index={self.camera_index} đã kết nối.")

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                _now = time.time()
                if _now - _last_frame_error_log > _FRAME_ERROR_LOG_INTERVAL:
                    _last_frame_error_log = _now
                    logger.warning("[Bi - Mắt] Mất frame từ camera — bỏ qua (log mỗi 10s)")
                time.sleep(0.05)
                continue

            # Resize để đồng nhất xử lý
            frame = cv2.resize(frame, (self._FRAME_WIDTH, self._FRAME_HEIGHT))
            self._frames_processed += 1
            frame_count += 1

            # Lưu vào pre-event buffer (bản copy để tránh mutation)
            self._pre_buffer.append(frame.copy())

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            event_type: str | None = None

            # ── Nhánh 1: Motion detection (luôn chạy) ──────────────────
            if self._surveillance_mode:
                fg_mask = self._bg_subtractor.apply(frame)
                contours, _ = cv2.findContours(
                    fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                for cnt in contours:
                    if cv2.contourArea(cnt) > self._MOTION_THRESHOLD:
                        event_type = "motion"
                        break

            # ── Nhánh 2: Face detection (mỗi _FACE_INTERVAL frame) ────
            if frame_count % self._FACE_INTERVAL == 0 and self._face_cascade is not None:
                faces = self._face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(60, 60),
                )
                for (x, y, w, h) in faces:
                    face_roi = gray[y : y + h, x : x + w]
                    name, score = self._recognize_face(face_roi)
                    if name == "stranger":
                        # Stranger quan trọng hơn motion
                        event_type = "stranger"
                    else:
                        # Nhận ra thành viên — gọi callback với tên người
                        self._events_detected += 1
                        if self.on_event_callback:
                            try:
                                self.on_event_callback("known_face", name)
                            except Exception as e:
                                logger.error("[Bi - Mắt] callback lỗi: %s", e)
                    break  # chỉ xử lý face đầu tiên mỗi frame

            # ── Nhánh 3: Clip recording ────────────────────────────────
            if self._recording:
                if writer is not None:
                    writer.write(frame)
                self._current_clip_frames.append(frame.copy())
                self._post_frames_remaining -= 1

                if self._post_frames_remaining <= 0:
                    # Kết thúc ghi clip
                    if writer is not None:
                        writer.release()
                        writer = None
                    self._recording = False
                    saved_path = clip_path
                    event = self._current_event_type
                    self._current_clip_frames = []
                    self._events_detected += 1
                    print(
                        f"[Bi - Mắt] Clip đã lưu: {saved_path} (sự kiện: {event})"
                    )
                    if self.on_event_callback:
                        try:
                            self.on_event_callback(event, saved_path)
                        except Exception as e:
                            logger.error("[Bi - Mắt] callback lỗi: %s", e)

            elif event_type in ("motion", "stranger") and self._surveillance_mode:
                # Bắt đầu ghi clip mới
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clip_filename = f"{timestamp}_{event_type}.mp4"
                clip_path = str(self.clips_dir / clip_filename)

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                try:
                    writer = cv2.VideoWriter(
                        clip_path, fourcc, 20.0,
                        (self._FRAME_WIDTH, self._FRAME_HEIGHT)
                    )
                    if not writer.isOpened():
                        raise IOError("VideoWriter không mở được")

                    # Ghi pre-buffer (5s trước sự kiện)
                    for pre_frame in list(self._pre_buffer):
                        writer.write(pre_frame)

                    self._recording = True
                    self._post_frames_remaining = self._POST_EVENT_FRAMES
                    self._current_event_type = event_type
                    print(
                        f"[Bi - Mắt] Bắt đầu ghi clip: {clip_filename} ({event_type})"
                    )

                except Exception as e:
                    logger.warning("[Bi - Mắt] Không ghi được clip: %s", e)
                    if writer:
                        writer.release()
                        writer = None

            # Nhỏ sleep để tránh chiếm 100% CPU
            time.sleep(0.01)

        # Cleanup
        if writer is not None:
            writer.release()
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None



# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== EyeVision standalone test ===")

    eye = EyeVision(camera_index=0, on_event_callback=lambda e, p: print(f"Event: {e} | {p}"))
    eye.set_surveillance_mode(True)
    eye.start()

    print("Đang chạy 10 giây... (Ctrl+C để dừng sớm)")
    try:
        for i in range(10):
            time.sleep(1)
            print(f"[{i+1}s] Stats:", eye.get_stats())
    except KeyboardInterrupt:
        pass

    eye.stop()
    print("Đã dừng. Stats cuối:", eye.get_stats())
