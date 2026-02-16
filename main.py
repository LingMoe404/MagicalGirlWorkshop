import sys
import os
os.environ["QT_API"] = "pyside6"
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from config import APP_ID
from ui.main_window import MainWindow

if __name__ == '__main__':
    # 设置 AppUserModelID，将程序与 Python 解释器区分开，确保任务栏图标清晰且独立
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    # 启用高分屏支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
