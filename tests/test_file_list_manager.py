"""FileListManager 单元测试。

覆盖 brief 中要求的行为：
- 递归目录扫描过滤 VIDEO_EXTS、路径归一化、去重、返回新增数量
- snapshot() 返回副本，无法通过返回对象修改管理器状态
- remove/clear 清理选中文件、列表行、待处理队列、缓存与元数据
- worker 队列对时长/缩略图请求去重，并遵守 thread_limit_getter
- 进度/状态方法对未知路径是 no-op，对已知路径更新具名子控件

不依赖真实 ffprobe / 媒体文件；使用 FakeDurationWorker / FakeThumbnailWorker。
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QListWidget, QWidget
from qfluentwidgets import BodyLabel, IconWidget, ProgressBar

from config import VIDEO_EXTS
from ui.file_list_manager import FileListManager


# --- 桩对象 ---
class _FakeSignal:
    """记录连接回调并可触发的伪信号。"""

    def __init__(self):
        self.connected = []

    def connect(self, fn):
        self.connected.append(fn)

    def emit(self, *args):
        for fn in self.connected:
            fn(*args)


class FakeDurationWorker:
    """模拟 DurationWorker 的可控生命周期。"""

    def __init__(self, path, manager):
        self.path = path
        self.manager = manager
        self.started = False
        self._is_running = True
        self.result = _FakeSignal()
        self.finished = _FakeSignal()

    def connect(self, fn):
        self.fn = fn

    def deleteLater(self):
        pass

    def start(self):
        self.started = True

    def stop(self):
        self._is_running = False
        self.finished.emit()

    def isRunning(self):
        return self._is_running


class FakeThumbnailWorker:
    """模拟 ThumbnailWorker 的可控生命周期。"""

    def __init__(self, path, duration_sec, manager):
        self.path = path
        self.duration_sec = duration_sec
        self.manager = manager
        self.started = False
        self._is_running = True
        self.result = _FakeSignal()
        self.finished = _FakeSignal()

    def connect(self, fn):
        self.fn = fn

    def deleteLater(self):
        pass

    def start(self):
        self.started = True

    def stop(self):
        self._is_running = False
        self.finished.emit()

    def isRunning(self):
        return self._is_running


class FileListManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

        # 构造真实目录树
        self.sub = os.path.join(self.root, "sub")
        os.makedirs(self.sub)
        for rel in [
            "a.mkv",
            "b.mkv",
            "c.mp4",
            "skip.txt",
            os.path.join("sub", "nested.mp4"),
        ]:
            path = os.path.join(self.root, rel)
            with open(path, "w", encoding="utf-8") as f:
                f.write("x")

        # 显式注入的列表控件
        self.list_widget = QListWidget()
        self.placeholder = QWidget()
        self.count_label = BodyLabel("0")
        self.status_text_calls = []
        self.removed = []

        self.thread_limit = 2
        self.manager = FileListManager(
            self.list_widget,
            self.placeholder,
            self.count_label,
            thread_limit_getter=lambda: self.thread_limit,
            status_text_callback=lambda speed, eta: self.status_text_calls.append(
                (speed, eta)
            ),
            remove_callback=self.removed.append,
        )
        # 注入假的 worker 工厂，避免启动真实线程
        self.manager.duration_worker_cls = lambda path: FakeDurationWorker(
            path, self.manager
        )
        self.manager.thumbnail_worker_cls = lambda path, d: FakeThumbnailWorker(
            path, d, self.manager
        )

    def _mkfile(self, name, ext=".mkv"):
        path = os.path.join(self.root, name + ext)
        with open(path, "w", encoding="utf-8") as f:
            f.write("x")
        return path

    def _set_duration(self, path):
        """模拟时长线程完成，回填缓存并触发缩略图请求。"""
        self.manager.update_file_duration_label(path, "00:01:00", 60.0, {})

    # --- 扫描 / 去重 ---
    def test_scan_filters_and_normalizes(self):
        added = self.manager.add_source_paths(
            [self.root, os.path.join(self.root, "a.mkv")]
        )
        # 目录扫描出 4 个视频（3 顶层 + 1 nested），重复的 a.mkv 只算一次
        self.assertEqual(added, 4)
        paths = self.manager.selected_files
        self.assertEqual(len(paths), 4)
        self.assertTrue(all(p.endswith(VIDEO_EXTS) for p in paths))
        # 路径已归一化
        self.assertTrue(all(p == os.path.normpath(p) for p in paths))
        # txt 被过滤
        self.assertFalse(any(p.endswith(".txt") for p in paths))

    def test_dedup_across_calls(self):
        p = self._mkfile("dup")
        self.assertEqual(self.manager.add_source_paths([p]), 1)
        # 重复添加同一文件不增加数量
        self.assertEqual(self.manager.add_source_paths([p]), 0)
        self.assertEqual(len(self.manager.selected_files), 1)

    def test_add_ignores_empty_and_nonvideo(self):
        added = self.manager.add_source_paths(["", os.path.join(self.root, "skip.txt")])
        self.assertEqual(added, 0)
        self.assertEqual(self.manager.selected_files, [])

    def test_add_updates_count_label(self):
        self.manager.add_source_paths([self._mkfile("c1"), self._mkfile("c2")])
        self.assertEqual(self.count_label.text(), "2")

    # --- snapshot ---
    def test_snapshot_returns_copies(self):
        p = self._mkfile("snap")
        self.manager.add_source_paths([p])
        self.manager.file_metadata[p] = {"codec": "h264"}

        files, meta = self.manager.snapshot()
        self.assertIsInstance(files, list)
        self.assertEqual(files, self.manager.selected_files)
        self.assertEqual(meta, self.manager.file_metadata)

        # 修改返回的副本不影响管理器
        files.append("bogus.mkv")
        meta["bogus"] = "x"
        self.assertNotIn("bogus.mkv", self.manager.selected_files)
        self.assertNotIn("bogus", self.manager.file_metadata)
        # 修改嵌套元数据也不影响
        meta[p]["codec"] = "changed"
        self.assertEqual(self.manager.file_metadata[p]["codec"], "h264")

    def test_snapshot_empty(self):
        files, meta = self.manager.snapshot()
        self.assertEqual(files, [])
        self.assertEqual(meta, {})

    # --- remove / clear ---
    def test_remove_selected_file_purges_all_state(self):
        p1 = self._mkfile("r1")
        p2 = self._mkfile("r2")
        self.manager.add_source_paths([p1, p2])
        self.manager.file_metadata[p1] = {"codec": "h264"}
        self.manager.cached_durations[p1] = ("00:00:10", 10.0)
        self.manager.cached_thumbnails[p1] = object()
        self.manager.pending_dur_tasks.append(p1)
        self.manager.pending_thumb_tasks.append((p1, 10.0))

        self.manager.remove_selected_file(p1)

        self.assertNotIn(p1, self.manager.selected_files)
        self.assertIn(p2, self.manager.selected_files)
        self.assertNotIn(p1, self.manager.file_metadata)
        self.assertNotIn(p1, self.manager.cached_durations)
        self.assertNotIn(p1, self.manager.cached_thumbnails)
        self.assertNotIn(p1, self.manager.path_to_item)
        self.assertNotIn(p1, self.manager.pending_dur_tasks)
        self.assertFalse(any(t[0] == p1 for t in self.manager.pending_thumb_tasks))
        # 列表行数已减
        self.assertEqual(self.list_widget.count(), 1)
        # remove_callback 被调用
        self.assertIn(p1, self.removed)

    def test_remove_unknown_path_is_noop(self):
        self.manager.remove_selected_file("does-not-exist.mkv")
        self.assertEqual(self.manager.selected_files, [])
        self.assertEqual(self.list_widget.count(), 0)

    def test_clear_purges_everything(self):
        p = self._mkfile("clr")
        self.manager.add_source_paths([p])
        self.manager.file_metadata[p] = {"codec": "h264"}
        self.manager.pending_dur_tasks.append(p)
        self.manager.pending_thumb_tasks.append((p, 10.0))

        self.manager.clear()

        self.assertEqual(self.manager.selected_files, [])
        self.assertEqual(self.manager.path_to_item, {})
        self.assertEqual(self.list_widget.count(), 0)
        self.assertEqual(self.manager.pending_dur_tasks, [])
        self.assertEqual(self.manager.pending_thumb_tasks, [])
        self.assertEqual(self.manager.cached_durations, {})
        self.assertEqual(self.manager.cached_thumbnails, {})
        self.assertEqual(self.manager.file_metadata, {})
        self.assertEqual(self.count_label.text(), "0")

    # --- worker 队列去重 / 线程限制 ---
    def test_duration_queue_dedup_and_limit(self):
        p1 = self._mkfile("w1")
        p2 = self._mkfile("w2")
        p3 = self._mkfile("w3")
        self.manager.add_source_paths([p1, p2, p3])
        # 新文件尚未缓存时长，入队后被同步调度，thread_limit=2
        self.assertEqual(len(self.manager.active_dur_workers), 2)
        self.assertEqual(len(self.manager.pending_dur_tasks), 1)
        # 已在活动/等待中的路径不重复入队
        self.manager.get_file_duration(p1)
        self.assertEqual(len(self.manager.pending_dur_tasks), 1)

        # 完成一个 worker -> 队列前进
        first = self.manager.active_dur_workers.pop(
            next(iter(self.manager.active_dur_workers))
        )
        self.manager.on_duration_worker_finished(first.path)
        self.assertEqual(len(self.manager.active_dur_workers), 2)
        self.assertEqual(len(self.manager.pending_dur_tasks), 0)

    def test_thumbnail_queue_dedup_and_limit(self):
        p1 = self._mkfile("t1")
        p2 = self._mkfile("t2")
        p3 = self._mkfile("t3")
        self.manager.add_source_paths([p1, p2, p3])
        # 先回填时长，触发缩略图请求
        for p in [p1, p2, p3]:
            self._set_duration(p)
        # 3 个请求，thread_limit=2，2 个活动 + 1 个待处理
        self.assertEqual(len(self.manager.active_thumb_workers), 2)
        self.assertEqual(len(self.manager.pending_thumb_tasks), 1)

        # 已在活动或等待中的路径不重复入队
        self.manager.get_file_thumbnail(p1, 10.0)
        self.assertEqual(len(self.manager.pending_thumb_tasks), 1)

        # 完成一个 -> 队列前进
        first = self.manager.active_thumb_workers.pop(
            next(iter(self.manager.active_thumb_workers))
        )
        self.manager.on_thumbnail_worker_finished(first.path)
        self.assertEqual(len(self.manager.active_thumb_workers), 2)
        self.assertEqual(len(self.manager.pending_thumb_tasks), 0)

    def test_thread_limit_respected_dynamically(self):
        p1 = self._mkfile("d1")
        p2 = self._mkfile("d2")
        p3 = self._mkfile("d3")
        self.manager.add_source_paths([p1, p2, p3])
        self.assertEqual(len(self.manager.active_dur_workers), 2)
        # 调高线程限制，下一次调度可再启动
        self.thread_limit = 3
        self.manager.process_duration_queue()
        self.assertEqual(len(self.manager.active_dur_workers), 3)

    # --- 进度 / 状态更新 ---
    def test_update_progress_unknown_path_noop(self):
        self.manager.update_file_progress("missing.mkv", 50)
        self.assertEqual(self.list_widget.count(), 0)

    def test_update_progress_known_path_updates_child(self):
        p = self._mkfile("prog")
        self.manager.add_source_paths([p])
        item = self.list_widget.item(0)
        widget = self.list_widget.itemWidget(item)
        pbar = widget.findChild(ProgressBar, "pbar")
        self.assertIsNotNone(pbar)
        self.assertTrue(pbar.isHidden())

        self.manager.update_file_progress(p, 42)
        self.assertEqual(pbar.value(), 42)
        self.assertFalse(pbar.isHidden())

    def test_update_stats_unknown_path_noop(self):
        self.manager.update_file_stats("missing.mkv", "100 fps", "00:01")
        self.assertEqual(self.list_widget.count(), 0)
        self.assertEqual(self.status_text_calls, [])

    def test_update_stats_known_path_updates_child_and_callback(self):
        p = self._mkfile("stat")
        self.manager.add_source_paths([p])
        item = self.list_widget.item(0)
        widget = self.list_widget.itemWidget(item)
        lbl = widget.findChild(BodyLabel, "lbl_stats")
        self.assertIsNotNone(lbl)
        self.assertTrue(lbl.isHidden())

        self.manager.update_file_stats(p, "200 fps", "00:02")
        self.assertFalse(lbl.isHidden())
        self.assertIn("200 fps | 00:02", lbl.text())
        # 状态文本回调被调用（探针文本）
        self.assertTrue(self.status_text_calls)

    def test_update_status_unknown_path_noop(self):
        self.manager.update_file_status("missing.mkv", "processing")
        self.assertEqual(self.list_widget.count(), 0)

    def test_update_status_known_path_updates_icon(self):
        p = self._mkfile("stat2")
        self.manager.add_source_paths([p])
        item = self.list_widget.item(0)
        widget = self.list_widget.itemWidget(item)
        icon_w = widget.findChild(IconWidget, "status_icon")
        self.assertIsNotNone(icon_w)

        # 不应抛异常，状态图标已切换
        self.manager.update_file_status(p, "success")
        self.assertIsNotNone(icon_w)

    # --- stop_workers ---
    def test_stop_workers_clears_queues_and_stops_actives(self):
        p1 = self._mkfile("s1")
        p2 = self._mkfile("s2")
        self.manager.add_source_paths([p1, p2])
        for p in [p1, p2]:
            self._set_duration(p)
        # 启动后清空待处理，便于精确断言活动 worker 被 stop
        self.manager.pending_dur_tasks.clear()
        self.manager.pending_thumb_tasks.clear()

        active_dur = dict(self.manager.active_dur_workers)
        active_thumb = dict(self.manager.active_thumb_workers)
        self.assertTrue(active_dur)
        self.assertTrue(active_thumb)

        self.manager.stop_workers()

        self.assertEqual(self.manager.pending_dur_tasks, [])
        self.assertEqual(self.manager.pending_thumb_tasks, [])
        for w in active_dur.values():
            self.assertFalse(w._is_running)
        for w in active_thumb.values():
            self.assertFalse(w._is_running)


if __name__ == "__main__":
    unittest.main()
