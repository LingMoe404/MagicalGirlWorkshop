"""TranscodeController 单元测试。

覆盖 brief / 计划 Task 3 要求的行为：
- start(config) 创建 coordinator、连接所有信号、启动并返回运行状态
- 重复 start() 不替换正在运行的 coordinator
- pause/resume/stop/错误决策转发
- finished_signal 后清理 coordinator 引用
- wait() / shutdown() 转发给 coordinator 并返回显式布尔值
- 无 coordinator 时各方法安全（no-op / 默认返回值）

使用 FakeCoordinator + FakeSignal，不实例化 MainWindow / 真实 worker，
不依赖 ffmpeg / GPU / 真实 Qt 事件循环。
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from config import SAVE_MODE_SAVE_AS
from workers.transcode_controller import TranscodeController


# --- 桩对象 ---
class FakeSignal:
    """模拟 Qt Signal：记录 emit 并同步调用回调。"""

    def __init__(self):
        self._callbacks = []
        self.emissions = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        self.emissions.append(args)
        for callback in tuple(self._callbacks):
            callback(*args)


class FakeCoordinator:
    """模拟 EncodingCoordinator 的最小实现，记录控制器转发到的方法调用。"""

    instances = []  # noqa: RUF012

    def __init__(self, config, parent=None):
        self.config = config
        self.started = False
        self.start_calls = 0
        self.stopped = False
        self.paused = False
        self.running = False
        self.decisions = []
        self.wait_calls = []
        self.wait_result = True
        self.finish_on_start = False

        self.log_signal = FakeSignal()
        self.progress_total_signal = FakeSignal()
        self.progress_current_signal = FakeSignal()
        self.file_progress_signal = FakeSignal()
        self.file_stats_signal = FakeSignal()
        self.file_status_signal = FakeSignal()
        self.finished_signal = FakeSignal()
        self.ask_error_decision = FakeSignal()
        self.concurrency_status_signal = FakeSignal()
        FakeCoordinator.instances.append(self)

    def start(self):
        self.start_calls += 1
        self.started = True
        if self.finish_on_start:
            # 模拟"启动即结束"（空文件列表 / 输出冲突）的情况
            self.running = False
            self.finished_signal.emit()
        else:
            self.running = True

    def stop(self):
        self.stopped = True

    def set_paused(self, paused):
        self.paused = paused

    def receive_error_decision(self, task_id, decision):
        self.decisions.append((task_id, decision))

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        return self.wait_result

    def isRunning(self):
        return self.running

    @property
    def is_paused(self):
        return self.paused


class FakeCoordinatorFactory:
    """工厂：每次调用创建新的 FakeCoordinator，并注入共享配置。"""

    def __init__(self):
        self.instances = []
        self.wait_result = True
        self.finish_on_start = False

    def __call__(self, config, parent=None):
        coord = FakeCoordinator(config, parent)
        coord.wait_result = self.wait_result
        coord.finish_on_start = self.finish_on_start
        self.instances.append(coord)
        return coord


def sample_config():
    return {
        "selected_files": ["a.mp4", "b.mp4"],
        "metadata": {"a.mp4": {"duration": 100.0}, "b.mp4": {"duration": 100.0}},
        "encoder": "NVIDIA NVENC",
    }


class TranscodeControllerTests(unittest.TestCase):
    def setUp(self):
        FakeCoordinator.instances.clear()
        self.factory = FakeCoordinatorFactory()
        self.config = sample_config()

    def make_controller(self):
        return TranscodeController(coordinator_factory=self.factory)

    # --- start() 创建 / 连接 / 启动 / 返回运行状态 ---
    def test_start_creates_coordinator_and_returns_running(self):
        controller = self.make_controller()
        ok = controller.start(self.config)
        self.assertTrue(ok)
        self.assertIsNotNone(controller.coordinator)
        self.assertEqual(controller.coordinator.config, self.config)
        self.assertTrue(controller.coordinator.started)
        self.assertTrue(controller.coordinator.isRunning())
        self.assertTrue(controller.is_running())
        self.assertEqual(len(self.factory.instances), 1)

    def test_start_connects_all_signals(self):
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator

        received = {
            "log": [],
            "progress_total": [],
            "progress_current": [],
            "file_progress": [],
            "file_stats": [],
            "file_status": [],
            "ask_error": [],
            "concurrency": [],
        }
        controller.log_signal.connect(lambda *a: received["log"].append(a))
        controller.progress_total_signal.connect(
            lambda *a: received["progress_total"].append(a)
        )
        controller.progress_current_signal.connect(
            lambda *a: received["progress_current"].append(a)
        )
        controller.file_progress_signal.connect(
            lambda *a: received["file_progress"].append(a)
        )
        controller.file_stats_signal.connect(
            lambda *a: received["file_stats"].append(a)
        )
        controller.file_status_signal.connect(
            lambda *a: received["file_status"].append(a)
        )
        controller.ask_error_decision.connect(
            lambda *a: received["ask_error"].append(a)
        )
        controller.concurrency_status_signal.connect(
            lambda *a: received["concurrency"].append(a)
        )

        coord.log_signal.emit("hello", "info")
        coord.progress_total_signal.emit(50)
        coord.progress_current_signal.emit(60)
        coord.file_progress_signal.emit("a.mp4", 30)
        coord.file_stats_signal.emit("a.mp4", "2.0x", "00:30")
        coord.file_status_signal.emit("a.mp4", "encoding")
        coord.ask_error_decision.emit("task-1", "标题", "内容")
        coord.concurrency_status_signal.emit("手动并发 1 路")

        self.assertEqual(received["log"], [("hello", "info")])
        self.assertEqual(received["progress_total"], [(50,)])
        self.assertEqual(received["progress_current"], [(60,)])
        self.assertEqual(received["file_progress"], [("a.mp4", 30)])
        self.assertEqual(received["file_stats"], [("a.mp4", "2.0x", "00:30")])
        self.assertEqual(received["file_status"], [("a.mp4", "encoding")])
        self.assertEqual(received["ask_error"], [("task-1", "标题", "内容")])
        self.assertEqual(received["concurrency"], [("手动并发 1 路",)])

    def test_start_returns_false_when_coordinator_not_running_after_start(self):
        self.factory.finish_on_start = True
        controller = self.make_controller()
        ok = controller.start(self.config)
        self.assertFalse(ok)
        self.assertFalse(controller.is_running())
        # finished_signal 已同步清理引用
        self.assertIsNone(controller.coordinator)

    # --- 重复 start() 不替换运行中的 coordinator ---
    def test_repeated_start_does_not_replace_running_coordinator(self):
        controller = self.make_controller()
        self.assertTrue(controller.start(self.config))
        first = controller.coordinator

        self.assertTrue(controller.start(self.config))
        self.assertIs(controller.coordinator, first)
        self.assertEqual(len(self.factory.instances), 1)
        self.assertEqual(first.start_calls, 1)

    def test_start_after_finished_creates_new_coordinator(self):
        controller = self.make_controller()
        controller.start(self.config)
        first = controller.coordinator
        first.finished_signal.emit()
        self.assertIsNone(controller.coordinator)

        self.assertTrue(controller.start(self.config))
        self.assertIsNotNone(controller.coordinator)
        self.assertIsNot(controller.coordinator, first)
        self.assertEqual(len(self.factory.instances), 2)

    # --- finished_signal 清理引用并透传 ---
    def test_finished_signal_clears_reference_and_is_forwarded(self):
        controller = self.make_controller()
        finished = []
        controller.finished_signal.connect(lambda: finished.append(True))
        controller.start(self.config)
        coord = controller.coordinator

        coord.finished_signal.emit()

        self.assertEqual(finished, [True])
        self.assertIsNone(controller.coordinator)
        self.assertFalse(controller.is_running())

    # --- pause / resume / stop / 错误决策转发 ---
    def test_pause_and_resume_forwarded(self):
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator

        controller.set_paused(True)
        self.assertTrue(coord.paused)
        self.assertTrue(controller.is_paused)

        controller.set_paused(False)
        self.assertFalse(coord.paused)
        self.assertFalse(controller.is_paused)

    def test_stop_forwarded(self):
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator
        controller.stop()
        self.assertTrue(coord.stopped)

    def test_decide_error_forwarded(self):
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator
        controller.decide_error("task-1", "continue")
        controller.decide_error("task-2", "stop")
        self.assertEqual(
            coord.decisions,
            [("task-1", "continue"), ("task-2", "stop")],
        )

    # --- wait() / shutdown() ---
    def test_wait_forwards_timeout_and_returns_result(self):
        self.factory.wait_result = False
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator

        result = controller.wait(2000)
        self.assertFalse(result)
        self.assertEqual(coord.wait_calls, [2000])

    def test_wait_without_coordinator_returns_true(self):
        controller = self.make_controller()
        self.assertTrue(controller.wait(500))
        self.assertEqual(self.factory.instances, [])

    def test_shutdown_stops_then_waits(self):
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator

        result = controller.shutdown(2000)
        self.assertTrue(result)
        self.assertTrue(coord.stopped)
        self.assertEqual(coord.wait_calls, [2000])

    def test_shutdown_default_timeout_is_2000(self):
        controller = self.make_controller()
        controller.start(self.config)
        coord = controller.coordinator

        controller.shutdown()
        self.assertEqual(coord.wait_calls, [2000])

    def test_shutdown_without_coordinator_returns_true(self):
        controller = self.make_controller()
        self.assertTrue(controller.shutdown(100))

    # --- 无 coordinator 时各方法安全 ---
    def test_methods_are_safe_without_coordinator(self):
        controller = self.make_controller()
        controller.stop()
        controller.set_paused(True)
        controller.decide_error("task-1", "stop")
        self.assertFalse(controller.is_running())
        self.assertFalse(controller.is_paused)
        self.assertIsNone(controller.coordinator)


# --- 组合真实 EncodingCoordinator 的集成用例 ---
class RealCoordinatorWorker:
    """模拟 EncoderWorker：持有同名校信号，手动触发 finished。"""

    instances = []  # noqa: RUF012

    def __init__(self, config):
        self.config = config
        self.log_signal = FakeSignal()
        self.file_progress_signal = FakeSignal()
        self.file_stats_signal = FakeSignal()
        self.file_status_signal = FakeSignal()
        self.stage_signal = FakeSignal()
        self.encoding_speed_signal = FakeSignal()
        self.resource_error_signal = FakeSignal()
        self.ask_error_decision = FakeSignal()
        self.finished = FakeSignal()
        RealCoordinatorWorker.instances.append(self)

    def start(self):
        pass

    def stop(self):
        pass

    def set_paused(self, paused):
        pass

    def receive_decision(self, decision):
        pass

    def wait(self, timeout=None):
        return True


class RealTimer:
    def __init__(self, parent=None):
        self.timeout = FakeSignal()

    def start(self, milliseconds):
        pass

    def stop(self):
        pass


class RealMetrics:
    def sample(self):
        return object()


class RealCoordinatorFactory:
    """用 FakeWorker/FakeTimer 组装真实 EncodingCoordinator 的工厂。"""

    def __call__(self, config, parent=None):
        from workers.coordinator import EncodingCoordinator

        return EncodingCoordinator(
            config,
            parent=parent,
            worker_factory=RealCoordinatorWorker,
            timer_factory=RealTimer,
            metrics_sampler=RealMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )


class TranscodeControllerWithRealCoordinatorTests(unittest.TestCase):
    def setUp(self):
        RealCoordinatorWorker.instances.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        files = []
        for name in ("a.mp4", "b.mp4"):
            path = self.root / "source" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"video")
            files.append(str(path))
        self.files = files

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_config(self, mode="manual", concurrency=1):
        return {
            "selected_files": self.files,
            "metadata": {path: {"duration": 100.0} for path in self.files},
            "save_mode": SAVE_MODE_SAVE_AS,
            "export_dir": str(self.root / "out"),
            "cache_dir": str(self.root / "cache"),
            "transcode_concurrency_mode": mode,
            "transcode_concurrency": concurrency,
            "encoder": "NVIDIA NVENC",
            "preset": "4",
            "vmaf": 93.0,
            "audio_bitrate": "96k",
            "loudnorm": "",
            "loudnorm_mode": "Disable",
        }

    def test_real_coordinator_signals_flow_through_controller(self):
        controller = TranscodeController(coordinator_factory=RealCoordinatorFactory())
        log = []
        status = []
        finished = []
        controller.log_signal.connect(lambda *a: log.append(a))
        controller.file_status_signal.connect(lambda *a: status.append(a))
        controller.finished_signal.connect(lambda: finished.append(True))

        self.assertTrue(controller.start(self.make_config()))
        self.assertTrue(controller.is_running())
        self.assertIsNotNone(controller.coordinator)

        worker = RealCoordinatorWorker.instances[0]
        worker.log_signal.emit("probe ok", "info")
        worker.file_status_signal.emit(self.files[0], "encoding")

        self.assertTrue(any("probe ok" in m for m, _ in log))
        self.assertEqual(status, [(self.files[0], "encoding")])

        # 单并发下：先结束当前 worker，补位产生新 worker，直到批次全部完成
        self._finish_active_workers(controller)

        self.assertEqual(finished, [True])
        self.assertIsNone(controller.coordinator)
        self.assertFalse(controller.is_running())

    def test_real_coordinator_pause_stop_and_shutdown(self):
        controller = TranscodeController(coordinator_factory=RealCoordinatorFactory())
        controller.start(self.make_config())

        controller.set_paused(True)
        self.assertTrue(controller.is_paused)
        controller.set_paused(False)
        self.assertFalse(controller.is_paused)

        # stop 是异步的：请求后 coordinator 仍引用，直到所有 worker 发出 finished
        controller.stop()
        self.assertIsNotNone(controller.coordinator)
        self._finish_active_workers(controller)
        self.assertIsNone(controller.coordinator)

        # 已清理后 shutdown 应安全返回 True
        self.assertTrue(controller.shutdown(100))

    @staticmethod
    def _finish_active_workers(controller):
        """对真实 coordinator 驱动的 worker 结束循环。

        每轮只对「当前已创建但尚未结束」的 worker 发 finished，随后真实
        coordinator 会补位或完成批次；以 is_running() 退出，避免无限循环。
        """
        emitted = set()
        for _ in range(100):  # 保险上限，防止真实调度逻辑意外死循环
            if not controller.is_running():
                return
            progressed = False
            for w in list(RealCoordinatorWorker.instances):
                if id(w) not in emitted:
                    emitted.add(id(w))
                    w.finished.emit()
                    progressed = True
            if not progressed:
                break
        raise AssertionError("coordinator did not finish after worker emissions")


if __name__ == "__main__":
    unittest.main()
