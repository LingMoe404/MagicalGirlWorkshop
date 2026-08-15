import os
import sys

os.environ["QT_API"] = "pyside6"
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from config import APP_ID
from ui.main_window import MainWindow

if __name__ == "__main__":
    # 设置 AppUserModelID，将程序与 Python 解释器区分开，确保任务栏图标清晰且独立
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

    # 启用高分屏支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    from PySide6.QtGui import QFont

    app = QApplication(sys.argv)

    # 注入全局优雅字体 (解决部分高分屏系统默认字体发虚或显示通用锯齿字体问题)
    global_font = QFont("Microsoft YaHei UI", 9)
    global_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(global_font)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())
