import ctypes
import os
import shutil
import time
import uuid
from collections import deque

from PySide6.QtCore import QObject, QTimer, Signal

from config import SAVE_MODE_SAVE_AS
from .batch_progress import calculate_batch_progress
from .concurrency_policy import DynamicConcurrencyPolicy
from .encoder import EncoderWorker
from .system_metrics import WindowsResourceSampler
from .transcode_paths import (
    build_final_output,
    cleanup_stale_sessions,
    create_session_root,
    create_task_paths,
    find_output_conflicts,
)
from .transcode_schedule import ACTIVE_STATES, BatchSchedule, TaskState


class EncodingCoordinator(QObject):
    log_signal = Signal(str, str)
    progress_total_signal = Signal(int)
    progress_current_signal = Signal(int)
    file_progress_signal = Signal(str, int)
    file_stats_signal = Signal(str, str, str)
    file_status_signal = Signal(str, str)
    finished_signal = Signal()
    ask_error_decision = Signal(str, str, str)
    concurrency_status_signal = Signal(str)

    def __init__(
        self,
        config,
        parent=None,
        worker_factory=EncoderWorker,
        timer_factory=QTimer,
        policy=None,
        metrics_sampler=None,
        clock=None,
        awake_setter=None,
    ):
        super().__init__(parent)
        self.config = dict(config)
        self.files = tuple(self.config.get("selected_files") or ())
        self.schedule = BatchSchedule(self.files)
        self._worker_factory = worker_factory
        self._metrics_sampler = metrics_sampler or WindowsResourceSampler()
        self._clock = clock or time.monotonic
        self._awake_setter = awake_setter or _set_system_awake

        mode = self.config.get("transcode_concurrency_mode", "manual")
        manual_limit = self.config.get("transcode_concurrency", 1)
        self.policy = policy or DynamicConcurrencyPolicy(
            mode=mode,
            manual_limit=manual_limit,
            auto_max=self.config.get("transcode_concurrency_auto_max", 3),
        )

        self._policy_timer = timer_factory(self)
        self._policy_timer.timeout.connect(self.evaluate_policy)
        self._workers_by_task = {}
        self._task_by_path = {}
        self._path_by_task = {}
        self._last_status = {}
        self._stages = {}
        self._encoding_speeds = {}
        self._progresses = {path: 0 for path in self.files}
        self._durations = {
            path: float(
                (self.config.get("metadata", {}).get(path) or {}).get(
                    "duration",
                    0,
                )
                or 0
            )
            for path in self.files
        }
        self._error_queue = deque()
        self._current_error = None
        self._error_tasks = set()
        self._session_root = None
        self._running = False
        self._paused = False
        self._stopping = False
        self._finished_emitted = False

    @property
    def active_workers(self):
        return tuple(
            self._workers_by_task[task_id]
            for task_id, path in self._path_by_task.items()
            if (
                task_id in self._workers_by_task
                and self.schedule.state_of(path) in ACTIVE_STATES
            )
        )

    @property
    def error_queue_size(self):
        return len(self._error_queue) + int(self._current_error is not None)

    @property
    def is_paused(self):
        return self._paused

    def isRunning(self):
        return self._running

    def start(self):
        if self._running:
            return

        self._running = True
        self._finished_emitted = False
        if not self.files:
            self.log_signal.emit("没有可转码的文件。", "error")
            self._finish()
            return

        conflicts = find_output_conflicts(
            self.files,
            self.config.get("save_mode"),
            self.config.get("export_dir", ""),
        )
        if conflicts:
            for conflict in conflicts:
                sources = "、".join(conflict.input_paths)
                self.log_signal.emit(
                    f"输出路径冲突：{conflict.output_path} <- {sources}",
                    "error",
                )
            self.schedule.cancel_all()
            self._finish()
            return

        try:
            self._prepare_session()
        except OSError as error:
            self.log_signal.emit(
                f"无法创建转码缓存目录：{error}",
                "error",
            )
            self.schedule.cancel_all()
            self._finish()
            return

        self._awake_setter(True)
        self._policy_timer.start(5000)
        self._emit_concurrency_status("批次开始")
        self._fill_slots()
        self._maybe_finish()

    def stop(self):
        if not self._running or self._stopping:
            return

        self._stopping = True
        self._policy_timer.stop()
        self.schedule.cancel_all()
        self._error_queue.clear()
        self._current_error = None
        self._error_tasks.clear()
        for worker in tuple(self._workers_by_task.values()):
            worker.stop()
        if not self._workers_by_task:
            self._finish()

    def wait(self, timeout=None):
        result = True
        for worker in tuple(self._workers_by_task.values()):
            worker_result = worker.wait(timeout)
            if worker_result is False:
                result = False
        return result

    def set_paused(self, paused):
        paused = bool(paused)
        if self._paused == paused:
            return
        self._paused = paused
        for worker in tuple(self._workers_by_task.values()):
            worker.set_paused(paused)
        if paused:
            self._policy_timer.stop()
            self._emit_concurrency_status("已暂停")
        elif self._running and not self._stopping:
            self._policy_timer.start(5000)
            self._emit_concurrency_status("已恢复")
            self._fill_slots()

    def evaluate_policy(self, hardware_resource_error=False):
        if not self._running or self._stopping:
            return
        try:
            resources = self._metrics_sampler.sample()
        except OSError as error:
            self.log_signal.emit(f"资源采样失败：{error}", "warning")
            return

        encoding_speeds = {
            path: speed
            for path, speed in self._encoding_speeds.items()
            if self._stages.get(path) == "encoding"
        }
        decision = self.policy.observe(
            self._clock(),
            encoding_speeds,
            resources,
            hardware_resource_error=hardware_resource_error,
            paused=self._paused,
        )
        if decision.reason:
            self._emit_concurrency_status(decision.reason)
        if not self._paused:
            self._fill_slots()

    def receive_error_decision(self, task_id, decision):
        if self._current_error is None:
            return
        current_task_id, _, _ = self._current_error
        if task_id != current_task_id:
            return
        if decision == "stop":
            self.stop()
            return

        worker = self._workers_by_task.get(task_id)
        if worker is not None:
            worker.receive_decision(decision)
        path = self._path_by_task.get(task_id)
        if path is not None:
            self.schedule.mark_terminal(path, TaskState.SKIPPED)
            self._progresses[path] = 100
            self.file_status_signal.emit(path, "skipped")
            self._emit_batch_progress()

        self._error_tasks.discard(task_id)
        self._current_error = None
        self._show_next_error()
        self._emit_concurrency_status("已跳过错误任务")
        self._maybe_finish()

    def _prepare_session(self):
        cache_root = os.path.abspath(
            os.fspath(self.config.get("cache_dir") or ".")
        )
        os.makedirs(cache_root, exist_ok=True)
        if self.config.get("save_mode") == SAVE_MODE_SAVE_AS:
            os.makedirs(self.config.get("export_dir") or ".", exist_ok=True)
        cleanup_stale_sessions(cache_root)
        self._session_root = create_session_root(
            cache_root,
            uuid.uuid4().hex,
        )

    def _fill_slots(self):
        if self._paused or self._stopping or not self._running:
            return
        started_any = False
        failed_any = False
        while True:
            started = self.schedule.fill_slots(
                self.policy.target_concurrency
            )
            if not started:
                break
            for path in started:
                try:
                    self._start_worker(path)
                    started_any = True
                except Exception as error:
                    failed_any = True
                    self.schedule.mark_terminal(path, TaskState.FAILED)
                    self.file_status_signal.emit(path, "error")
                    self.log_signal.emit(
                        f"[{os.path.basename(path)}] 无法启动任务：{error}",
                        "error",
                    )
            if len(self.schedule.active_files) >= (
                self.policy.target_concurrency
            ):
                break
        if failed_any:
            self._emit_batch_progress()
        if started_any or failed_any:
            self._emit_concurrency_status("任务补位")

    def _start_worker(self, path):
        task_id = uuid.uuid4().hex
        final_output = build_final_output(
            path,
            self.config.get("save_mode"),
            self.config.get("export_dir", ""),
        )
        task_paths = create_task_paths(
            self._session_root,
            task_id,
            final_output,
        )
        worker_config = dict(self.config)
        worker_config.update(
            {
                "selected_files": [path],
                "metadata": {
                    path: (self.config.get("metadata", {}).get(path) or {})
                },
                "manage_system_awake": False,
                "task_paths": task_paths,
            }
        )
        worker = self._worker_factory(worker_config)
        self._workers_by_task[task_id] = worker
        self._task_by_path[path] = task_id
        self._path_by_task[task_id] = path
        self._connect_worker(task_id, path, worker)
        worker.start()

    def _connect_worker(self, task_id, path, worker):
        worker.log_signal.connect(
            lambda message, level, p=path: self.log_signal.emit(
                f"[{os.path.basename(p)}] {message}",
                level,
            )
        )
        worker.file_progress_signal.connect(self._on_file_progress)
        worker.file_stats_signal.connect(self.file_stats_signal.emit)
        worker.file_status_signal.connect(self._on_file_status)
        worker.stage_signal.connect(self._on_stage)
        worker.encoding_speed_signal.connect(self._on_encoding_speed)
        worker.resource_error_signal.connect(
            lambda _path, message: self._on_resource_error(
                path,
                message,
            )
        )
        worker.ask_error_decision.connect(
            lambda title, content: self._on_worker_error(
                task_id,
                path,
                title,
                content,
            )
        )
        worker.finished.connect(
            lambda: self._on_worker_finished(task_id, path)
        )
        if hasattr(worker, "deleteLater"):
            worker.finished.connect(worker.deleteLater)

    def _on_file_progress(self, path, percent):
        self._progresses[path] = max(0, min(100, int(percent)))
        self.file_progress_signal.emit(path, int(percent))
        self._emit_batch_progress()

    def _on_file_status(self, path, status):
        self._last_status[path] = status
        self.file_status_signal.emit(path, status)

    def _on_stage(self, path, stage):
        self._stages[path] = stage
        if stage == "encoding":
            self.schedule.mark_encoding(path)

    def _on_encoding_speed(self, path, speed):
        self._encoding_speeds[path] = float(speed)

    def _on_resource_error(self, path, message):
        self.log_signal.emit(
            f"[{os.path.basename(path)}] 检测到硬件资源错误：{message}",
            "warning",
        )
        self.evaluate_policy(hardware_resource_error=True)

    def _on_worker_error(self, task_id, path, title, content):
        if task_id in self._error_tasks:
            return
        self._error_tasks.add(task_id)
        self.schedule.mark_waiting_decision(path)
        self._stages.pop(path, None)
        self._encoding_speeds.pop(path, None)
        self._error_queue.append((task_id, title, content))
        self._fill_slots()
        self._emit_concurrency_status("任务等待错误处理")
        self._show_next_error()

    def _show_next_error(self):
        if self._current_error is not None or not self._error_queue:
            return
        self._current_error = self._error_queue.popleft()
        self.ask_error_decision.emit(*self._current_error)

    def _on_worker_finished(self, task_id, path):
        if task_id not in self._workers_by_task:
            return
        self._workers_by_task.pop(task_id, None)
        self._task_by_path.pop(path, None)
        self._path_by_task.pop(task_id, None)
        self._stages.pop(path, None)
        self._encoding_speeds.pop(path, None)

        state = self.schedule.state_of(path)
        if state in ACTIVE_STATES:
            status = self._last_status.get(path)
            terminal_state = (
                TaskState.SUCCESS
                if status == "success"
                else TaskState.FAILED
            )
            self.schedule.mark_terminal(path, terminal_state)
            if terminal_state is TaskState.SUCCESS:
                self._progresses[path] = 100
            self._emit_batch_progress()
        elif state is TaskState.WAITING_DECISION:
            self.schedule.mark_terminal(path, TaskState.FAILED)
            self._remove_error_task(task_id)

        if not self._stopping:
            self._fill_slots()
            self._emit_concurrency_status("任务结束")
        self._maybe_finish()

    def _remove_error_task(self, task_id):
        self._error_tasks.discard(task_id)
        self._error_queue = deque(
            error
            for error in self._error_queue
            if error[0] != task_id
        )
        if (
            self._current_error is not None
            and self._current_error[0] == task_id
        ):
            self._current_error = None
            self._show_next_error()

    def _emit_batch_progress(self):
        progress = calculate_batch_progress(
            self._progresses,
            self._durations,
            self.schedule.terminal_files,
        )
        self.progress_total_signal.emit(progress)
        self.progress_current_signal.emit(progress)

    def _emit_concurrency_status(self, reason):
        target = self.policy.target_concurrency
        mode = self.config.get("transcode_concurrency_mode", "manual")
        if mode == "auto":
            limit = getattr(self.policy, "auto_max", 3)
            mode_text = f"自动并发 {target}/{limit} 路"
        else:
            mode_text = f"手动并发 {target} 路"
        status = (
            f"{mode_text}，活动 {len(self.schedule.active_files)} 路，"
            f"排队 {self.schedule.queued_count} 路，"
            f"等待处理 {self.schedule.waiting_count}"
        )
        if reason:
            status = f"{status}（{reason}）"
        self.concurrency_status_signal.emit(status)
        self.log_signal.emit(status, "info")

    def _maybe_finish(self):
        if self._workers_by_task:
            return
        if self._stopping or self.schedule.is_finished:
            self._finish()

    def _finish(self):
        if self._finished_emitted:
            return
        self._finished_emitted = True
        self._running = False
        self._policy_timer.stop()
        self._awake_setter(False)
        if self._session_root:
            shutil.rmtree(self._session_root, ignore_errors=True)
            self._session_root = None
        if self.schedule.is_finished:
            self.progress_total_signal.emit(100)
            self.progress_current_signal.emit(100)
        self.finished_signal.emit()


def _set_system_awake(keep_awake):
    try:
        flags = 0x80000003 if keep_awake else 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except (AttributeError, OSError):
        pass
