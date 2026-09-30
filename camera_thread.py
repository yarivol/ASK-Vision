import os
import sys
import time
from collections import deque
from datetime import datetime, time as dt_time

import cv2
from PyQt5.QtCore import QThread, pyqtSignal

from motion_detector import MotionDetector


class CameraThread(QThread):
    frame_ready = pyqtSignal(int, object, bool)
    status_changed = pyqtSignal(int, str)
    recording_status = pyqtSignal(int, bool)

    def __init__(
        self,
        cam_id,
        name,
        url,
        threshold=25,
        min_area=500,
        pre_record=3,
        post_record=5,
        detection_enabled=True,
        recording_mode="motion",
        recording_settings=None,
    ):
        super().__init__()
        self.cam_id = cam_id
        self.name = name
        self.url = url
        self.threshold = threshold
        self.min_area = min_area
        self.pre_record = pre_record
        self.post_record = post_record
        self.detection_enabled = detection_enabled
        self.recording_mode = recording_mode
        self.recording_settings = recording_settings or {}
        self.running = True
        self.detector = MotionDetector(threshold, min_area)
        self.cap = None
        self.writer = None
        self.recording = False
        self.last_motion_time = 0
        self.fps = 20.0
        self.pre_buffer = deque()
        self.last_status = None
        self.storage_blocked = False

    def run(self):
        self.cap = self.create_capture()
        if not self.cap or not self.cap.isOpened():
            if self.cap:
                self.cap.release()
                self.cap = None
            self.emit_status("ОТКЛЮЧЕНА")
            return

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        self.fps = self.get_capture_fps()
        self.pre_buffer = deque(maxlen=max(int(self.pre_record * self.fps), 1))

        reconnect_delay = 1.0
        while self.running:
            if self.cap is None:
                self.emit_status("ОТКЛЮЧЕНА")
                time.sleep(reconnect_delay)
                if not self.running:
                    break
                candidate = self.create_capture()
                if candidate and candidate.isOpened():
                    self.cap = candidate
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
                    reconnect_delay = 1.0
                else:
                    if candidate:
                        candidate.release()
                    reconnect_delay = min(reconnect_delay * 2, 10.0)
                continue

            ret, frame = self.cap.read()
            if not ret:
                self.stop_recording()
                self.cap.release()
                self.cap = None
                continue

            self.emit_status("АКТИВНА")

            preview_frame = frame.copy()
            recording_frame = frame.copy()
            motion = False
            boxes = []

            if self.detection_enabled:
                motion, boxes = self.detector.detect(frame)
                for x, y, w, h in boxes:
                    cv2.rectangle(preview_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            self.frame_ready.emit(self.cam_id, preview_frame, motion)
            self.buffer_frame(recording_frame)

            current_time = time.time()
            allowed_to_record = self.is_recording_allowed()
            if self.recording_mode == "constant":
                if not allowed_to_record:
                    self.stop_recording()
                elif self.storage_blocked and not self.recording:
                    self.emit_status("ЛИМИТ АРХИВА")
                elif not self.recording:
                    self.start_recording(recording_frame)
                else:
                    self.writer.write(recording_frame)
            else:
                if not allowed_to_record:
                    self.stop_recording()
                elif self.storage_blocked and not self.recording:
                    self.emit_status("ЛИМИТ АРХИВА")
                elif motion and not self.recording:
                    self.start_recording(recording_frame)
                    self.last_motion_time = current_time
                elif self.recording:
                    if motion:
                        self.last_motion_time = current_time
                    self.writer.write(recording_frame)
                    if not motion and current_time - self.last_motion_time > self.post_record:
                        self.stop_recording()

            self.msleep(max(int(1000 / max(self.fps, 1)), 30))

        if self.cap:
            self.cap.release()
            self.cap = None
        self.stop_recording()

    def create_capture(self):
        url_str = str(self.url).strip()
        if url_str == "0" or url_str.isdigit():
            camera_index = int(url_str)
            if sys.platform.startswith("win"):
                return cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if sys.platform.startswith("linux") and hasattr(cv2, "CAP_V4L2"):
                return cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
            return cv2.VideoCapture(camera_index)
        return cv2.VideoCapture(url_str)

    def emit_status(self, status):
        if self.last_status == status:
            return
        self.last_status = status
        self.status_changed.emit(self.cam_id, status)

    def get_capture_fps(self):
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 1 or fps > 120:
            return 20.0
        return fps

    def buffer_frame(self, frame):
        if self.recording or self.recording_mode != "motion" or self.pre_record <= 0:
            return
        self.pre_buffer.append(frame.copy())

    def is_recording_allowed(self):
        schedule_enabled = self.recording_settings.get("schedule_enabled", False)
        if not schedule_enabled:
            return True

        days = self.recording_settings.get("days", [0, 1, 2, 3, 4, 5, 6])
        now = datetime.now()
        if now.weekday() not in days:
            return False

        start = self.parse_time(self.recording_settings.get("start_time", "00:00"))
        end = self.parse_time(self.recording_settings.get("end_time", "23:59"))
        if start is None or end is None:
            return True

        current = now.time()
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def parse_time(self, value):
        try:
            hours, minutes = map(int, str(value).split(":"))
            return dt_time(hours, minutes)
        except (ValueError, TypeError):
            return None

    def get_archive_files(self):
        if not os.path.exists("videos"):
            return []

        files = []
        for name in os.listdir("videos"):
            path = os.path.join("videos", name)
            if os.path.isfile(path) and name.lower().endswith(".mp4"):
                files.append(path)
        return files

    def get_archive_size_bytes(self):
        total = 0
        for path in self.get_archive_files():
            try:
                total += os.path.getsize(path)
            except OSError:
                continue
        return total

    def enforce_storage_policy(self):
        limit_gb = self.recording_settings.get("disk_limit_gb", 0)
        overwrite = self.recording_settings.get("overwrite_disk", True)
        if not limit_gb or limit_gb <= 0:
            self.storage_blocked = False
            return True

        limit_bytes = int(limit_gb * 1024 * 1024 * 1024)
        current_size = self.get_archive_size_bytes()
        if current_size < limit_bytes:
            self.storage_blocked = False
            return True

        if not overwrite:
            self.storage_blocked = True
            return False

        files = sorted(self.get_archive_files(), key=lambda path: os.path.getmtime(path))
        for path in files:
            if current_size < limit_bytes:
                break
            try:
                current_size -= os.path.getsize(path)
                os.remove(path)
            except OSError:
                continue

        self.storage_blocked = current_size >= limit_bytes
        return current_size < limit_bytes

    def start_recording(self, frame):
        if not self.enforce_storage_policy():
            self.emit_status("ЛИМИТ АРХИВА")
            return

        self.recording = True
        self.recording_status.emit(self.cam_id, True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"videos/{self.name}_{timestamp}.mp4"
        os.makedirs("videos", exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(filename, fourcc, self.fps, (frame.shape[1], frame.shape[0]))

        buffered_frames = list(self.pre_buffer) if self.pre_record > 0 else []
        if not buffered_frames:
            buffered_frames = [frame]
        for buffered_frame in buffered_frames:
            self.writer.write(buffered_frame)
        self.pre_buffer.clear()

        from database import get_db

        conn = get_db()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO events (camera_name, timestamp, file_path, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                self.name,
                datetime.now().isoformat(),
                filename,
                "Постоянная запись" if self.recording_mode == "constant" else "Обнаружено движение",
            ),
        )
        conn.commit()
        conn.close()

    def stop_recording(self):
        if self.writer:
            self.writer.release()
            self.writer = None
        if self.recording:
            self.recording = False
            self.recording_status.emit(self.cam_id, False)

    def stop(self):
        self.running = False
        self.wait()
