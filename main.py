import sys
import os
from PyQt5.QtWidgets import QApplication, QSplashScreen, QDialog
from PyQt5.QtCore import Qt, QTimer
from ui_main import LoginDialog, MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)

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


    login = LoginDialog()
    if login.exec_() == QDialog.Accepted and login.accepted:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
