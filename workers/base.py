from PySide6.QtCore import QThread

class BaseWorker(QThread):
    """
    所有后台工作线程的基类。
    提供统一的 is_running 标志位和基础的 stop 方法结构。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True

    def stop(self):
        """ 请求停止线程，子类应重写此方法以清理特定资源（如子进程）。 """
        self.is_running = False
        self.quit()
        self.wait()