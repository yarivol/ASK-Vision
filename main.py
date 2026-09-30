import os
import sys

if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    for env_name in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_PLUGIN_PATH", "QT_QPA_FONTDIR"):
        env_value = os.environ.get(env_name, "")
        if "cv2" in env_value.lower():
            os.environ.pop(env_name, None)

from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QLibraryInfo
from PyQt5.QtWidgets import QApplication, QSplashScreen, QDialog

if sys.platform.startswith("linux"):
    plugins_path = QLibraryInfo.location(QLibraryInfo.PluginsPath)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugins_path
    os.environ["QT_PLUGIN_PATH"] = plugins_path
    QCoreApplication.setLibraryPaths([plugins_path])

from ui_main import LoginDialog, MainWindow, apply_appearance
from database import init_db, get_user_by_username
from settings import load_app_settings


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    app_settings = load_app_settings()
    apply_appearance(app, app_settings.get("style", "modern"), app_settings.get("theme", "dark"))

    splash = QSplashScreen()
    splash.setStyleSheet("""
        background-color: #1e1e1e; 
        color: white; 
        font-size: 22px; 
        font-weight: bold;
    """)
    splash.showMessage(
        "ASK-Vision v1.0\nЗагрузка...", 
        Qt.AlignCenter | Qt.AlignBottom, 
        Qt.white
    )
    splash.show()
    app.processEvents()


    QTimer.singleShot(700, splash.close)

    if app_settings.get("autologin_enabled"):
        autologin_user = get_user_by_username(app_settings.get("autologin_user", "admin"))
        # Если у пользователя дефолтный пароль — автологин пропускаем, чтобы показать смену пароля
        if autologin_user and not autologin_user.get("must_change_password"):
            window = MainWindow(autologin_user)
            window.show()
            sys.exit(app.exec_())

    login = LoginDialog()
    if login.exec_() == QDialog.Accepted and login.accepted:
        window = MainWindow(login.current_user)
        window.show()
        sys.exit(app.exec_())

    sys.exit(0)
