from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QPushButton, QLabel, QListWidget, QGridLayout, QTableWidget,
                             QTableWidgetItem, QDialog, QFormLayout, QLineEdit, QSpinBox,
                             QMessageBox, QStatusBar, QCheckBox, QComboBox, QScrollArea, QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
import cv2
import os
import csv
from camera_thread import CameraThread
from database import init_db, get_db
from config import load_cameras, save_cameras


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход в ASK-Vision")
        self.setFixedSize(360, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)

        title = QLabel("ASK-Vision")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.username = QLineEdit("admin")
        self.password = QLineEdit("admin")
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("Логин:", self.username)
        form.addRow("Пароль:", self.password)
        layout.addLayout(form)

        btn = QPushButton("Войти в систему")
        btn.clicked.connect(self.try_login)
        layout.addWidget(btn)

        self.accepted = False

    def try_login(self):
        if self.username.text() == "admin" and self.password.text() == "admin":
            self.accepted = True
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка входа", "Неверный логин или пароль")


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("О создателе")
        self.setFixedSize(380, 170)
        layout = QVBoxLayout(self)
        info = QLabel("<b>Ярцев Иван Олегович</b><br><br>Группа ДИ-35<br>АТТ")
        info.setFont(QFont("Arial", 14))
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class VideoPlayerDialog(QDialog):
    def __init__(self, video_path):
        super().__init__()
        self.setWindowTitle("Просмотр записи")
        self.setMinimumSize(900, 620)
        self.cap = cv2.VideoCapture(video_path)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.close)
        layout.addWidget(btn)
        self.timer.start(33)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qimg).scaled(self.label.size(), Qt.KeepAspectRatio))

    def closeEvent(self, event):
        self.timer.stop()
        self.cap.release()
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ASK-Vision v1.0 — Система видеонаблюдения")
        self.resize(1680, 980)

        icon_path = "images/ask_vision_icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        init_db()
        self.threads = {}
        self.camera_labels = {}
        self.current_cameras = load_cameras()
        self.grid_cols = 2

        self.init_ui()
        self.load_existing_cameras()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        btn_add = QPushButton("➕ Добавить камеру")
        btn_add.clicked.connect(self.add_camera_dialog)
        btn_delete = QPushButton("🗑 Удалить камеру")
        btn_delete.clicked.connect(self.delete_selected_camera)
        btn_settings = QPushButton("⚙ Настройки камеры")
        btn_settings.clicked.connect(self.open_camera_settings)
        btn_about = QPushButton("ℹ О создателе")
        btn_about.clicked.connect(self.show_about)
        btn_grid = QPushButton("Сетка 2×2 / 3×3")
        btn_grid.clicked.connect(self.change_grid)
        btn_toggle = QPushButton("⏯ Все камеры")
        btn_toggle.clicked.connect(self.toggle_all_cameras)
        btn_restart = QPushButton("🔄 Перезапустить все камеры")
        btn_restart.clicked.connect(self.restart_all_cameras)
        btn_export = QPushButton("📤 Экспорт CSV")
        btn_export.clicked.connect(self.export_events_csv)

        top_bar.addWidget(btn_add)
        top_bar.addWidget(btn_delete)
        top_bar.addWidget(btn_settings)
        top_bar.addWidget(btn_grid)
        top_bar.addWidget(btn_toggle)
        top_bar.addWidget(btn_restart)
        top_bar.addWidget(btn_export)
        top_bar.addStretch()
        top_bar.addWidget(btn_about)
        main_layout.addLayout(top_bar)

        tabs = QTabWidget()
        main_layout.addWidget(tabs, 1)

        # Live View
        live_tab = QWidget()
        live_layout = QHBoxLayout(live_tab)
        self.camera_list = QListWidget()
        self.camera_list.setMaximumWidth(280)
        live_layout.addWidget(self.camera_list)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_widget = QWidget()
        self.video_grid = QGridLayout(grid_widget)
        scroll.setWidget(grid_widget)
        live_layout.addWidget(scroll, 1)
        tabs.addTab(live_tab, "📹 Live View")

        # Журнал событий
        events_tab = QWidget()
        events_layout = QVBoxLayout(events_tab)
        self.events_table = QTableWidget(0, 4)
        self.events_table.setHorizontalHeaderLabels(["Время", "Камера", "Событие", "Файл"])
        self.events_table.cellDoubleClicked.connect(self.play_selected_event)
        events_layout.addWidget(self.events_table)

        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("🔄 Обновить журнал")
        btn_refresh.clicked.connect(self.load_events)
        btn_clear = QPushButton("🗑 Очистить журнал")
        btn_clear.clicked.connect(self.clear_events_log)
        btn_clear.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        btn_play = QPushButton("▶ Воспроизвести выбранное")
        btn_play.clicked.connect(self.play_selected_event)

        btn_layout.addWidget(btn_refresh)
        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_play)
        events_layout.addLayout(btn_layout)
        tabs.addTab(events_tab, "📋 Журнал событий")

        # Просмотр записей
        player_tab = QWidget()
        player_layout = QVBoxLayout(player_tab)
        self.recordings_list = QListWidget()
        player_layout.addWidget(self.recordings_list)
        btn_load = QPushButton("Загрузить список записей")
        btn_load.clicked.connect(self.load_recordings)
        player_layout.addWidget(btn_load)
        btn_play_rec = QPushButton("▶ Воспроизвести")
        btn_play_rec.clicked.connect(self.play_recording_from_list)
        player_layout.addWidget(btn_play_rec)
        tabs.addTab(player_tab, "📼 Просмотр записей")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово к работе")

        # Горячие клавиши
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        QShortcut(QKeySequence("F5"), self, self.load_events)
        QShortcut(QKeySequence("Esc"), self, self.close)
        QShortcut(QKeySequence("Ctrl+R"), self, self.restart_all_cameras)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

    def show_about(self):
        AboutDialog().exec_()

    def clear_events_log(self):
        reply = QMessageBox.question(self, "Очистка журнала", 
                                     "Вы действительно хотите удалить ВЕСЬ журнал событий?\n\nЭто действие нельзя отменить!",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = get_db()
            c = conn.cursor()
            c.execute("DELETE FROM events")
            conn.commit()
            conn.close()
            self.load_events()
            self.statusBar().showMessage("Журнал событий полностью очищен", 5000)

    def restart_all_cameras(self):
        self.toggle_all_cameras()
        self.load_existing_cameras()
        self.statusBar().showMessage("Все камеры перезапущены", 3000)

    def change_grid(self):
        self.grid_cols = 3 if self.grid_cols == 2 else 2
        self.rebuild_grid()

    def rebuild_grid(self):
        for i in reversed(range(self.video_grid.count())):
            w = self.video_grid.itemAt(i).widget()
            if w: w.setParent(None)
        for idx, cam_id in enumerate(list(self.camera_labels.keys())):
            row = idx // self.grid_cols
            col = idx % self.grid_cols
            self.video_grid.addWidget(self.camera_labels[cam_id], row, col)

    def toggle_all_cameras(self):
        if self.threads:
            for t in list(self.threads.values()):
                t.stop()
            self.threads.clear()
            self.statusBar().showMessage("Все камеры остановлены", 2000)
        else:
            self.load_existing_cameras()

    def export_events_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт журнала", "", "CSV (*.csv)")
        if not path: return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM events")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Камера", "Время", "Файл", "Описание"])
            writer.writerows(c.fetchall())
        conn.close()

    def load_existing_cameras(self):
        for cam in self.current_cameras:
            self.add_camera_to_ui(cam)

    def add_camera_to_ui(self, cam):
        self.camera_list.addItem(f"🟢 {cam['name']}")
        label = QLabel()
        label.setMinimumSize(640, 360)
        label.setStyleSheet("background: #111; border: 2px solid #444;")
        label.setAlignment(Qt.AlignCenter)
        self.camera_labels[cam['id']] = label
        self.rebuild_grid()

        thread = CameraThread(
            cam['id'], cam['name'], cam['url'],
            cam.get('threshold', 25), cam.get('min_area', 500),
            cam.get('pre_record', 3), cam.get('post_record', 5),
            cam.get('detection_enabled', True),
            cam.get('recording_mode', 'motion')
        )
        thread.frame_ready.connect(self.update_frame)
        thread.status_changed.connect(self.update_camera_status)
        thread.start()
        self.threads[cam['id']] = thread

    def update_frame(self, cam_id, frame, motion):
        if cam_id not in self.camera_labels: return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888)
        self.camera_labels[cam_id].setPixmap(QPixmap.fromImage(qimg).scaled(640, 360, Qt.KeepAspectRatio))

    def update_camera_status(self, cam_id, status):
        self.status_bar.showMessage(f"Камера {cam_id}: {status}")

    def add_camera_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить камеру")
        form = QFormLayout(dialog)

        name = QLineEdit("Новая камера")
        url = QLineEdit("0")
        thresh = QSpinBox(); thresh.setValue(25)
        area = QSpinBox(); area.setValue(500)
        pre = QSpinBox(); pre.setValue(3)
        post = QSpinBox(); post.setValue(5)
        mode = QComboBox()
        mode.addItems(["Только по движению", "Постоянная запись"])
        detect = QCheckBox("Включить детекцию"); detect.setChecked(True)

        form.addRow("Название:", name)
        form.addRow("URL / 0 = веб-камера:", url)
        form.addRow("Порог детекции:", thresh)
        form.addRow("Мин. площадь:", area)
        form.addRow("Предзапись (сек):", pre)
        form.addRow("Постзапись (сек):", post)
        form.addRow("Режим записи:", mode)
        form.addRow("", detect)

        btn = QPushButton("Добавить")
        btn.clicked.connect(lambda: self.save_new_camera(dialog, name.text(), url.text(),
                                                         thresh.value(), area.value(), pre.value(),
                                                         post.value(), mode.currentText(), detect.isChecked()))
        form.addWidget(btn)
        dialog.exec_()

    def save_new_camera(self, dialog, name, url, thresh, area, pre, post, mode_text, detect):
        new_id = max([c['id'] for c in self.current_cameras], default=-1) + 1
        rec_mode = "constant" if "Постоянная" in mode_text else "motion"
        cam = {
            "id": new_id, "name": name, "url": url,
            "threshold": thresh, "min_area": area,
            "pre_record": pre, "post_record": post,
            "detection_enabled": detect, "recording_mode": rec_mode
        }
        self.current_cameras.append(cam)
        save_cameras(self.current_cameras)
        self.add_camera_to_ui(cam)
        dialog.accept()

    def delete_selected_camera(self):
        row = self.camera_list.currentRow()
        if row < 0: return
        cam = self.current_cameras[row]
        if QMessageBox.question(self, "Удалить?", f"Удалить {cam['name']}?") == QMessageBox.Yes:
            if cam['id'] in self.threads:
                self.threads[cam['id']].stop()
                del self.threads[cam['id']]
            if cam['id'] in self.camera_labels:
                self.camera_labels[cam['id']].deleteLater()
                del self.camera_labels[cam['id']]
            del self.current_cameras[row]
            save_cameras(self.current_cameras)
            self.camera_list.takeItem(row)
            self.rebuild_grid()

    def open_camera_settings(self):
        row = self.camera_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Внимание", "Выберите камеру в списке")
            return

        cam = self.current_cameras[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Настройки: {cam['name']}")
        form = QFormLayout(dialog)

        thresh = QSpinBox()
        thresh.setValue(cam.get('threshold', 25))
        area = QSpinBox()
        area.setRange(100, 50000)
        area.setValue(cam.get('min_area', 500))
        pre = QSpinBox()
        pre.setValue(cam.get('pre_record', 3))
        post = QSpinBox()
        post.setValue(cam.get('post_record', 5))

        mode = QComboBox()
        mode.addItems(["Только по движению", "Постоянная запись"])
        mode.setCurrentText("Постоянная запись" if cam.get('recording_mode') == "constant" else "Только по движению")

        detect = QCheckBox("Включить детекцию движения")
        detect.setChecked(cam.get('detection_enabled', True))

        form.addRow("Порог детекции:", thresh)
        form.addRow("Мин. площадь:", area)
        form.addRow("Предзапись (сек):", pre)
        form.addRow("Постзапись (сек):", post)
        form.addRow("Режим записи:", mode)
        form.addRow("", detect)

        btn = QPushButton("Сохранить")
        btn.clicked.connect(lambda: self.save_camera_settings(
            dialog, row, thresh.value(), area.value(), pre.value(), post.value(),
            mode.currentText(), detect.isChecked()
        ))
        form.addWidget(btn)
        dialog.exec_()

    def save_camera_settings(self, dialog, row, thresh, area, pre, post, mode_text, detect):
        rec_mode = "constant" if "Постоянная" in mode_text else "motion"

        self.current_cameras[row]['threshold'] = thresh
        self.current_cameras[row]['min_area'] = area
        self.current_cameras[row]['pre_record'] = pre
        self.current_cameras[row]['post_record'] = post
        self.current_cameras[row]['detection_enabled'] = detect
        self.current_cameras[row]['recording_mode'] = rec_mode

        save_cameras(self.current_cameras)

        cam = self.current_cameras[row]
        if cam['id'] in self.threads:
            self.threads[cam['id']].stop()
            del self.threads[cam['id']]

        thread = CameraThread(cam['id'], cam['name'], cam['url'], thresh, area, pre, post, detect, rec_mode)
        thread.frame_ready.connect(self.update_frame)
        thread.status_changed.connect(self.update_camera_status)
        thread.start()
        self.threads[cam['id']] = thread

        dialog.accept()
        self.status_bar.showMessage("Настройки сохранены")

    def load_events(self):
        self.events_table.setRowCount(0)
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT timestamp, camera_name, description, file_path FROM events ORDER BY timestamp DESC")
        for data in c.fetchall():
            r = self.events_table.rowCount()
            self.events_table.insertRow(r)
            for col, val in enumerate(data):
                self.events_table.setItem(r, col, QTableWidgetItem(str(val)))
        conn.close()

    def play_selected_event(self):
        row = self.events_table.currentRow()
        if row < 0: return
        path = self.events_table.item(row, 3).text()
        if os.path.exists(path):
            VideoPlayerDialog(path).exec_()

    def load_recordings(self):
        self.recordings_list.clear()
        if os.path.exists("videos"):
            for f in sorted(os.listdir("videos"), reverse=True):
                if f.endswith(".mp4"):
                    self.recordings_list.addItem(f)

    def play_recording_from_list(self):
        item = self.recordings_list.currentItem()
        if item:
            VideoPlayerDialog(os.path.join("videos", item.text())).exec_()

    def closeEvent(self, event):
        for t in self.threads.values():
            t.stop()
        event.accept()


# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec_() == QDialog.Accepted and login.accepted:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)