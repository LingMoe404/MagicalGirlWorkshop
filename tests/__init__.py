"""测试包：提供跨测试文件共享的清理工具。"""

from PySide6.QtCore import QCoreApplication, QEvent


def drain_deferred_deletes():
    """排空 Qt 的 DeferredDelete 事件队列。

    headless 测试没有事件循环，deleteLater() 投递的 DeferredDelete 事件永不派发，
    窗口对象（如 MainWindow）会跨测试持续存活；下一次构造又把这些存活窗口纳入
    父子遍历，导致构造成本随测试数线性上升（实测 6 个窗口 0.21s -> 1.02s）。
    在 teardown 里手动排空，使每次构造保持常数开销。产品本身有事件循环，
    deleteLater 正常工作，因此该处理只属于测试环境。
    """
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
