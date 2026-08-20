"""MainWindow <-> FileListManager 集成测试。

验证主窗口渐进接入 FileListManager 后的接线行为：
- 主窗口实例化 manager 并显式注入 list_widget/placeholder/count label/回调
- 文件选择/拖放/清空包装与双击打开保留在主窗口
- snapshot() 用于构建转码 config，selected_files/file_metadata 行为兼容
- thread_limit_getter 把 global_settings['thread_limit'] 转 int，缺失/非法回退 4
- status_text_callback 恢复 ab-av1/探测 分支的状态栏行为
- closeEvent 路径使用 manager.stop_workers()
- Controller 信号连接到 manager 方法

不依赖真实 ffprobe/ffmpeg：通过注入 FakeController 隔离转码批次。
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from qfluentwidgets import IconWidget, ProgressBar

from i18n.translator import tr
from ui.config_manager import ConfigManager
from ui.file_list_manager import FileListManager
from ui.main_window import MainWindow
from workers import DurationWorker, ThumbnailWorker


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


class FakeController:
    """模拟 TranscodeController：捕获 start(config) 并暴露记录信号。"""

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


class MainWindowFileListIntegrationTests(unittest.TestCase):
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

    def _make_window(self, use_fake_workers=True, controller=None):
        w = MainWindow(
            config_manager=ConfigManager(config_path=self.cfg_path),
            transcode_controller=controller,
        )
        if use_fake_workers:
            # 注入桩 worker 工厂，避免真实 ffprobe/ffmpeg 线程导致 teardown 崩溃
            w.file_list_manager.duration_worker_cls = _FakeWorker
            w.file_list_manager.thumbnail_worker_cls = _FakeWorker
        self.addCleanup(w.file_list_manager.stop_workers)
        self.addCleanup(w.deleteLater)
        return w

    # --- 1. manager 实例化与显式注入 ---
    def test_manager_instantiated_with_injected_widgets(self):
        w = self._make_window()
        mgr = w.file_list_manager
        self.assertIsInstance(mgr, FileListManager)
        self.assertIs(mgr.list_widget, w.list_selected_files)
        self.assertIs(mgr.placeholder, w.lbl_selected_placeholder)
        self.assertIs(mgr.count_label, w.lbl_selected_count_right)

    def test_manager_uses_real_worker_factories(self):
        w = self._make_window(use_fake_workers=False)
        self.assertIs(w.file_list_manager.duration_worker_cls, DurationWorker)
        self.assertIs(w.file_list_manager.thumbnail_worker_cls, ThumbnailWorker)

    # --- 2. 文件选择/拖放/清空包装保留 ---
    def test_drop_wrappers_still_on_main_window(self):
        w = self._make_window()
        for name in [
            "handle_dropped_paths",
            "choose_source_folder",
            "browse_files",
            "clear_all_selected_files",
            "add_source_paths_from_info",
            "open_file_location",
            "add_source_paths",
        ]:
            self.assertTrue(hasattr(w, name), f"MainWindow.{name} 应保留")

    # --- 3. add_source_paths 转发到 manager ---
    def test_add_source_paths_delegates_to_manager(self):
        w = self._make_window()
        p = self._mkfile("c.mkv")
        added = w.add_source_paths([p])
        self.assertEqual(added, 1)
        self.assertIn(p, w.file_list_manager.selected_files)
        self.assertEqual(w.file_list_manager.count_label.text(), "1")

    def test_clear_all_selected_files_clears_manager_state(self):
        w = self._make_window()
        p = self._mkfile("d.mkv")
        w.add_source_paths([p])
        w.file_list_manager.file_metadata[p] = {"codec": "h264"}
        # 直接走 manager.clear()（clear_all_selected_files 对话框之外的清空逻辑）
        w.file_list_manager.clear()
        self.assertEqual(w.file_list_manager.selected_files, [])
        self.assertEqual(w.file_list_manager.file_metadata, {})
        self.assertEqual(w.list_selected_files.count(), 0)
        self.assertEqual(w.lbl_selected_count_right.text(), "0")

    # --- 4. snapshot 构建转码 config ---
    def test_start_task_config_uses_manager_snapshot(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        p = self._mkfile("snap.mkv")
        w.add_source_paths([p])
        w.file_list_manager.file_metadata[p] = {"codec": "h264", "duration": 120.0}

        w.start_task()

        self.assertEqual(len(controller.start_calls), 1)
        config = controller.start_calls[0]
        self.assertEqual(config["selected_files"], [p])
        self.assertEqual(config["metadata"], w.file_list_manager.file_metadata)
        # 快照应相互独立：修改返回的列表不影响 manager
        config["selected_files"].append("bogus.mkv")
        self.assertNotIn("bogus.mkv", w.file_list_manager.selected_files)

    # --- 5. thread_limit_getter 转 int / 回退 4 ---
    def test_thread_limit_getter_converts_to_int(self):
        w = self._make_window()
        w.global_settings["thread_limit"] = "3"
        self.assertEqual(w.file_list_manager.thread_limit_getter(), 3)

    def test_thread_limit_getter_falls_back_to_4(self):
        w = self._make_window()
        w.global_settings["thread_limit"] = "not-a-number"
        self.assertEqual(w.file_list_manager.thread_limit_getter(), 4)
        w.global_settings.pop("thread_limit", None)
        self.assertEqual(w.file_list_manager.thread_limit_getter(), 4)

    # --- 6. status_text_callback 恢复 ab-av1/探测 分支 ---
    def test_status_text_callback_probe_text(self):
        w = self._make_window()
        w.file_list_manager.status_text_callback("ab-av1 123fps", "00:05")
        self.assertIn("ab-av1", w.lbl_current.text())
        self.assertIn("00:05", w.lbl_current.text())

        w.file_list_manager.status_text_callback("探测 探测中", "00:06")
        self.assertIn("探测", w.lbl_current.text())

        # 普通编码恢复翻译后的当前标签
        w.file_list_manager.status_text_callback("350 fps", "00:10")
        self.assertNotIn("ab-av1", w.lbl_current.text())
        self.assertEqual(w.lbl_current.text(), tr("home.status_bar.current_label"))

    # --- 7. Controller 信号连接到 manager 方法 ---
    def test_coordinator_file_signals_connected_to_manager(self):
        controller = FakeController()
        w = self._make_window(controller=controller)
        p = self._mkfile("sig.mkv")
        w.add_source_paths([p])

        # 控制器信号在窗口初始化时连接；验证文件列表信号连到 manager 方法
        self.assertEqual(controller.file_progress_signal.count(), 1)
        self.assertEqual(controller.file_stats_signal.count(), 1)
        self.assertEqual(controller.file_status_signal.count(), 1)
        self.assertIn(
            w.file_list_manager.update_file_progress,
            controller.file_progress_signal._connected,
        )
        self.assertIn(
            w.file_list_manager.update_file_stats,
            controller.file_stats_signal._connected,
        )
        self.assertIn(
            w.file_list_manager.update_file_status,
            controller.file_status_signal._connected,
        )

    def test_coordinator_file_signals_drive_manager_updates(self):
        w = self._make_window()
        p = self._mkfile("sig2.mkv")
        w.add_source_paths([p])
        item = w.list_selected_files.item(0)
        widget = w.list_selected_files.itemWidget(item)
        pbar = widget.findChild(ProgressBar, "pbar")

        w.file_list_manager.update_file_progress(p, 42)
        self.assertEqual(pbar.value(), 42)
        w.file_list_manager.update_file_status(p, "success")
        self.assertIsNotNone(widget.findChild(IconWidget, "status_icon"))

    # --- 8. stop_workers 停止 manager 的活动 worker ---
    def test_stop_workers_stops_manager_active_workers(self):
        w = self._make_window()
        p = self._mkfile("close.mkv")
        w.add_source_paths([p])

        class FakeWorker:
            def __init__(self, *args, **kwargs):
                self.stopped = False

            def stop(self):
                self.stopped = True

            def deleteLater(self):
                pass

            def start(self):
                pass

        dur = FakeWorker()
        thumb = FakeWorker()
        w.file_list_manager.active_dur_workers[p] = dur
        w.file_list_manager.active_thumb_workers[p] = thumb

        # closeEvent 会委托到 manager.stop_workers()
        w.file_list_manager.stop_workers()
        self.assertTrue(dur.stopped)
        self.assertTrue(thumb.stopped)


if __name__ == "__main__":
    unittest.main()
