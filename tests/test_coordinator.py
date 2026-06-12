import tempfile
import unittest
from pathlib import Path

from config import SAVE_MODE_SAVE_AS
from workers.concurrency_policy import ConcurrencyDecision
from workers.coordinator import EncodingCoordinator


class FakeSignal:
    def __init__(self):
        self._callbacks = []
        self.emissions = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        self.emissions.append(args)
        for callback in tuple(self._callbacks):
            callback(*args)


class FakeWorker:
    instances = []

    def __init__(self, config):
        self.config = config
        self.started = False
        self.stopped = False
        self.paused = False
        self.decisions = []
        self.log_signal = FakeSignal()
        self.progress_total_signal = FakeSignal()
        self.progress_current_signal = FakeSignal()
        self.file_progress_signal = FakeSignal()
        self.file_stats_signal = FakeSignal()
        self.file_status_signal = FakeSignal()
        self.finished_signal = FakeSignal()
        self.ask_error_decision = FakeSignal()
        self.stage_signal = FakeSignal()
        self.encoding_speed_signal = FakeSignal()
        self.resource_error_signal = FakeSignal()
        self.finished = FakeSignal()
        FakeWorker.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def set_paused(self, paused):
        self.paused = paused

    def receive_decision(self, decision):
        self.decisions.append(decision)

    def wait(self, timeout=None):
        return True


class FakeTimer:
    def __init__(self, parent=None):
        self.timeout = FakeSignal()
        self.started_with = None
        self.stopped = False

    def start(self, milliseconds):
        self.started_with = milliseconds
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakePolicy:
    def __init__(self, target=1):
        self.target_concurrency = target
        self.auto_max = 3
        self.calls = []
        self.next_decision = ConcurrencyDecision(target)

    def observe(
        self,
        now,
        encoding_speeds,
        resources,
        hardware_resource_error=False,
        paused=False,
    ):
        self.calls.append(
            {
                "now": now,
                "speeds": dict(encoding_speeds),
                "resource_error": hardware_resource_error,
                "paused": paused,
            }
        )
        decision = self.next_decision
        self.target_concurrency = decision.target_concurrency
        return decision


class FakeMetrics:
    def sample(self):
        return object()


def batch_config(root, files, mode="manual", concurrency=2):
    return {
        "selected_files": files,
        "metadata": {
            path: {"duration": 100.0}
            for path in files
        },
        "save_mode": SAVE_MODE_SAVE_AS,
        "export_dir": str(Path(root) / "out"),
        "cache_dir": str(Path(root) / "cache"),
        "transcode_concurrency_mode": mode,
        "transcode_concurrency": concurrency,
        "encoder": "NVIDIA NVENC",
        "preset": "4",
        "vmaf": 93.0,
        "audio_bitrate": "96k",
        "loudnorm": "",
        "loudnorm_mode": "Disable",
    }


class EncodingCoordinatorTests(unittest.TestCase):
    def setUp(self):
        FakeWorker.instances.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_files(self, names):
        files = []
        for name in names:
            path = self.root / "source" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"video")
            files.append(str(path))
        return files

    def make_coordinator(self, files, **kwargs):
        config = batch_config(self.root, files, **kwargs)
        return EncodingCoordinator(
            config,
            worker_factory=FakeWorker,
            timer_factory=FakeTimer,
            metrics_sampler=FakeMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )

    def test_manual_coordinator_starts_only_requested_workers(self):
        files = self.make_files(["a.mp4", "b.mp4", "c.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=2,
        )

        coordinator.start()

        self.assertEqual(len(coordinator.active_workers), 2)
        self.assertEqual(len(FakeWorker.instances), 2)
        self.assertTrue(all(w.started for w in FakeWorker.instances))

    def test_finished_worker_releases_slot_and_starts_next_file(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=1,
        )
        coordinator.start()
        first = FakeWorker.instances[0]

        first.file_status_signal.emit(files[0], "success")
        first.finished_signal.emit()

        self.assertEqual(len(FakeWorker.instances), 2)
        self.assertTrue(FakeWorker.instances[1].started)

    def test_error_queue_emits_one_dialog_at_a_time(self):
        files = self.make_files(["a.mp4", "b.mp4", "c.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=2,
        )
        dialogs = []
        coordinator.ask_error_decision.connect(
            lambda *args: dialogs.append(args)
        )
        coordinator.start()
        first, second = FakeWorker.instances

        first.ask_error_decision.emit("first", "error one")
        second.ask_error_decision.emit("second", "error two")

        self.assertEqual(len(dialogs), 1)
        first_task_id = dialogs[0][0]
        coordinator.receive_error_decision(first_task_id, "continue")
        self.assertEqual(len(dialogs), 2)
        self.assertEqual(first.decisions, ["continue"])

    def test_waiting_error_releases_slot_for_queued_file(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=1,
        )
        coordinator.start()

        FakeWorker.instances[0].ask_error_decision.emit(
            "error",
            "failed",
        )

        self.assertEqual(len(FakeWorker.instances), 2)
        self.assertTrue(FakeWorker.instances[1].started)

    def test_stop_decision_stops_all_workers(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=2,
        )
        dialogs = []
        coordinator.ask_error_decision.connect(
            lambda *args: dialogs.append(args)
        )
        coordinator.start()
        FakeWorker.instances[0].ask_error_decision.emit(
            "error",
            "failed",
        )

        coordinator.receive_error_decision(dialogs[0][0], "stop")

        self.assertTrue(all(w.stopped for w in FakeWorker.instances))

    def test_duplicate_worker_error_is_queued_once(self):
        files = self.make_files(["a.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=1,
        )
        dialogs = []
        coordinator.ask_error_decision.connect(
            lambda *args: dialogs.append(args)
        )
        coordinator.start()
        worker = FakeWorker.instances[0]

        worker.ask_error_decision.emit("error", "failed")
        worker.ask_error_decision.emit("error", "failed")

        self.assertEqual(len(dialogs), 1)
        self.assertEqual(coordinator.error_queue_size, 1)

    def test_policy_increase_starts_new_worker(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        policy = FakePolicy(target=1)
        coordinator = EncodingCoordinator(
            batch_config(
                self.root,
                files,
                mode="auto",
                concurrency=2,
            ),
            worker_factory=FakeWorker,
            timer_factory=FakeTimer,
            policy=policy,
            metrics_sampler=FakeMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )
        coordinator.start()
        policy.next_decision = ConcurrencyDecision(
            target_concurrency=2,
            reason="trial concurrency 2",
            changed=True,
        )

        coordinator.evaluate_policy()

        self.assertEqual(len(FakeWorker.instances), 2)

    def test_policy_decrease_does_not_stop_active_workers(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        policy = FakePolicy(target=2)
        coordinator = EncodingCoordinator(
            batch_config(
                self.root,
                files,
                mode="auto",
                concurrency=2,
            ),
            worker_factory=FakeWorker,
            timer_factory=FakeTimer,
            policy=policy,
            metrics_sampler=FakeMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )
        coordinator.start()
        policy.next_decision = ConcurrencyDecision(
            target_concurrency=1,
            reason="resource pressure",
            changed=True,
        )

        coordinator.evaluate_policy()

        self.assertEqual(len(coordinator.active_workers), 2)
        self.assertFalse(any(w.stopped for w in FakeWorker.instances))

    def test_policy_receives_only_encoding_speeds(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        policy = FakePolicy(target=2)
        coordinator = EncodingCoordinator(
            batch_config(
                self.root,
                files,
                mode="auto",
                concurrency=2,
            ),
            worker_factory=FakeWorker,
            timer_factory=FakeTimer,
            policy=policy,
            metrics_sampler=FakeMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )
        coordinator.start()
        first, second = FakeWorker.instances
        first.stage_signal.emit(files[0], "encoding")
        first.encoding_speed_signal.emit(files[0], 0.8)
        second.stage_signal.emit(files[1], "probing")
        second.encoding_speed_signal.emit(files[1], 9.0)

        coordinator.evaluate_policy()

        self.assertEqual(policy.calls[-1]["speeds"], {files[0]: 0.8})

    def test_resource_error_is_forwarded_to_policy_immediately(self):
        files = self.make_files(["a.mp4"])
        policy = FakePolicy(target=1)
        coordinator = EncodingCoordinator(
            batch_config(
                self.root,
                files,
                mode="auto",
                concurrency=1,
            ),
            worker_factory=FakeWorker,
            timer_factory=FakeTimer,
            policy=policy,
            metrics_sampler=FakeMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )
        coordinator.start()

        FakeWorker.instances[0].resource_error_signal.emit(
            files[0],
            "out of memory",
        )

        self.assertTrue(policy.calls[-1]["resource_error"])

    def test_top_progress_uses_weighted_batch_progress(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=2,
        )
        total_progress = []
        current_progress = []
        coordinator.progress_total_signal.connect(total_progress.append)
        coordinator.progress_current_signal.connect(
            current_progress.append
        )
        coordinator.start()

        FakeWorker.instances[0].file_progress_signal.emit(files[0], 50)

        self.assertEqual(total_progress[-1], 25)
        self.assertEqual(current_progress[-1], 25)

    def test_pause_and_resume_propagate_to_workers(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        coordinator = self.make_coordinator(
            files,
            mode="manual",
            concurrency=2,
        )
        coordinator.start()

        coordinator.set_paused(True)
        self.assertTrue(all(w.paused for w in FakeWorker.instances))
        coordinator.set_paused(False)
        self.assertFalse(any(w.paused for w in FakeWorker.instances))

    def test_worker_start_failure_marks_file_failed_and_continues(self):
        files = self.make_files(["a.mp4", "b.mp4"])
        calls = []

        def worker_factory(config):
            calls.append(config["selected_files"][0])
            if len(calls) == 1:
                raise RuntimeError("worker creation failed")
            return FakeWorker(config)

        coordinator = EncodingCoordinator(
            batch_config(
                self.root,
                files,
                mode="manual",
                concurrency=1,
            ),
            worker_factory=worker_factory,
            timer_factory=FakeTimer,
            metrics_sampler=FakeMetrics(),
            clock=lambda: 100.0,
            awake_setter=lambda _: None,
        )
        statuses = []
        coordinator.file_status_signal.connect(
            lambda *args: statuses.append(args)
        )

        coordinator.start()

        self.assertEqual(calls, files)
        self.assertEqual(statuses[0], (files[0], "error"))
        self.assertEqual(len(FakeWorker.instances), 1)
        self.assertTrue(FakeWorker.instances[0].started)


if __name__ == "__main__":
    unittest.main()
