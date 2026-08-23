import csv
import os
import shutil
import sys

if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    for env_name in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_PLUGIN_PATH", "QT_QPA_FONTDIR"):
        env_value = os.environ.get(env_name, "")
        if "cv2" in env_value.lower():
            os.environ.pop(env_name, None)

from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont, QIcon, QImage, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSlider,
    QSpinBox,
    QStatusBar,
    QSystemTrayIcon,
    QTimeEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import cv2

from camera_thread import CameraThread
from config import load_cameras, save_cameras
from database import (
    PERMISSION_LABELS,
    authenticate_user,
    check_database_health,
    create_user,
    delete_user,
    fetch_usernames,
    fetch_users,
    get_default_permissions,
    get_user_by_username,
    get_user_by_id,
    init_db,
    update_user,
    get_db,
)
from settings import load_app_settings, save_app_settings, DEFAULT_SETTINGS, sync_autostart

STYLE_OPTIONS = {
    "Модерн": "modern",
    "Олд": "old",
}

THEME_OPTIONS = {
    "Тёмная": "dark",
    "Светлая": "light",
}


MODERN_DARK_STYLESHEET = """
QWidget {
    background-color: #16181d;
    color: #ecf1f8;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #111318;
}
QLabel#titleLabel {
    font-size: 26px;
    font-weight: 700;
    color: #f4f7fb;
}
QLabel#hintLabel {
    color: #9eabc2;
}
QLabel#badgeLabel {
    background: #222834;
    border: 1px solid #334156;
    border-radius: 12px;
    padding: 6px 10px;
    font-weight: 600;
}
QPushButton {
    background-color: #273244;
    border: 1px solid #3d4e68;
    border-radius: 8px;
    padding: 8px 14px;
}
QPushButton:hover {
    background-color: #30405a;
}
QPushButton:pressed {
    background-color: #1e2938;
}
QPushButton:disabled {
    color: #71809a;
    background-color: #1b202a;
    border-color: #2a3342;
}
QLineEdit, QComboBox, QSpinBox, QListWidget, QTableWidget, QScrollArea, QSlider {
    background-color: #1d232d;
    border: 1px solid #314159;
    border-radius: 8px;
    padding: 8px 10px;
}
QLineEdit, QComboBox, QSpinBox {
    min-height: 24px;
    selection-background-color: #4e79b9;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6f9ce0;
    background-color: #202833;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background-color: #1d232d;
    color: #ecf1f8;
    border: 1px solid #314159;
    selection-background-color: #30405a;
}
QTabWidget::pane {
    border: 1px solid #314159;
    background: #131820;
    border-radius: 10px;
}
QTabBar::tab {
    background: #1d232d;
    border: 1px solid #314159;
    padding: 9px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: #2c3b53;
}
QHeaderView::section {
    background-color: #222834;
    color: #eff4fb;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #314159;
}
QStatusBar {
    background: #111318;
    color: #a9b7cd;
}
QMenu {
    background-color: #1a2029;
    color: #eff4fb;
    border: 1px solid #314159;
}
QMenu::item:selected {
    background-color: #30405a;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #161b22;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #40506d;
    border-radius: 6px;
    min-height: 28px;
    min-width: 28px;
}
"""


MODERN_LIGHT_STYLESHEET = """
QWidget {
    background-color: #eef2f7;
    color: #1d2a3b;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #f8fbff;
}
QLabel#titleLabel {
    font-size: 26px;
    font-weight: 700;
    color: #1b2b3f;
}
QLabel#hintLabel {
    color: #5f7187;
}
QLabel#badgeLabel {
    background: #dde7f4;
    border: 1px solid #b7c8dd;
    border-radius: 12px;
    padding: 6px 10px;
    font-weight: 600;
}
QPushButton {
    background-color: #d7e3f2;
    border: 1px solid #aebfd6;
    border-radius: 8px;
    padding: 8px 14px;
}
QPushButton:hover {
    background-color: #c8d9ee;
}
QPushButton:pressed {
    background-color: #b8cde7;
}
QPushButton:disabled {
    color: #76879d;
    background-color: #edf2f8;
    border-color: #d0d9e4;
}
QLineEdit, QComboBox, QSpinBox, QListWidget, QTableWidget, QScrollArea, QSlider {
    background-color: #ffffff;
    border: 1px solid #b8c6d9;
    border-radius: 8px;
    padding: 8px 10px;
}
QLineEdit, QComboBox, QSpinBox {
    min-height: 24px;
    selection-background-color: #8eb0dc;
    selection-color: #102033;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #5d88c4;
    background-color: #fbfdff;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1d2a3b;
    border: 1px solid #b8c6d9;
    selection-background-color: #d7e3f2;
}
QTabWidget::pane {
    border: 1px solid #c1cfdf;
    background: #fefefe;
    border-radius: 10px;
}
QTabBar::tab {
    background: #e6edf7;
    border: 1px solid #c1cfdf;
    padding: 9px 16px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: #ffffff;
}
QHeaderView::section {
    background-color: #dde7f4;
    color: #1d2a3b;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #c1cfdf;
}
QStatusBar {
    background: #edf3fa;
    color: #52657d;
}
QMenu {
    background-color: #ffffff;
    color: #1d2a3b;
    border: 1px solid #c1cfdf;
}
QMenu::item:selected {
    background-color: #dde7f4;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #ebf0f6;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #b5c7dd;
    border-radius: 6px;
    min-height: 28px;
    min-width: 28px;
}
"""


OLD_DARK_STYLESHEET = """
QWidget {
    background-color: #2f2f2f;
    color: #f2f2f2;
}
QMainWindow, QDialog {
    background-color: #2f2f2f;
}
QMenuBar, QMenu, QStatusBar {
    background-color: #3a3a3a;
    color: #f2f2f2;
}
QPushButton, QComboBox, QSpinBox, QLineEdit, QListWidget, QTableWidget, QTabWidget::pane, QScrollArea {
    background-color: #404040;
    color: #f2f2f2;
    border: 1px solid #6a6a6a;
}
QPushButton:hover, QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid #8a8a8a;
}
QPushButton:pressed {
    background-color: #4d4d4d;
}
QComboBox QAbstractItemView {
    background-color: #404040;
    color: #f2f2f2;
    selection-background-color: #5a5a5a;
}
QHeaderView::section {
    background-color: #3b3b3b;
    color: #f2f2f2;
    border: 1px solid #6a6a6a;
}
QTabBar::tab {
    background-color: #404040;
    color: #f2f2f2;
    border: 1px solid #6a6a6a;
    padding: 6px 10px;
}
QTabBar::tab:selected {
    background-color: #4c4c4c;
}
QScrollBar:vertical, QScrollBar:horizontal {
    background: #383838;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #6b6b6b;
    min-height: 24px;
    min-width: 24px;
}
"""


APPEARANCE_STYLESHEETS = {
    ("modern", "dark"): MODERN_DARK_STYLESHEET,
    ("modern", "light"): MODERN_LIGHT_STYLESHEET,
    ("old", "dark"): OLD_DARK_STYLESHEET,
    ("old", "light"): "",
}


def apply_appearance(app, style_name, theme_name):
    app.setStyleSheet(APPEARANCE_STYLESHEETS.get((style_name, theme_name), MODERN_DARK_STYLESHEET))


def apply_theme(app, theme_name):
    apply_appearance(app, "modern", theme_name)


def apply_dark_theme(app):
    apply_appearance(app, "modern", "dark")


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setObjectName("classicLoginDialog")
        self.setWindowTitle("Вход в ASK-Vision")
        self.setFixedSize(360, 220)
        self.accepted = False
        self.current_user = None
        self.setStyleSheet(
            """
            QDialog#classicLoginDialog,
            QDialog#classicLoginDialog QWidget {
                background-color: #ffffff;
                color: #000000;
                font-family: "Segoe UI";
                font-size: 12px;
            }
            QDialog#classicLoginDialog QLabel#loginTitle {
                font-size: 24px;
                font-weight: 700;
            }
            QDialog#classicLoginDialog QLineEdit {
                background-color: #ffffff;
                border: 1px solid #7f9db9;
                padding: 2px 4px;
                min-height: 20px;
            }
            QDialog#classicLoginDialog QLineEdit:focus {
                border: 2px solid #3399ff;
                padding: 1px 3px;
            }
            QDialog#classicLoginDialog QPushButton {
                background-color: #f0f0f0;
                color: #000000;
                border: 1px solid #3399ff;
                padding: 4px 10px;
                min-height: 22px;
            }
            QDialog#classicLoginDialog QPushButton:pressed {
                background-color: #e5e5e5;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 26, 40, 28)
        layout.setSpacing(12)

        title = QLabel("ASK-Vision")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignHCenter)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(12)

        self.username = QLineEdit("admin")
        self.username.setMinimumWidth(230)
        self.username.setFont(QFont("Segoe UI", 10))

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setMinimumWidth(230)
        self.password.setFont(QFont("Segoe UI", 10))
        self.password.returnPressed.connect(self.try_login)

        form.addRow("Логин:", self.username)
        form.addRow("Пароль:", self.password)
        layout.addLayout(form)
        layout.addSpacing(10)

        login_button = QPushButton("Войти в систему")
        login_button.clicked.connect(self.try_login)
        login_button.setDefault(True)
        login_button.setMinimumWidth(230)
        layout.addWidget(login_button)
        layout.setAlignment(login_button, Qt.AlignHCenter)
        self.password.setFocus()

    def try_login(self):
        username = self.username.text().strip()
        password = self.password.text()
        user = authenticate_user(username, password)

        if not user:
            QMessageBox.warning(self, "Ошибка входа", "Неверный логин или пароль")
            return

        self.current_user = user
        self.accepted = True
        self.accept()


class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("О создателе")
        self.setFixedSize(380, 180)

        layout = QVBoxLayout(self)
        info = QLabel("<b>Ярцев Иван Олегович</b><br><br>Группа ДИ-35<br>АТТ")
        info.setFont(QFont("Segoe UI", 13))
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        btn = QPushButton("Закрыть")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


class UserEditorDialog(QDialog):
    def __init__(self, user=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Редактирование пользователя" if user else "Создание пользователя")
        self.resize(520, 520)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.username = QLineEdit(user["username"] if user else "")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Оставьте пустым, чтобы не менять пароль" if user else "Введите пароль")

        self.role = QComboBox()
        self.role.addItems(["admin", "operator"])
        role_value = user["role"] if user else "operator"
        self.role.setCurrentText(role_value)

        form.addRow("Логин:", self.username)
        form.addRow("Пароль:", self.password)
        form.addRow("Роль:", self.role)
        layout.addLayout(form)

        rights_title = QLabel("Права доступа")
        rights_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(rights_title)

        permissions_widget = QWidget()
        permissions_layout = QGridLayout(permissions_widget)
        permissions_layout.setContentsMargins(0, 0, 0, 0)
        permissions_layout.setHorizontalSpacing(14)
        permissions_layout.setVerticalSpacing(8)

        self.permission_boxes = {}
        for index, (key, label) in enumerate(PERMISSION_LABELS.items()):
            checkbox = QCheckBox(label)
            row = index // 2
            col = index % 2
            permissions_layout.addWidget(checkbox, row, col)
            self.permission_boxes[key] = checkbox

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(permissions_widget)
        layout.addWidget(scroll, 1)

        template_buttons = QHBoxLayout()
        self.btn_fill_role = QPushButton("Шаблон по роли")
        self.btn_fill_role.clicked.connect(self.apply_role_template)
        template_buttons.addWidget(self.btn_fill_role)
        template_buttons.addStretch()
        layout.addLayout(template_buttons)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if user:
            self.set_permissions(user["permissions"])
        else:
            self.apply_role_template()

    def set_permissions(self, permissions):
        for key, checkbox in self.permission_boxes.items():
            checkbox.setChecked(bool(permissions.get(key, False)))

    def apply_role_template(self):
        self.set_permissions(get_default_permissions(self.role.currentText()))

    def validate_and_accept(self):
        username = self.username.text().strip()
        password = self.password.text()

        if not username:
            QMessageBox.warning(self, "Ошибка", "Логин не может быть пустым")
            return

        if not self.user and not password:
            QMessageBox.warning(self, "Ошибка", "Для нового пользователя нужен пароль")
            return

        self.accept()

    def get_data(self):
        permissions = {key: checkbox.isChecked() for key, checkbox in self.permission_boxes.items()}
        return {
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "role": self.role.currentText(),
            "permissions": permissions,
        }


class RecordingSettingsDialog(QDialog):
    def __init__(self, recording_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки записи")
        self.resize(520, 420)
        self.recording_settings = recording_settings

        layout = QVBoxLayout(self)
        form = QFormLayout()

        schedule = recording_settings
        self.schedule_enabled = QCheckBox("Запись по календарю")
        self.schedule_enabled.setChecked(schedule.get("schedule_enabled", False))
        form.addRow("", self.schedule_enabled)

        days_widget = QWidget()
        days_layout = QHBoxLayout(days_widget)
        days_layout.setContentsMargins(0, 0, 0, 0)
        days_layout.setSpacing(6)
        self.day_boxes = []
        day_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        enabled_days = set(schedule.get("days", [0, 1, 2, 3, 4, 5, 6]))
        for index, label in enumerate(day_labels):
            box = QCheckBox(label)
            box.setChecked(index in enabled_days)
            self.day_boxes.append(box)
            days_layout.addWidget(box)
        form.addRow("Дни:", days_widget)

        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(self._parse_time(schedule.get("start_time", "00:00")))

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(self._parse_time(schedule.get("end_time", "23:59")))

        form.addRow("Начало:", self.start_time)
        form.addRow("Конец:", self.end_time)

        self.overwrite_disk = QCheckBox("Перезаписывать архив при лимите")
        self.overwrite_disk.setChecked(recording_settings.get("overwrite_disk", True))
        self.disk_limit = QSpinBox()
        self.disk_limit.setRange(0, 10000)
        self.disk_limit.setSuffix(" ГБ")
        self.disk_limit.setValue(recording_settings.get("disk_limit_gb", 50))
        form.addRow("", self.overwrite_disk)
        form.addRow("Лимит записи:", self.disk_limit)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_cancel = QPushButton("Отмена")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)

    def _parse_time(self, value):
        parts = str(value).split(":")
        if len(parts) != 2:
            return QTime(0, 0)
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
        except ValueError:
            hours, minutes = 0, 0
        return QTime(hours, minutes)

    def get_data(self):
        days = [index for index, box in enumerate(self.day_boxes) if box.isChecked()]
        return {
            "schedule_enabled": self.schedule_enabled.isChecked(),
            "days": days,
            "start_time": self.start_time.time().toString("HH:mm"),
            "end_time": self.end_time.time().toString("HH:mm"),
            "overwrite_disk": self.overwrite_disk.isChecked(),
            "disk_limit_gb": self.disk_limit.value(),
        }


class QuickSettingsDialog(QDialog):
    def __init__(self, app_settings, current_user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки программы")
        self.resize(560, 520)
        self.app_settings = app_settings
        self.current_user = current_user
        self.parent_window = parent

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.style_combo = QComboBox()
        self.style_combo.addItems(list(STYLE_OPTIONS.keys()))
        self.style_combo.setCurrentText("Модерн" if app_settings.get("style", "modern") == "modern" else "Олд")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEME_OPTIONS.keys()))
        self.theme_combo.setCurrentText("Тёмная" if app_settings.get("theme", "dark") == "dark" else "Светлая")

        self.grid_selector = QSpinBox()
        self.grid_selector.setRange(1, 10)
        self.grid_selector.setValue(int(app_settings.get("grid_columns", 2)))
        self.grid_selector.setSuffix(" камер")

        self.autostart_enabled = QCheckBox("Автозапуск при старте системы")
        self.autostart_enabled.setChecked(bool(app_settings.get("autostart_enabled", False)))

        self.autologin_enabled = QCheckBox("Автологин")
        self.autologin_enabled.setChecked(bool(app_settings.get("autologin_enabled", False)))
        self.autologin_enabled.toggled.connect(self.update_autologin_state)

        self.autologin_user = QComboBox()
        usernames = fetch_usernames() or ["admin"]
        self.autologin_user.addItems(usernames)
        saved_user = app_settings.get("autologin_user", "admin")
        if saved_user not in usernames:
            self.autologin_user.addItem(saved_user)
        self.autologin_user.setCurrentText(saved_user)

        form.addRow("Стиль:", self.style_combo)
        form.addRow("Тема:", self.theme_combo)
        form.addRow("Сетка:", self.grid_selector)
        form.addRow("", self.autostart_enabled)
        form.addRow("", self.autologin_enabled)
        form.addRow("Пользователь:", self.autologin_user)
        layout.addLayout(form)

        self.db_status = QLabel("БД: не проверено")
        self.disk_status = QLabel("Диск: состояние не проверено")
        layout.addWidget(self.db_status)
        layout.addWidget(self.disk_status)

        quick_actions = QHBoxLayout()
        self.btn_quick_setup = QPushButton("Быстрая настройка")
        self.btn_quick_setup.clicked.connect(self.apply_quick_setup)
        quick_actions.addWidget(self.btn_quick_setup)
        quick_actions.addStretch()
        layout.addLayout(quick_actions)

        status_buttons = QHBoxLayout()
        self.btn_check_db = QPushButton("Проверить БД")
        self.btn_check_db.clicked.connect(lambda: self.refresh_db_status(show_dialog=True))
        self.btn_check_disk = QPushButton("Проверить диск")
        self.btn_check_disk.clicked.connect(lambda: self.refresh_disk_status(show_dialog=True))
        status_buttons.addWidget(self.btn_check_db)
        status_buttons.addWidget(self.btn_check_disk)
        layout.addLayout(status_buttons)

        extra_actions = QHBoxLayout()
        if self.current_user.get("role") == "admin":
            self.btn_manage_users = QPushButton("Пользователи и права")
            self.btn_manage_users.clicked.connect(self.open_user_management)
            extra_actions.addWidget(self.btn_manage_users)
        self.btn_about = QPushButton("О создателе")
        self.btn_about.clicked.connect(self.show_about)
        extra_actions.addWidget(self.btn_about)
        extra_actions.addStretch()
        layout.addLayout(extra_actions)

        logs_title = QLabel("Журнал настроек")
        logs_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(logs_title)

        self.logs_list = QListWidget()
        self.logs_list.setMinimumHeight(160)
        layout.addWidget(self.logs_list, 1)

        buttons = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_cancel = QPushButton("Отмена")
        self.btn_save.clicked.connect(self.save_and_accept)
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)

        self.update_autologin_state(self.autologin_enabled.isChecked())
        self.refresh_db_status()
        self.refresh_disk_status()
        self.add_log("Окно настроек открыто")
        self.add_log(f"Текущий пользователь: {self.current_user['username']}")
        self.add_log(
            f"Активная тема: {self.theme_combo.currentText()}, стиль: {self.style_combo.currentText()}"
        )

    def show_about(self):
        self.add_log("Открыто окно 'О создателе'")
        AboutDialog().exec_()

    def add_log(self, message):
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.logs_list.insertItem(0, f"[{timestamp}] {message}")
        while self.logs_list.count() > 100:
            self.logs_list.takeItem(self.logs_list.count() - 1)

    def save_and_accept(self):
        self.add_log("Настройки подготовлены к сохранению")
        self.accept()

    def update_autologin_state(self, enabled):
        self.autologin_user.setEnabled(bool(enabled))
        state = "включён" if enabled else "выключен"
        self.add_log(f"Автологин {state}")

    def apply_quick_setup(self):
        self.style_combo.setCurrentText("Модерн")
        self.theme_combo.setCurrentText("Тёмная")
        self.grid_selector.setValue(4)
        self.autostart_enabled.setChecked(False)
        self.autologin_enabled.setChecked(False)
        self.refresh_db_status()
        self.refresh_disk_status()
        self.add_log("Применена быстрая настройка")

    def refresh_db_status(self, show_dialog=False):
        ok, message = check_database_health()
        self.db_status.setText(message if ok else message)
        self.add_log(message)
        if show_dialog:
            title = "Проверка БД"
            details = "Проверка базы данных завершена успешно." if ok else "Проверка базы данных завершена, найдены замечания."
            QMessageBox.information(self, title, f"{details}\n\n{message}")

    def refresh_disk_status(self, show_dialog=False):
        try:
            usage = shutil.disk_usage(os.getcwd())
        except OSError:
            self.disk_status.setText("Диск: состояние недоступно")
            self.add_log("Проверка диска: состояние недоступно")
            if show_dialog:
                QMessageBox.information(
                    self,
                    "Проверка диска",
                    "Проверка диска завершена.\n\nСостояние диска сейчас недоступно, но модуль ответа работает корректно.",
                )
            return

        total_gb = usage.total / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        self.disk_status.setText(
            f"Диск: свободно {free_gb:.1f} ГБ из {total_gb:.1f} ГБ"
        )
        self.add_log(f"Проверка диска: свободно {free_gb:.1f} ГБ из {total_gb:.1f} ГБ")
        if show_dialog:
            QMessageBox.information(
                self,
                "Проверка диска",
                (
                    "Проверка диска завершена успешно.\n\n"
                    f"Свободно {free_gb:.1f} ГБ из {total_gb:.1f} ГБ."
                ),
            )

    def get_data(self):
        return {
            "style": STYLE_OPTIONS.get(self.style_combo.currentText(), "modern"),
            "theme": THEME_OPTIONS.get(self.theme_combo.currentText(), "dark"),
            "grid_columns": self.grid_selector.value(),
            "autostart_enabled": self.autostart_enabled.isChecked(),
            "autologin_enabled": self.autologin_enabled.isChecked(),
            "autologin_user": self.autologin_user.currentText().strip() or "admin",
        }

    def open_user_management(self):
        dialog = UserManagementDialog(self.current_user, self.on_current_user_updated, self)
        self.add_log("Открыто управление пользователями")
        dialog.exec_()

    def on_current_user_updated(self, updated_user):
        self.current_user = updated_user
        if self.parent_window:
            self.parent_window.refresh_current_user_context(updated_user)
        self.add_log(f"Обновлены права текущего пользователя: {updated_user['username']}")


class UserManagementDialog(QDialog):
    def __init__(self, current_user, current_user_callback=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.current_user_callback = current_user_callback
        self.setWindowTitle("Пользователи и права")
        self.resize(760, 460)

        layout = QVBoxLayout(self)

        self.users_table = QTableWidget(0, 3)
        self.users_table.setHorizontalHeaderLabels(["Логин", "Роль", "Права"])
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.users_table)

        buttons = QHBoxLayout()
        self.btn_add_user = QPushButton("Создать пользователя")
        self.btn_add_user.clicked.connect(self.create_user_dialog)
        self.btn_edit_user = QPushButton("Редактировать")
        self.btn_edit_user.clicked.connect(self.edit_selected_user)
        self.btn_delete_user = QPushButton("Удалить пользователя")
        self.btn_delete_user.clicked.connect(self.delete_selected_user_account)
        self.btn_refresh_users = QPushButton("Обновить список")
        self.btn_refresh_users.clicked.connect(self.load_users)
        buttons.addWidget(self.btn_add_user)
        buttons.addWidget(self.btn_edit_user)
        buttons.addWidget(self.btn_delete_user)
        buttons.addWidget(self.btn_refresh_users)
        layout.addLayout(buttons)

        self.load_users()

    def format_permissions_summary(self, permissions):
        enabled = [label for key, label in PERMISSION_LABELS.items() if permissions.get(key)]
        if not enabled:
            return "Нет прав"
        if len(enabled) <= 3:
            return ", ".join(enabled)
        return f"{', '.join(enabled[:3])} +{len(enabled) - 3}"

    def load_users(self):
        self.users_table.setRowCount(0)
        for user in fetch_users():
            row = self.users_table.rowCount()
            self.users_table.insertRow(row)

            username_item = QTableWidgetItem(user["username"])
            username_item.setData(Qt.UserRole, user["id"])
            self.users_table.setItem(row, 0, username_item)
            self.users_table.setItem(row, 1, QTableWidgetItem(user["role"]))
            self.users_table.setItem(row, 2, QTableWidgetItem(self.format_permissions_summary(user["permissions"])))

    def get_selected_user(self):
        row = self.users_table.currentRow()
        if row < 0:
            return None

        user_id = self.users_table.item(row, 0).data(Qt.UserRole)
        return get_user_by_id(user_id)

    def create_user_dialog(self):
        dialog = UserEditorDialog(parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.get_data()
        try:
            create_user(data["username"], data["password"], data["role"], data["permissions"])
        except Exception as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось создать пользователя: {error}")
            return

        self.load_users()
        QMessageBox.information(self, "Готово", "Пользователь создан")

    def edit_selected_user(self):
        user = self.get_selected_user()
        if not user:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        dialog = UserEditorDialog(user=user, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.get_data()
        try:
            update_user(
                user["id"],
                data["username"],
                data["role"],
                data["permissions"],
                data["password"] or None,
            )
        except Exception as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить пользователя: {error}")
            return

        self.load_users()
        if user["id"] == self.current_user["id"]:
            self.current_user = get_user_by_id(user["id"])
            if self.current_user_callback:
                self.current_user_callback(self.current_user)
        QMessageBox.information(self, "Готово", "Пользователь обновлён")

    def delete_selected_user_account(self):
        user = self.get_selected_user()
        if not user:
            QMessageBox.information(self, "Внимание", "Выберите пользователя")
            return

        if user["id"] == self.current_user["id"]:
            QMessageBox.warning(self, "Запрещено", "Нельзя удалить текущего пользователя")
            return

        if QMessageBox.question(self, "Удалить?", f"Удалить пользователя {user['username']}?") != QMessageBox.Yes:
            return

        try:
            delete_user(user["id"])
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка", str(error))
            return

        self.load_users()
        QMessageBox.information(self, "Готово", "Пользователь удалён")


class VideoPlayerDialog(QDialog):
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.setWindowTitle(f"Плеер: {os.path.basename(video_path)}")
        self.setMinimumSize(960, 680)

        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        if self.fps <= 1:
            self.fps = 25.0
        self.total_frames = max(int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)), 0)
        self.was_playing_before_seek = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        layout = QVBoxLayout(self)

        self.label = QLabel("Загрузка видео...")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumHeight(460)
        self.label.setStyleSheet("background: #090b0f; border: 1px solid #314159; border-radius: 12px;")
        layout.addWidget(self.label, 1)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, max(self.total_frames - 1, 0))
        self.position_slider.sliderPressed.connect(self.on_slider_pressed)
        self.position_slider.sliderReleased.connect(self.on_slider_released)
        layout.addWidget(self.position_slider)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.time_label)

        controls = QHBoxLayout()
        self.play_button = QPushButton("Воспроизвести")
        self.pause_button = QPushButton("Пауза")
        self.stop_button = QPushButton("Стоп")
        self.close_button = QPushButton("Закрыть")

        self.play_button.clicked.connect(self.play_video)
        self.pause_button.clicked.connect(self.pause_video)
        self.stop_button.clicked.connect(self.stop_video)
        self.close_button.clicked.connect(self.close)

        controls.addWidget(self.play_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        controls.addWidget(self.close_button)
        layout.addLayout(controls)

        if self.cap.isOpened():
            self.show_frame_at(0)
            self.play_video()
        else:
            self.label.setText("Не удалось открыть видео")

    def format_seconds(self, seconds):
        minutes = int(seconds // 60)
        sec = int(seconds % 60)
        return f"{minutes:02}:{sec:02}"

    def update_time_label(self, frame_index):
        current_seconds = frame_index / self.fps if self.fps else 0
        total_seconds = self.total_frames / self.fps if self.fps else 0
        self.time_label.setText(f"{self.format_seconds(current_seconds)} / {self.format_seconds(total_seconds)}")

    def render_frame(self, frame, slider_index):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qimg).scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(max(slider_index, 0))
        self.position_slider.blockSignals(False)
        self.update_time_label(max(slider_index, 0))

    def show_frame_at(self, frame_index):
        if not self.cap.isOpened():
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.cap.read()
        if ret:
            self.render_frame(frame, frame_index)

    def update_frame(self):
        if not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            self.pause_video()
            self.position_slider.setValue(max(self.total_frames - 1, 0))
            return

        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        self.render_frame(frame, current_frame)

    def play_video(self):
        if self.cap.isOpened():
            self.timer.start(max(int(1000 / self.fps), 20))

    def pause_video(self):
        self.timer.stop()

    def stop_video(self):
        self.pause_video()
        self.show_frame_at(0)

    def on_slider_pressed(self):
        self.was_playing_before_seek = self.timer.isActive()
        self.pause_video()

    def on_slider_released(self):
        target_frame = self.position_slider.value()
        self.show_frame_at(target_frame)
        if self.was_playing_before_seek:
            self.play_video()

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        event.accept()


class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.permissions = current_user["permissions"]
        self.app_settings = load_app_settings()
        self.current_style = self.app_settings.get("style", "modern") if self.app_settings.get("style") in STYLE_OPTIONS.values() else "modern"
        self.current_theme = self.app_settings.get("theme", "dark") if self.app_settings.get("theme") in THEME_OPTIONS.values() else "dark"
        self.recording_settings = self.app_settings.get("recording", DEFAULT_SETTINGS["recording"].copy())
        self.autostart_enabled = bool(self.app_settings.get("autostart_enabled", False))
        self.autologin_enabled = bool(self.app_settings.get("autologin_enabled", False))
        self.autologin_user = self.app_settings.get("autologin_user", "admin")
        self.force_exit = False
        self.tray_icon = None

        self.setWindowTitle("ASK-Vision v1.0 — Система видеонаблюдения")
        self.resize(1680, 980)

        icon_path = "images/ask_vision_icon.ico"
        if os.path.exists(icon_path):
            self.app_icon = QIcon(icon_path)
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = self.style().standardIcon(self.style().SP_ComputerIcon)

        init_db()
        self.threads = {}
        self.camera_labels = {}
        self.camera_items = {}
        self.current_cameras = load_cameras()
        self.grid_cols = max(1, min(10, int(self.app_settings.get("grid_columns", 2))))

        self.init_ui()
        self.apply_current_appearance()
        self.setup_tray_icon()
        self.start_all_cameras()
        self.load_events()
        self.load_recordings()
        self.apply_permissions()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(14)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.btn_add = QPushButton("Добавить камеру")
        self.btn_add.clicked.connect(self.add_camera_dialog)
        self.btn_delete = QPushButton("Удалить камеру")
        self.btn_delete.clicked.connect(self.delete_selected_camera)
        self.btn_settings = QPushButton("Настройки камеры")
        self.btn_settings.clicked.connect(self.open_camera_settings)
        self.btn_quick_settings = QPushButton("Настройки программы")
        self.btn_quick_settings.clicked.connect(self.open_quick_settings)
        self.btn_toggle = QPushButton("Все камеры")
        self.btn_toggle.clicked.connect(self.toggle_all_cameras)
        self.btn_restart = QPushButton("Перезапустить камеры")
        self.btn_restart.clicked.connect(self.restart_all_cameras)
        self.btn_export = QPushButton("Экспорт CSV")
        self.btn_export.clicked.connect(self.export_events_csv)
        self.btn_recording_settings = QPushButton("Настройки записи")
        self.btn_recording_settings.clicked.connect(self.open_recording_settings)
        self.btn_tray = QPushButton("Свернуть в трей")
        self.btn_tray.clicked.connect(self.minimize_to_tray)
        self.btn_switch_user = QPushButton("Сменить пользователя")
        self.btn_switch_user.clicked.connect(self.switch_user)
        self.grid_selector = QSpinBox()
        self.grid_selector.setRange(1, 10)
        self.grid_selector.setValue(self.grid_cols)
        self.grid_selector.setPrefix("Сетка ")
        self.grid_selector.setMinimumWidth(110)
        self.grid_selector.valueChanged.connect(self.set_grid_columns)

        for button in [
            self.btn_add,
            self.btn_delete,
            self.btn_settings,
            self.btn_quick_settings,
            self.btn_toggle,
            self.btn_restart,
            self.btn_export,
            self.btn_recording_settings,
            self.btn_tray,
            self.btn_switch_user,
        ]:
            top_bar.addWidget(button)

        top_bar.addStretch()

        self.user_badge = QLabel(f"{self.current_user['username']} ({self.current_user['role']})")
        self.user_badge.setObjectName("badgeLabel")
        top_bar.addWidget(self.grid_selector)
        top_bar.addWidget(self.user_badge)
        main_layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)

        self.live_tab = QWidget()
        live_layout = QHBoxLayout(self.live_tab)
        self.camera_list = QListWidget()
        self.camera_list.setMaximumWidth(280)
        live_layout.addWidget(self.camera_list)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        grid_widget = QWidget()
        self.video_grid = QGridLayout(grid_widget)
        self.video_grid.setSpacing(12)
        scroll.setWidget(grid_widget)
        live_layout.addWidget(scroll, 1)
        self.tabs.addTab(self.live_tab, "Live View")

        self.events_tab = QWidget()
        events_layout = QVBoxLayout(self.events_tab)
        self.events_table = QTableWidget(0, 4)
        self.events_table.setHorizontalHeaderLabels(["Время", "Камера", "Событие", "Файл"])
        self.events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.events_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.events_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.events_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.events_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.events_table.cellDoubleClicked.connect(self.play_selected_event)
        events_layout.addWidget(self.events_table)

        events_buttons = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить журнал")
        self.btn_refresh.clicked.connect(self.load_events)
        self.btn_clear = QPushButton("Очистить журнал")
        self.btn_clear.clicked.connect(self.clear_events_log)
        self.btn_play_event = QPushButton("Открыть запись")
        self.btn_play_event.clicked.connect(self.play_selected_event)
        events_buttons.addWidget(self.btn_refresh)
        events_buttons.addWidget(self.btn_clear)
        events_buttons.addWidget(self.btn_play_event)
        events_layout.addLayout(events_buttons)
        self.tabs.addTab(self.events_tab, "Журнал событий")

        self.player_tab = QWidget()
        player_layout = QVBoxLayout(self.player_tab)
        self.recordings_list = QListWidget()
        self.recordings_list.itemDoubleClicked.connect(self.play_recording_from_list)
        player_layout.addWidget(self.recordings_list)
        player_buttons = QHBoxLayout()
        self.btn_load_recordings = QPushButton("Обновить список")
        self.btn_load_recordings.clicked.connect(self.load_recordings)
        self.btn_play_recording = QPushButton("Воспроизвести")
        self.btn_play_recording.clicked.connect(self.play_recording_from_list)
        player_buttons.addWidget(self.btn_load_recordings)
        player_buttons.addWidget(self.btn_play_recording)
        player_layout.addLayout(player_buttons)
        self.tabs.addTab(self.player_tab, "Просмотр записей")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Система готова к работе")

        QShortcut(QKeySequence("F5"), self, self.load_events)
        QShortcut(QKeySequence("Ctrl+R"), self, self.restart_all_cameras)
        QShortcut(QKeySequence("Ctrl+W"), self, self.minimize_to_tray)

    def setup_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.btn_tray.setEnabled(False)
            self.btn_tray.setText("Трей недоступен")
            return

        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        tray_menu = QMenu(self)

        open_action = QAction("Открыть", self)
        open_action.triggered.connect(self.restore_from_tray)
        tray_menu.addAction(open_action)

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.exit_from_tray)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.handle_tray_activation)
        self.tray_icon.show()

    def handle_tray_activation(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_from_tray()

    def minimize_to_tray(self):
        if not self.tray_icon:
            self.showMinimized()
            return

        self.hide()
        self.tray_icon.showMessage(
            "ASK-Vision",
            "Приложение продолжает работать в системном трее.",
            QSystemTrayIcon.Information,
            2500,
        )

    def restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def exit_from_tray(self):
        self.force_exit = True
        self.close()

    def sync_app_settings(self):
        self.app_settings["style"] = self.current_style
        self.app_settings["theme"] = self.current_theme
        self.app_settings["grid_columns"] = self.grid_cols
        self.app_settings["recording"] = self.recording_settings
        self.app_settings["autostart_enabled"] = self.autostart_enabled
        self.app_settings["autologin_enabled"] = self.autologin_enabled
        self.app_settings["autologin_user"] = self.autologin_user
        save_app_settings(self.app_settings)

    def apply_current_appearance(self):
        app = QApplication.instance()
        if app:
            apply_appearance(app, self.current_style, self.current_theme)
        self.sync_app_settings()

    def set_grid_columns(self, value):
        self.grid_cols = int(value)
        self.sync_app_settings()
        if hasattr(self, "video_grid"):
            self.rebuild_grid()

    def open_recording_settings(self):
        if not self.has_permission("recording_settings"):
            return

        dialog = RecordingSettingsDialog(self.recording_settings, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        self.recording_settings = dialog.get_data()
        self.sync_app_settings()
        self.restart_all_cameras()
        self.status_bar.showMessage("Настройки записи сохранены", 3000)

    def open_quick_settings(self):
        dialog = QuickSettingsDialog(self.app_settings, self.current_user, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.get_data()
        self.current_style = data["style"]
        self.current_theme = data["theme"]
        self.grid_cols = data["grid_columns"]
        self.grid_selector.blockSignals(True)
        self.grid_selector.setValue(self.grid_cols)
        self.grid_selector.blockSignals(False)
        self.autostart_enabled = data["autostart_enabled"]
        self.autologin_enabled = data["autologin_enabled"]
        self.autologin_user = data["autologin_user"]
        self.apply_current_appearance()
        try:
            sync_autostart(self.autostart_enabled)
        except OSError as error:
            QMessageBox.warning(self, "Автозапуск", f"Не удалось обновить автозапуск: {error}")
        self.sync_app_settings()
        self.rebuild_grid()
        self.status_bar.showMessage("Настройки программы сохранены", 3000)

    def has_permission(self, key):
        return bool(self.permissions.get(key, False))

    def set_tab_access(self, widget, allowed):
        index = self.tabs.indexOf(widget)
        if index < 0:
            return

        if hasattr(self.tabs, "setTabVisible"):
            self.tabs.setTabVisible(index, allowed)
        self.tabs.setTabEnabled(index, allowed)

    def apply_permissions(self):
        self.btn_quick_settings.setVisible(self.current_user.get("role") == "admin")
        self.btn_add.setVisible(self.has_permission("add_camera"))
        self.btn_delete.setVisible(self.has_permission("delete_camera"))
        self.btn_settings.setVisible(self.has_permission("camera_settings"))
        self.btn_toggle.setVisible(self.has_permission("toggle_cameras"))
        self.btn_restart.setVisible(self.has_permission("restart_cameras"))
        self.btn_export.setVisible(self.has_permission("export_csv"))
        self.btn_clear.setVisible(self.has_permission("clear_events"))
        self.btn_recording_settings.setVisible(self.has_permission("recording_settings"))

        self.set_tab_access(self.live_tab, self.has_permission("live_view"))
        self.set_tab_access(self.events_tab, self.has_permission("events_tab"))
        self.set_tab_access(self.player_tab, self.has_permission("recordings_tab"))

        for index in range(self.tabs.count()):
            if self.tabs.isTabEnabled(index):
                self.tabs.setCurrentIndex(index)
                break

    def refresh_current_user_context(self, user):
        self.current_user = user
        self.permissions = self.current_user["permissions"]
        self.user_badge.setText(f"{self.current_user['username']} ({self.current_user['role']})")
        self.apply_permissions()

    def switch_user(self):
        login = LoginDialog()
        login.username.setCurrentText(self.current_user["username"])
        if login.exec_() != QDialog.Accepted or not login.accepted:
            return

        self.refresh_current_user_context(login.current_user)
        self.status_bar.showMessage(f"Активный пользователь: {self.current_user['username']}", 3000)

    def start_all_cameras(self):
        for cam in self.current_cameras:
            self.add_camera_to_ui(cam)

    def stop_all_cameras(self):
        for cam_id, thread in list(self.threads.items()):
            thread.stop()
            self.set_camera_item_text(cam_id, "OFF")
        self.threads.clear()

    def restart_all_cameras(self):
        self.stop_all_cameras()
        self.start_all_cameras()
        self.status_bar.showMessage("Все камеры перезапущены", 3000)

    def change_grid(self):
        self.grid_cols = 3 if self.grid_cols == 2 else 2
        self.rebuild_grid()

    def rebuild_grid(self):
        for i in reversed(range(self.video_grid.count())):
            widget = self.video_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        ordered_ids = [cam["id"] for cam in self.current_cameras if cam["id"] in self.camera_labels]
        for index, cam_id in enumerate(ordered_ids):
            row = index // self.grid_cols
            col = index % self.grid_cols
            self.video_grid.addWidget(self.camera_labels[cam_id], row, col)

    def toggle_all_cameras(self):
        if self.threads:
            self.stop_all_cameras()
            self.status_bar.showMessage("Все камеры остановлены", 2500)
        else:
            self.start_all_cameras()
            self.status_bar.showMessage("Все камеры запущены", 2500)

    def export_events_csv(self):
        if not self.has_permission("export_csv"):
            return

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт журнала", "", "CSV (*.csv)")
        if not path:
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM events ORDER BY timestamp DESC")
        rows = c.fetchall()
        conn.close()

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "Камера", "Время", "Файл", "Описание"])
            writer.writerows(rows)

        self.status_bar.showMessage("Журнал экспортирован в CSV", 3000)

    def clear_events_log(self):
        if not self.has_permission("clear_events"):
            return

        reply = QMessageBox.question(
            self,
            "Очистка журнала",
            "Удалить весь журнал событий? Это действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM events")
        conn.commit()
        conn.close()
        self.load_events()
        self.status_bar.showMessage("Журнал событий очищен", 4000)

    def get_camera_name(self, cam_id):
        cam = next((camera for camera in self.current_cameras if camera["id"] == cam_id), None)
        return cam["name"] if cam else f"Camera {cam_id}"

    def set_camera_item_text(self, cam_id, state):
        item = self.camera_items.get(cam_id)
        if item:
            item.setText(f"[{state}] {self.get_camera_name(cam_id)}")

    def is_local_camera_source(self, value):
        source = str(value).strip().lower()
        return source.isdigit() or source.startswith("/dev/video")

    def open_capture_for_source(self, source):
        source_str = str(source).strip()
        if source_str.isdigit():
            index = int(source_str)
            if sys.platform.startswith("win") and hasattr(cv2, "CAP_DSHOW"):
                return cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if sys.platform.startswith("linux") and hasattr(cv2, "CAP_V4L2"):
                return cv2.VideoCapture(index, cv2.CAP_V4L2)
            return cv2.VideoCapture(index)

        if sys.platform.startswith("linux") and source_str.startswith("/dev/video") and hasattr(cv2, "CAP_V4L2"):
            return cv2.VideoCapture(source_str, cv2.CAP_V4L2)

        return cv2.VideoCapture(source_str)

    def discover_local_camera_sources(self, max_devices=6):
        sources = []
        seen_urls = set()

        if sys.platform.startswith("linux") and os.path.exists("/dev"):
            for device_name in sorted(name for name in os.listdir("/dev") if name.startswith("video")):
                device_path = os.path.join("/dev", device_name)
                cap = self.open_capture_for_source(device_path)
                opened = cap.isOpened()
                cap.release()
                if opened:
                    sources.append({"label": f"Веб-камера {device_name}", "url": device_path})
                    seen_urls.add(device_path)

        for index in range(max_devices):
            source = str(index)
            if source in seen_urls:
                continue
            cap = self.open_capture_for_source(source)
            opened = cap.isOpened()
            cap.release()
            if opened:
                sources.append({"label": f"Веб-камера {index}", "url": source})
                seen_urls.add(source)

        return sources

    def setup_camera_source_editor(self, source_type, local_combo, url_field, refresh_button, selected_url="0"):
        def apply_selected_local_camera():
            selected_source = local_combo.currentData()
            if selected_source:
                url_field.setText(str(selected_source))

        def sync_editor_state():
            local_mode = source_type.currentData() == "local"
            has_local_source = bool(local_combo.currentData())
            refresh_button.setEnabled(local_mode)
            local_combo.setEnabled(local_mode and local_combo.count() > 0)
            url_field.setReadOnly(local_mode and has_local_source)
            if local_mode and has_local_source:
                apply_selected_local_camera()

        def refresh_local_cameras():
            current_url = url_field.text().strip() or str(selected_url).strip()
            local_combo.blockSignals(True)
            local_combo.clear()
            for source in self.discover_local_camera_sources():
                local_combo.addItem(source["label"], source["url"])

            if local_combo.count() == 0:
                local_combo.addItem("Камеры не найдены", "")

            match_index = local_combo.findData(current_url)
            if match_index >= 0:
                local_combo.setCurrentIndex(match_index)
            elif self.is_local_camera_source(current_url):
                local_combo.addItem(f"Текущий источник ({current_url})", current_url)
                local_combo.setCurrentIndex(local_combo.count() - 1)

            local_combo.blockSignals(False)
            sync_editor_state()

        local_combo.currentIndexChanged.connect(lambda _=None: sync_editor_state())
        source_type.currentIndexChanged.connect(lambda _=None: sync_editor_state())
        refresh_button.clicked.connect(refresh_local_cameras)

        source_type.blockSignals(True)
        source_type.setCurrentIndex(0 if self.is_local_camera_source(selected_url) else 1)
        source_type.blockSignals(False)
        url_field.setText(str(selected_url).strip())
        refresh_local_cameras()
        sync_editor_state()

    def add_camera_to_ui(self, cam):
        cam_id = cam["id"]
        if cam_id not in self.camera_items:
            item = QListWidgetItem()
            self.camera_list.addItem(item)
            self.camera_items[cam_id] = item
        self.set_camera_item_text(cam_id, "LIVE")

        if cam_id not in self.camera_labels:
            label = QLabel()
            label.setMinimumSize(640, 360)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background: #090b0f; border: 1px solid #314159; border-radius: 10px;")
            self.camera_labels[cam_id] = label
            self.rebuild_grid()

        if cam_id in self.threads:
            return

        thread = CameraThread(
            cam_id,
            cam["name"],
            cam["url"],
            cam.get("threshold", 25),
            cam.get("min_area", 500),
            cam.get("pre_record", 3),
            cam.get("post_record", 5),
            cam.get("detection_enabled", True),
            cam.get("recording_mode", "motion"),
            self.recording_settings,
        )
        thread.frame_ready.connect(self.update_frame)
        thread.status_changed.connect(self.update_camera_status)
        thread.recording_status.connect(self.update_recording_status)
        thread.start()
        self.threads[cam_id] = thread

    def update_frame(self, cam_id, frame, motion):
        if cam_id not in self.camera_labels:
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        label = self.camera_labels[cam_id]
        label.setPixmap(QPixmap.fromImage(qimg).scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def update_camera_status(self, cam_id, status):
        if status == "ОТКЛЮЧЕНА":
            self.set_camera_item_text(cam_id, "OFF")
        elif cam_id not in self.threads or not self.threads[cam_id].recording:
            self.set_camera_item_text(cam_id, "LIVE")
        self.status_bar.showMessage(f"{self.get_camera_name(cam_id)}: {status}", 2500)

    def update_recording_status(self, cam_id, is_recording):
        self.set_camera_item_text(cam_id, "REC" if is_recording else "LIVE")
        if is_recording:
            self.status_bar.showMessage(f"{self.get_camera_name(cam_id)}: идёт запись", 2500)

    def add_camera_dialog(self):
        if not self.has_permission("add_camera"):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить камеру")
        form = QFormLayout(dialog)

        name = QLineEdit("Новая камера")
        source_type = QComboBox()
        source_type.addItem("Веб-камера", "local")
        source_type.addItem("RTSP / URL", "network")
        local_camera = QComboBox()
        refresh_local = QPushButton("Обновить список")
        local_source_row = QWidget()
        local_source_layout = QHBoxLayout(local_source_row)
        local_source_layout.setContentsMargins(0, 0, 0, 0)
        local_source_layout.setSpacing(8)
        local_source_layout.addWidget(local_camera, 1)
        local_source_layout.addWidget(refresh_local)
        url = QLineEdit("0")
        thresh = QSpinBox()
        thresh.setValue(25)
        area = QSpinBox()
        area.setValue(500)
        pre = QSpinBox()
        pre.setValue(3)
        post = QSpinBox()
        post.setValue(5)
        mode = QComboBox()
        mode.addItems(["Только по движению", "Постоянная запись"])
        detect = QCheckBox("Включить детекцию")
        detect.setChecked(True)

        form.addRow("Название:", name)
        form.addRow("Источник:", source_type)
        form.addRow("Локальная камера:", local_source_row)
        form.addRow("URL / путь:", url)
        form.addRow("Порог детекции:", thresh)
        form.addRow("Мин. площадь:", area)
        form.addRow("Предзапись (сек):", pre)
        form.addRow("Постзапись (сек):", post)
        form.addRow("Режим записи:", mode)
        form.addRow("", detect)
        self.setup_camera_source_editor(source_type, local_camera, url, refresh_local, "0")

        button = QPushButton("Добавить")
        button.clicked.connect(
            lambda: self.save_new_camera(
                dialog,
                name.text(),
                url.text(),
                thresh.value(),
                area.value(),
                pre.value(),
                post.value(),
                mode.currentText(),
                detect.isChecked(),
            )
        )
        form.addRow(button)
        dialog.exec_()

    def save_new_camera(self, dialog, name, url, thresh, area, pre, post, mode_text, detect):
        source_url = url.strip()
        if not source_url:
            QMessageBox.warning(dialog, "Ошибка", "Укажите источник камеры")
            return

        new_id = max([c["id"] for c in self.current_cameras], default=-1) + 1
        recording_mode = "constant" if "Постоянная" in mode_text else "motion"
        camera = {
            "id": new_id,
            "name": name.strip() or f"Камера {new_id}",
            "url": source_url,
            "threshold": thresh,
            "min_area": area,
            "pre_record": pre,
            "post_record": post,
            "detection_enabled": detect,
            "recording_mode": recording_mode,
        }
        self.current_cameras.append(camera)
        save_cameras(self.current_cameras)
        self.add_camera_to_ui(camera)
        dialog.accept()

    def delete_selected_camera(self):
        if not self.has_permission("delete_camera"):
            return

        row = self.camera_list.currentRow()
        if row < 0:
            return

        camera = self.current_cameras[row]
        if QMessageBox.question(self, "Удалить?", f"Удалить {camera['name']}?") != QMessageBox.Yes:
            return

        if camera["id"] in self.threads:
            self.threads[camera["id"]].stop()
            del self.threads[camera["id"]]
        if camera["id"] in self.camera_labels:
            self.camera_labels[camera["id"]].deleteLater()
            del self.camera_labels[camera["id"]]
        if camera["id"] in self.camera_items:
            row_to_remove = self.camera_list.row(self.camera_items[camera["id"]])
            self.camera_list.takeItem(row_to_remove)
            del self.camera_items[camera["id"]]

        del self.current_cameras[row]
        save_cameras(self.current_cameras)
        self.rebuild_grid()

    def open_camera_settings(self):
        if not self.has_permission("camera_settings"):
            return

        row = self.camera_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "Внимание", "Выберите камеру в списке")
            return

        camera = self.current_cameras[row]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Настройки: {camera['name']}")
        form = QFormLayout(dialog)

        name = QLineEdit(camera.get("name", ""))
        source_type = QComboBox()
        source_type.addItem("Веб-камера", "local")
        source_type.addItem("RTSP / URL", "network")
        local_camera = QComboBox()
        refresh_local = QPushButton("Обновить список")
        local_source_row = QWidget()
        local_source_layout = QHBoxLayout(local_source_row)
        local_source_layout.setContentsMargins(0, 0, 0, 0)
        local_source_layout.setSpacing(8)
        local_source_layout.addWidget(local_camera, 1)
        local_source_layout.addWidget(refresh_local)
        url = QLineEdit(camera.get("url", "0"))
        thresh = QSpinBox()
        thresh.setValue(camera.get("threshold", 25))
        area = QSpinBox()
        area.setRange(100, 50000)
        area.setValue(camera.get("min_area", 500))
        pre = QSpinBox()
        pre.setValue(camera.get("pre_record", 3))
        post = QSpinBox()
        post.setValue(camera.get("post_record", 5))
        mode = QComboBox()
        mode.addItems(["Только по движению", "Постоянная запись"])
        mode.setCurrentText("Постоянная запись" if camera.get("recording_mode") == "constant" else "Только по движению")
        detect = QCheckBox("Включить детекцию движения")
        detect.setChecked(camera.get("detection_enabled", True))

        form.addRow("Название:", name)
        form.addRow("Источник:", source_type)
        form.addRow("Локальная камера:", local_source_row)
        form.addRow("URL / путь:", url)
        form.addRow("Порог детекции:", thresh)
        form.addRow("Мин. площадь:", area)
        form.addRow("Предзапись (сек):", pre)
        form.addRow("Постзапись (сек):", post)
        form.addRow("Режим записи:", mode)
        form.addRow("", detect)
        self.setup_camera_source_editor(source_type, local_camera, url, refresh_local, camera.get("url", "0"))

        button = QPushButton("Сохранить")
        button.clicked.connect(
            lambda: self.save_camera_settings(
                dialog,
                row,
                name.text(),
                url.text(),
                thresh.value(),
                area.value(),
                pre.value(),
                post.value(),
                mode.currentText(),
                detect.isChecked(),
            )
        )
        form.addRow(button)
        dialog.exec_()

    def save_camera_settings(self, dialog, row, name, url, thresh, area, pre, post, mode_text, detect):
        source_url = url.strip()
        if not source_url:
            QMessageBox.warning(dialog, "Ошибка", "Укажите источник камеры")
            return

        recording_mode = "constant" if "Постоянная" in mode_text else "motion"
        camera = self.current_cameras[row]
        camera["name"] = name.strip() or camera.get("name") or f"Камера {camera['id']}"
        camera["url"] = source_url
        camera["threshold"] = thresh
        camera["min_area"] = area
        camera["pre_record"] = pre
        camera["post_record"] = post
        camera["detection_enabled"] = detect
        camera["recording_mode"] = recording_mode

        save_cameras(self.current_cameras)

        if camera["id"] in self.threads:
            self.threads[camera["id"]].stop()
            del self.threads[camera["id"]]

        self.add_camera_to_ui(camera)
        dialog.accept()
        self.status_bar.showMessage("Настройки камеры сохранены", 3000)

    def load_events(self):
        self.events_table.setRowCount(0)
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT timestamp, camera_name, description, file_path FROM events ORDER BY timestamp DESC")
        for data in c.fetchall():
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            for col, value in enumerate(data):
                self.events_table.setItem(row, col, QTableWidgetItem(str(value)))
        conn.close()

    def play_selected_event(self):
        row = self.events_table.currentRow()
        if row < 0:
            return

        path = self.events_table.item(row, 3).text()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Файл не найден", "Видео для выбранного события не найдено")
            return

        VideoPlayerDialog(path).exec_()

    def load_recordings(self):
        self.recordings_list.clear()
        if not os.path.exists("videos"):
            return

        for filename in sorted(os.listdir("videos"), reverse=True):
            if filename.lower().endswith(".mp4"):
                self.recordings_list.addItem(filename)

    def play_recording_from_list(self):
        item = self.recordings_list.currentItem()
        if not item:
            return

        path = os.path.join("videos", item.text())
        if not os.path.exists(path):
            QMessageBox.warning(self, "Файл не найден", "Выбранная запись недоступна")
            return

        VideoPlayerDialog(path).exec_()

    def closeEvent(self, event):
        if self.tray_icon:
            self.tray_icon.hide()
        self.stop_all_cameras()
        event.accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    init_db()
    app_settings = load_app_settings()
    apply_appearance(app, app_settings.get("style", "modern"), app_settings.get("theme", "dark"))

    if app_settings.get("autologin_enabled"):
        autologin_user = get_user_by_username(app_settings.get("autologin_user", "admin"))
        if autologin_user:
            window = MainWindow(autologin_user)
            window.show()
            sys.exit(app.exec_())

    login = LoginDialog()
    if login.exec_() == QDialog.Accepted and login.accepted:
        window = MainWindow(login.current_user)
        window.show()
        sys.exit(app.exec_())
    sys.exit(0)
