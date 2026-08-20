"""MainWindow <-> LogManager 集成测试。

验证主窗口接入 LogManager 后的接线行为：
- MainWindow 不再持有 log_mutex / log_queue，日志状态由 LogManager 管理
- LogManager 在 _init_log_area 创建 text_log 后 attach
- log() 转发到 manager，process_log_queue() 转发到 manager.flush()
- 主窗口 QTimer 仍作为定时器槽连接点（Manager 不创建隐式 timer）
- on_settings_save_requested 更新 global_settings 后同步 log_cap，
  非法值回退 LOG_MAX_BLOCKS；初始加载/恢复默认后同步 log_cap
- closeEvent 停止日志 timer 与 manager

不依赖真实 ffprobe/ffmpeg。
不依赖真实 QTextEdit 渲染：通过替换 text_log 验证 flush 被调用。
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from config import LOG_MAX_BLOCKS
from ui.config_manager import ConfigManager
from ui.log_manager import LogManager
from ui.main_window import MainWindow


class _RecordingSignal:
    """记录 connect 回调并可手动触发的伪信号。"""

    def __init__(self):
        self._connected = []

    def connect(self, fn, *args, **kwargs):
        self._connected.append(fn)

    def emit(self, *args):
        for fn in self._connected:
            fn(*args)

    def disconnect(self, *args, **kwargs):
        self._connected.clear()

    def count(self):
        return len(self._connected)


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


class _FakeLogTextEdit:
    """记录 flush 期间是否被写入；仅用于验证 manager 与 text_log 的接线。"""

    def __init__(self):
        self.calls = 0
        self.html = []

    def setUpdatesEnabled(self, value):
        pass

    def textCursor(self):
        return FakeLogCursor(self)

    def setTextCursor(self, cursor):
        pass

    def ensureCursorVisible(self):
        pass

    def clear(self):
        pass

    def append(self, html):
        self.html.append(html)

    def document(self):
        return FakeLogDocument(self)


class FakeLogCursor:
    """最小 QTextCursor 桩：记录 insertHtml 内容。"""

    class MoveOperation:
        End = "End"

    def __init__(self, owner):
        self.owner = owner

    def movePosition(self, op):
        return True

    def insertHtml(self, html):
        self.owner.html.append(html)
        self.owner.calls += 1


class FakeLogDocument:
    def __init__(self, owner):
        self.owner = owner

    def blockCount(self):
        return 0


class MainWindowLogIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cfg_path = os.path.join(self._tmp.name, "config.ini")

    def _make_window(self):
        w = MainWindow(config_manager=ConfigManager(config_path=self.cfg_path))
        # 注入桩 worker 工厂，避免真实 ffprobe/ffmpeg 线程导致 teardown 崩溃
        w.file_list_manager.duration_worker_cls = _FakeWorker
        w.file_list_manager.thumbnail_worker_cls = _FakeWorker
        w.info_interface.stop_worker = lambda: None
        self.addCleanup(w.file_list_manager.stop_workers)
        self.addCleanup(w.info_interface.stop_worker)
        self.addCleanup(w.deleteLater)
        return w

    # --- 1. manager 实例化与 attach ---
    def test_manager_instantiated_and_attached_to_text_log(self):
        w = self._make_window()
        self.assertIsInstance(w.log_manager, LogManager)
        # LogManager 在 _init_log_area 创建 text_log 后 attach
        self.assertIs(w.log_manager._text_log, w.text_log)
        # 不再持有旧的 mutex / list 缓冲
        self.assertFalse(hasattr(w, "log_mutex"))
        self.assertFalse(hasattr(w, "log_queue"))
        # text_log 仍在主窗口，便于原有样式/布局代码使用
        self.assertTrue(hasattr(w, "text_log"))

    def test_log_manager_is_not_running_implicit_timer(self):
        w = self._make_window()
        # LogManager 不应创建隐式 QTimer：它只有计时器所需的 flush 槽
        self.assertTrue(hasattr(w.log_manager, "flush"))
        self.assertFalse(hasattr(w.log_manager, "log_timer"))

    # --- 2. log() 转发到 manager ---
    def test_log_forwards_to_manager_queue(self):
        w = self._make_window()
        w.log_manager._drain()  # 清空 __init__ 欢迎语
        w.log("hello", "info")
        w.log("boom", "error")
        items = list(w.log_manager._queue.queue)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0][1], "hello")
        self.assertEqual(items[0][2], "info")
        self.assertEqual(items[1][1], "boom")
        self.assertEqual(items[1][2], "error")

    def test_worker_log_signal_connect_still_works(self):
        w = self._make_window()
        w.log_manager._drain()  # 清空 __init__ 欢迎语
        # 现有 worker 用 log_signal.connect(self.log) 无需改写
        signal = _RecordingSignal()
        signal.connect(w.log)
        signal.emit("from worker", "warning")
        items = list(w.log_manager._queue.queue)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][1], "from worker")
        self.assertEqual(items[0][2], "warning")

    # --- 3. process_log_queue 调用 manager.flush ---
    def test_process_log_queue_calls_manager_flush(self):
        w = self._make_window()
        with mock.patch.object(w.log_manager, "flush") as m_flush:
            w.process_log_queue()
            m_flush.assert_called_once_with()

    def test_flush_renders_into_text_log(self):
        w = self._make_window()
        # 用假控件替换真实 text_log，验证 log+flush 写入控件
        fake = _FakeLogTextEdit()
        w.log_manager.attach(fake)
        w.log("rendered line", "info")
        w.process_log_queue()
        self.assertGreater(fake.calls, 0)

    # --- 4. on_settings_save_requested 同步 log_cap ---
    def test_settings_save_syncs_log_cap(self):
        w = self._make_window()
        w.global_settings["log_cap"] = "1000"
        with mock.patch.object(w, "save_settings_file") as m_save:
            w.on_settings_save_requested({"log_cap": "5000"})
        self.assertEqual(w.log_manager._log_cap, 5000)
        self.assertEqual(w.global_settings["log_cap"], "5000")
        m_save.assert_called_once()

    def test_settings_save_invalid_log_cap_falls_back_to_max_blocks(self):
        w = self._make_window()
        w.log_manager.set_log_cap(9999)
        with mock.patch.object(w, "save_settings_file"):
            w.on_settings_save_requested({"log_cap": "not-a-number"})
        self.assertEqual(w.log_manager._log_cap, LOG_MAX_BLOCKS)

    # --- 5. 初始加载 / 恢复默认后同步 log_cap ---
    def test_initial_load_syncs_log_cap(self):
        w = self._make_window()
        # load_settings_to_ui 已在 __init__ 中执行，manager 应持有配置中的 cap
        self.assertEqual(w.log_manager._log_cap, int(w.global_settings["log_cap"]))

    def test_restore_defaults_syncs_log_cap(self):
        w = self._make_window()
        w.log_manager.set_log_cap(9999)
        w.global_settings["log_cap"] = "9999"
        w.restore_defaults()
        self.assertEqual(w.log_manager._log_cap, int(w.global_settings["log_cap"]))
        self.assertEqual(w.log_manager._log_cap, LOG_MAX_BLOCKS)

    # --- 6. closeEvent 停止日志 timer 与 manager ---
    def test_close_event_stops_log_timer_and_manager(self):
        w = self._make_window()
        # 记录 manager.stop() 是否被调用（wraps 保留真实行为）
        with (
            mock.patch.object(
                w.log_manager, "stop", wraps=w.log_manager.stop
            ) as m_stop,
            mock.patch.object(w.info_interface, "stop_worker"),
        ):
            w.closeEvent(QCloseEvent())
        m_stop.assert_called_once_with()
        # 关闭后 manager 拒绝新日志
        w.log_manager.log("after close", "info")
        self.assertTrue(w.log_manager._queue.empty())

    def test_close_event_does_not_touch_old_mutex_list(self):
        w = self._make_window()
        # 关闭路径不应再访问旧 mutex / list（它们已被移除）
        with mock.patch.object(w.info_interface, "stop_worker"):
            w.closeEvent(QCloseEvent())
        self.assertFalse(hasattr(w, "log_mutex"))
        self.assertFalse(hasattr(w, "log_queue"))

    def test_close_event_with_running_worker_prompts(self):
        w = self._make_window()
        with (
            mock.patch.object(
                w.transcode_controller, "is_running", return_value=True
            ) as m_run,
            mock.patch("ui.main_window.MessageDialog", autospec=True) as m_dlg,
        ):
            dlg = m_dlg.return_value
            dlg.yesButton = mock.Mock()
            dlg.cancelButton = mock.Mock()
            dlg.exec.return_value = False  # 用户选择留下
            w.closeEvent(QCloseEvent())
        # 用户取消关闭时不停止日志，事件被 ignore
        self.assertTrue(dlg.exec.called)
        self.assertEqual(m_run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
