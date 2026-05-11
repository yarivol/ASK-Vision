from PyQt5.QtCore import QThread, pyqtSignal
import cv2
import time
import os
from datetime import datetime
from motion_detector import MotionDetector

class CameraThread(QThread):
    frame_ready = pyqtSignal(int, object, bool)
    status_changed = pyqtSignal(int, str)
    recording_status = pyqtSignal(int, bool)   # новый сигнал

    def __init__(self, cam_id, name, url, threshold=25, min_area=500,
                 pre_record=3, post_record=5, detection_enabled=True,
                 recording_mode="motion"):   # "motion" или "constant"
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
        self.running = True
        self.detector = MotionDetector(threshold, min_area)
        self.cap = None
        self.writer = None
        self.recording = False
        self.last_motion_time = 0

    def run(self):
        url_str = str(self.url).strip()
        if url_str == "0" or url_str.isdigit():
            self.cap = cv2.VideoCapture(int(url_str), cv2.CAP_DSHOW)
        else:
            self.cap = cv2.VideoCapture(url_str)

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 5)

        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                self.status_changed.emit(self.cam_id, "ОТКЛЮЧЕНА")
                time.sleep(2)
                continue

            processed_frame = frame.copy()
            motion = False

            if self.detection_enabled:
                motion, boxes, processed_frame = self.detector.detect(frame)
                for x, y, w, h in boxes:
                    cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (0, 255, 0), 3)

            self.frame_ready.emit(self.cam_id, processed_frame, motion)

            current_time = time.time()

            # РЕЖИМ ПОСТОЯННОЙ ЗАПИСИ
            if self.recording_mode == "constant":
                if not self.recording:
                    self.start_recording(processed_frame)
                else:
                    self.writer.write(processed_frame)
            else:
                # РЕЖИМ ТОЛЬКО ПО ДВИЖЕНИЮ
                if motion and not self.recording:
                    self.start_recording(processed_frame)
                    self.last_motion_time = current_time
                elif self.recording:
                    self.writer.write(processed_frame)
                    if not motion and (current_time - self.last_motion_time > self.post_record):
                        self.stop_recording()

            self.msleep(30)

        if self.cap:
            self.cap.release()
        if self.writer:
            self.writer.release()

    def start_recording(self, frame):
        self.recording = True
        self.recording_status.emit(self.cam_id, True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"videos/{self.name}_{timestamp}.mp4"
        os.makedirs("videos", exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(filename, fourcc, 20.0, (frame.shape[1], frame.shape[0]))

        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO events (camera_name, timestamp, file_path, description) VALUES (?,?,?,?)",
                  (self.name, datetime.now().isoformat(), filename, 
                   "Постоянная запись" if self.recording_mode == "constant" else "Обнаружено движение"))
        conn.commit()
        conn.close()

    def stop_recording(self):
        if self.writer:
            self.writer.release()
            self.writer = None
        self.recording = False
        self.recording_status.emit(self.cam_id, False)

    def stop(self):
        self.running = False
        self.wait()