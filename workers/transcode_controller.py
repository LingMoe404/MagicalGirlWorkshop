"""TranscodeController：EncodingCoordinator 的无 UI 门面（facade）。

作为 ``EncodingCoordinator`` 的薄封装，把批次转码生命周期
（启动 / 暂停 / 恢复 / 停止 / 错误决策 / 等待 / 关闭）暴露给 UI 层，
同时原样透传全部 Qt 信号。控制器只组合 coordinator，不复制任何调度算法。

coordinator 的引用由 ``finished_signal`` 驱动清理：信号发出后清空引用，
允许后续批次重新创建新实例。``start()`` 不会替换正在运行的 coordinator。

按计划 Task 3，本阶段不纳入 DependencyWorker——依赖自检保持其独立的
MainWindow 生命周期，避免范围扩张。
"""

from PySide6.QtCore import QObject, Signal

from .coordinator import EncodingCoordinator


class TranscodeController(QObject):
    # 透传自 EncodingCoordinator 的信号（签名保持一致）
    log_signal = Signal(str, str)
    progress_total_signal = Signal(int)
    progress_current_signal = Signal(int)
    file_progress_signal = Signal(str, int)
    file_stats_signal = Signal(str, str, str)
    file_status_signal = Signal(str, str)
    finished_signal = Signal()
    ask_error_decision = Signal(str, str, str)
    concurrency_status_signal = Signal(str)

    def __init__(self, parent=None, coordinator_factory=EncodingCoordinator):
        super().__init__(parent)
        self._coordinator_factory = coordinator_factory
        # 当前批次 coordinator；finished_signal 后清空为 None
        self.coordinator = None

    @property
    def is_paused(self):
        coordinator = self.coordinator
        if coordinator is None:
            return False
        return bool(coordinator.is_paused)

    def start(self, config):
        """启动一个批次。

        已运行时视为成功（不替换 coordinator）返回 True；
        启动后 coordinator 缺失或未处于运行态时返回 False。
        """
        coordinator = self.coordinator
        if coordinator is not None and coordinator.isRunning():
            return True

        new_coordinator = self._coordinator_factory(config, self)
        self.coordinator = new_coordinator
        self._connect(new_coordinator)
        new_coordinator.start()

        current = self.coordinator
        return not (current is None or not current.isRunning())

    def stop(self):
        """异步停止当前批次（保持异步，不阻塞等待）。"""
        coordinator = self.coordinator
        if coordinator is not None:
            coordinator.stop()

    def set_paused(self, paused):
        """暂停 / 恢复当前批次，转发给 coordinator。"""
        coordinator = self.coordinator
        if coordinator is not None:
            coordinator.set_paused(paused)

    def decide_error(self, task_id, decision):
        """转发错误决策（如 continue / stop）给 coordinator。"""
        coordinator = self.coordinator
        if coordinator is not None:
            coordinator.receive_error_decision(task_id, decision)

    def wait(self, timeout=None):
        """等待当前批次结束；无 coordinator 时视为立即成功。"""
        coordinator = self.coordinator
        if coordinator is None:
            return True
        return bool(coordinator.wait(timeout))

    def shutdown(self, timeout=2000):
        """stop + wait 的组合：先异步停止，再等待指定超时（默认 2000ms）。"""
        coordinator = self.coordinator
        if coordinator is None:
            return True
        coordinator.stop()
        return bool(coordinator.wait(timeout))

    def is_running(self):
        coordinator = self.coordinator
        if coordinator is None:
            return False
        return bool(coordinator.isRunning())

    def _connect(self, coordinator):
        """把 coordinator 的全部信号透传给控制器同名信号。"""
        coordinator.log_signal.connect(self.log_signal.emit)
        coordinator.progress_total_signal.connect(self.progress_total_signal.emit)
        coordinator.progress_current_signal.connect(self.progress_current_signal.emit)
        coordinator.file_progress_signal.connect(self.file_progress_signal.emit)
        coordinator.file_stats_signal.connect(self.file_stats_signal.emit)
        coordinator.file_status_signal.connect(self.file_status_signal.emit)
        coordinator.ask_error_decision.connect(self.ask_error_decision.emit)
        coordinator.concurrency_status_signal.connect(
            self.concurrency_status_signal.emit
        )
        coordinator.finished_signal.connect(
            lambda: self._on_coordinator_finished(coordinator)
        )

    def _on_coordinator_finished(self, coordinator):
        """先透传 finished_signal，再清理引用。

        仅当传入的 coordinator 仍是当前引用时清空，避免旧实例在停止期间
        被新批次替换后，其 finished 回调误清空新批次的引用。
        """
        self.finished_signal.emit()
        if self.coordinator is coordinator:
            self.coordinator = None
