"""MainWindow <-> TranscodeController 集成测试。

验证主窗口接入 TranscodeController 后的接线行为：
- MainWindow 创建并持有 self.transcode_controller（可构造函数注入 FakeController）
- start_task 保留 UI 输入校验与 config 构建，改用 controller.start(config)
- controller 的 9 个信号连接到现有 log / pbar / FileListManager / on_finished /
  on_worker_error / 并发状态 UI
- pause_task / stop_task / on_worker_error 改为调用 controller 方法
- finished 后 UI 恢复；closeEvent 运行中确认后调用 controller.shutdown(2000)
- 不再存在两套实际转码生命周期（不再持有 self.worker）

使用 FakeController 隔离真实 ffmpeg / GPU / coordinator。不依赖真实 Qt 事件循环。
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from i18n.translator import tr
from ui.config_manager import ConfigManager
from ui.main_window import MainWindow
from workers import TranscodeController


class _RecordingSignal:
    """记录 connect 回调并可手动触发的伪信号（与既有测试一致）。"""

    def __init__(self):
        self._connected = []

    def connect(self, fn, *args, **kwargs):
        self._connected.append(fn)

    def emit(self, *args):
        for fn in list(self._connected):
            fn(*args)

    def disconnect(self, *args, **kwargs):
        self._connected.clear()

    def count(self):
        return len(self._connected)


class FakeController:
    """模拟 TranscodeController：捕获调用，不启动真实批次。"""

    def __init__(self, parent=None, coordinator_factory=None):
        self.parent = parent
        self.coordinator_factory = coordinator_factory
        self.start_calls = []
        self.stop_calls = 0
        self.pause_calls = []
        self.decisions = []
        self.shutdown_calls = []
        self.is_paused = False
        self.coordinator = None

        self.log_signal = _RecordingSignal()
        self.progress_total_signal = _RecordingSignal()
        self.progress_current_signal = _RecordingSignal()
        self.file_progress_signal = _RecordingSignal()
        self.file_stats_signal = _RecordingSignal()
        self.file_status_signal = _RecordingSignal()
        self.finished_signal = _RecordingSignal()
        self.ask_error_decision = _RecordingSignal()
        self.concurrency_status_signal = _RecordingSignal()

    def start(self, config):
        self.start_calls.append(config)
        return True

    def stop(self):
        self.stop_calls += 1

    def set_paused(self, paused):
        self.pause_calls.append(paused)
        self.is_paused = paused

    def decide_error(self, task_id, decision):
        self.decisions.append((task_id, decision))

    def shutdown(self, timeout=2000):
        self.shutdown_calls.append(timeout)
        return True

    def is_running(self):
        return bool(self.start_calls) and not self.stop_calls


class _FakeWorker:
    """模拟 Duration/Thumbnail worker：不启动真实 QThread。"""

    def __init__(self, *args, **kwargs):
        self.result = _RecordingSignal()
        self.finished = _RecordingSignal()
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        pass

    def deleteLater(self):
        pass


class MainWindowTranscodeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.cfg_path = os.path.join(self.root, "config.ini")
        self._mkfile("a.mkv")
        self._mkfile("b.mkv")

    def _mkfile(self, name):
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("x")
        return path

    def _make_window(self, controller=None):
        w = MainWindow(
            config_manager=ConfigManager(config_path=self.cfg_path),
            transcode_controller=controller,
        )
        # 注入桩 worker 工厂，避免真实 ffprobe/ffmpeg 线程导致 teardown 崩溃
        w.file_list_manager.duration_worker_cls = _FakeWorker
        w.file_list_manager.thumbnail_worker_cls = _FakeWorker
        w.info_interface.stop_worker = lambda: None
        self.addCleanup(w.file_list_manager.stop_workers)
        self.addCleanup(w.info_interface.stop_worker)
        self.addCleanup(w.deleteLater)
        return w

    # --- 1. controller 实例化与持有 ---
    def test_controller_created_and_held(self):
        w = self._make_window()
        self.assertIsInstance(w.transcode_controller, TranscodeController)
        # 不再持有旧的两套转码生命周期（self.worker 被移除）
        self.assertFalse(hasattr(w, "worker"))

    def test_injected_controller_is_used(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        self.assertIs(w.transcode_controller, controller)

    # --- 2. start_task 使用 controller.start(config) ---
    def test_start_task_uses_controller_start(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        p = self._mkfile("snap.mkv")
        w.add_source_paths([p])
        w.file_list_manager.file_metadata[p] = {"codec": "h264", "duration": 120.0}

        with mock.patch.object(controller, "start", wraps=controller.start) as m_start:
            w.start_task()

        m_start.assert_called_once()
        config = m_start.call_args.args[0]
        self.assertEqual(config["selected_files"], [p])
        self.assertEqual(config["metadata"], w.file_list_manager.file_metadata)

    def test_start_task_disables_ui_and_configures_buttons(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        p = self._mkfile("ui.mkv")
        w.add_source_paths([p])
        w.start_task()
        self.assertFalse(w.btn_start.isEnabled())
        self.assertFalse(w.btn_clear_list.isEnabled())
        self.assertTrue(w.btn_pause.isEnabled())
        self.assertTrue(w.btn_stop.isEnabled())
        self.assertEqual(w.btn_start.text(), tr("button.start.in_progress"))

    def test_start_task_keeps_input_validation(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        # 无文件：不应调用 controller.start，UI 保持可点
        w.start_task()
        self.assertEqual(controller.start_calls, [])
        self.assertTrue(w.btn_start.isEnabled())

    # --- 3. 9 个信号连接 ---
    def test_controller_signals_connected(self):
        controller = FakeController()
        self._make_window(controller=controller)
        self.assertGreater(controller.log_signal.count(), 0)
        self.assertGreater(controller.progress_total_signal.count(), 0)
        self.assertGreater(controller.progress_current_signal.count(), 0)
        self.assertGreater(controller.file_progress_signal.count(), 0)
        self.assertGreater(controller.file_stats_signal.count(), 0)
        self.assertGreater(controller.file_status_signal.count(), 0)
        self.assertGreater(controller.finished_signal.count(), 0)
        self.assertGreater(controller.ask_error_decision.count(), 0)
        self.assertGreater(controller.concurrency_status_signal.count(), 0)

    def test_controller_log_signal_connected_to_log(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        self.assertIn(w.log, controller.log_signal._connected)

    def test_controller_finished_signal_connected_to_on_finished(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        self.assertIn(w.on_finished, controller.finished_signal._connected)

    def test_controller_ask_error_signal_connected_to_on_worker_error(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        self.assertIn(w.on_worker_error, controller.ask_error_decision._connected)

    def test_controller_concurrency_signal_connected_to_status_label(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        self.assertIn(
            w.lbl_concurrency_status.setText,
            controller.concurrency_status_signal._connected,
        )

    # --- 4. pause / stop / error decision ---
    def test_pause_task_forwards_to_controller(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        controller.start_calls.append({"selected_files": ["a.mkv"]})
        w.pause_task()
        self.assertEqual(controller.pause_calls, [True])

    def test_stop_task_forwards_to_controller(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        controller.start_calls.append({"selected_files": ["a.mkv"]})
        w.stop_task()
        self.assertEqual(controller.stop_calls, 1)

    def test_on_worker_error_decision_routes_to_controller(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        with mock.patch("ui.main_window.MessageDialog", autospec=True) as m_dlg:
            dlg = m_dlg.return_value
            dlg.yesButton = mock.Mock()
            dlg.cancelButton = mock.Mock()
            dlg.titleLabel = mock.Mock()
            dlg.accept = mock.Mock()
            dlg.exec.return_value = True  # 用户选择跳过 -> continue
            w.on_worker_error("task-1", "标题", "内容")
        self.assertEqual(controller.decisions, [("task-1", "continue")])

    def test_on_worker_error_stop_decision_routes_to_controller(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        with mock.patch("ui.main_window.MessageDialog", autospec=True) as m_dlg:
            dlg = m_dlg.return_value
            dlg.yesButton = mock.Mock()
            dlg.cancelButton = mock.Mock()
            dlg.titleLabel = mock.Mock()
            dlg.accept = mock.Mock()
            dlg.exec.return_value = False  # 用户选择停止 -> stop
            w.on_worker_error("task-1", "标题", "内容")
        self.assertEqual(controller.decisions, [("task-1", "stop")])

    # --- 5. finished UI 恢复 ---
    def test_finished_restores_ui(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        p = self._mkfile("done.mkv")
        w.add_source_paths([p])
        w.start_task()
        self.assertFalse(w.btn_start.isEnabled())
        w.on_finished()
        self.assertTrue(w.btn_start.isEnabled())
        self.assertTrue(w.btn_clear_list.isEnabled())
        self.assertFalse(w.btn_pause.isEnabled())
        self.assertFalse(w.btn_stop.isEnabled())
        self.assertEqual(
            w.lbl_concurrency_status.text(),
            tr("home.action_card.concurrency.idle"),
        )

    # --- 6. closeEvent shutdown ---
    def test_close_event_with_running_batch_prompts_and_shuts_down(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        # 构造"批次运行中"：controller.start 已被调用且未 stop
        controller.start_calls.append({"selected_files": ["a.mkv"]})
        with (
            mock.patch("ui.main_window.MessageDialog", autospec=True) as m_dlg,
            mock.patch.object(w.info_interface, "stop_worker"),
        ):
            dlg = m_dlg.return_value
            dlg.yesButton = mock.Mock()
            dlg.cancelButton = mock.Mock()
            dlg.exec.return_value = True  # 用户确认关闭
            w.closeEvent(QCloseEvent())
        self.assertEqual(controller.shutdown_calls, [2000])

    def test_close_event_cancel_keeps_batch(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        controller.start_calls.append({"selected_files": ["a.mkv"]})
        with (
            mock.patch("ui.main_window.MessageDialog", autospec=True) as m_dlg,
            mock.patch.object(w.info_interface, "stop_worker"),
        ):
            dlg = m_dlg.return_value
            dlg.yesButton = mock.Mock()
            dlg.cancelButton = mock.Mock()
            dlg.exec.return_value = False  # 用户取消关闭
            w.closeEvent(QCloseEvent())
        self.assertEqual(controller.shutdown_calls, [])

    def test_close_event_without_running_batch_no_shutdown(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        with mock.patch.object(w.info_interface, "stop_worker"):
            w.closeEvent(QCloseEvent())
        self.assertEqual(controller.shutdown_calls, [])


if __name__ == "__main__":
    unittest.main()
