# v1.4.0 Dynamic Transcode Concurrency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe manual and automatic multi-file transcoding for QSV, NVENC, and AMF while preserving the existing per-file probing, fallback, and quality behavior.

**Architecture:** Keep `EncoderWorker` as the per-file execution engine and introduce a Qt `EncodingCoordinator` that assigns one file and one isolated cache directory to each worker. Put scheduling, automatic concurrency decisions, progress aggregation, output conflict detection, and Windows resource sampling in pure modules so their behavior can be tested without running FFmpeg or Qt event loops.

**Tech Stack:** Python 3.12, PySide6, standard-library `unittest`, `dataclasses`, `ctypes`, FFmpeg, ab-av1 0.10.4.

---

### Task 1: Preserve the existing encoding fixes as a clean baseline

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `README_JP.md`
- Modify: `config.py`
- Modify: `docs/releases/Releases1.3.1.md`
- Modify: `docs/superpowers/specs/2026-06-12-nvenc-rdp-fallback-design.md`
- Modify: `i18n/locales/en_US.py`
- Modify: `i18n/locales/ja_JP.py`
- Modify: `i18n/locales/zh_CN.py`
- Modify: `i18n/locales/zh_TW.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `workers/encoder.py`
- Create: `workers/ab_av1_result.py`
- Create: `workers/ffmpeg_retry.py`
- Create: `tests/__init__.py`
- Create: `tests/test_ab_av1_result.py`
- Create: `tests/test_ffmpeg_retry.py`
- Create: `docs/superpowers/plans/2026-06-12-ab-av1-result-parsing.md`
- Create: `docs/superpowers/plans/2026-06-12-nvenc-rdp-fallback.md`

- [x] **Step 1: Run the existing regression suite**

Run:

```powershell
uv run python -m unittest discover -s tests -v
```

Expected: 25 tests pass.

- [x] **Step 2: Run static verification**

Run:

```powershell
uv run python -m compileall workers tests i18n config.py
uv run ruff check workers\ab_av1_result.py workers\ffmpeg_retry.py tests config.py i18n\locales
uv run python .\check_lang.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop diff --check
```

Expected: all commands exit with code `0`; Git may print line-ending conversion warnings but no whitespace errors.

- [x] **Step 3: Commit only the existing fallback and parser work**

Run:

```powershell
git -c safe.directory=A:/Code/MagicalGirlWorkshop add CHANGELOG.md README.md README_EN.md README_JP.md config.py pyproject.toml uv.lock workers tests i18n docs/releases/Releases1.3.1.md docs/superpowers/specs/2026-06-12-nvenc-rdp-fallback-design.md docs/superpowers/plans/2026-06-12-ab-av1-result-parsing.md docs/superpowers/plans/2026-06-12-nvenc-rdp-fallback.md
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "fix: harden hardware encoding fallbacks"
```

Expected: a commit containing the already verified CUDA, subtitle, retry, and ab-av1 changes.

### Task 2: Add the pure batch scheduling model

**Files:**
- Create: `workers/transcode_schedule.py`
- Create: `tests/test_transcode_schedule.py`

- [x] **Step 1: Write failing tests for task states and slot filling**

Add:

```python
import unittest

from workers.transcode_schedule import BatchSchedule, TaskState


class BatchScheduleTests(unittest.TestCase):
    def test_fill_slots_starts_queued_files_in_order(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4", "c.mp4"])

        started = schedule.fill_slots(target_concurrency=2)

        self.assertEqual(started, ["a.mp4", "b.mp4"])
        self.assertEqual(schedule.state_of("a.mp4"), TaskState.PROBING)
        self.assertEqual(schedule.state_of("c.mp4"), TaskState.QUEUED)

    def test_waiting_decision_releases_a_slot(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4"])
        schedule.fill_slots(target_concurrency=1)

        schedule.mark_waiting_decision("a.mp4")

        self.assertEqual(schedule.fill_slots(1), ["b.mp4"])

    def test_lower_target_does_not_cancel_active_tasks(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4", "c.mp4"])
        schedule.fill_slots(target_concurrency=3)

        self.assertEqual(schedule.fill_slots(target_concurrency=1), [])
        self.assertEqual(
            schedule.active_files,
            ("a.mp4", "b.mp4", "c.mp4"),
        )
```

- [x] **Step 2: Run tests and verify RED**

Run:

```powershell
uv run python -m unittest tests.test_transcode_schedule -v
```

Expected: import failure because `workers.transcode_schedule` does not exist.

- [x] **Step 3: Implement the minimal schedule**

Create:

```python
from collections import deque
from enum import Enum


class TaskState(Enum):
    QUEUED = "queued"
    PROBING = "probing"
    ENCODING = "encoding"
    WAITING_DECISION = "waiting_decision"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATES = {TaskState.PROBING, TaskState.ENCODING}
TERMINAL_STATES = {
    TaskState.SUCCESS,
    TaskState.SKIPPED,
    TaskState.FAILED,
    TaskState.CANCELLED,
}


class BatchSchedule:
    def __init__(self, files):
        self._queue = deque(files)
        self._states = {path: TaskState.QUEUED for path in files}

    @property
    def active_files(self):
        return tuple(
            path
            for path, state in self._states.items()
            if state in ACTIVE_STATES
        )

    def state_of(self, path):
        return self._states[path]

    def fill_slots(self, target_concurrency):
        available = max(0, target_concurrency - len(self.active_files))
        started = []
        while available and self._queue:
            path = self._queue.popleft()
            if self._states[path] is not TaskState.QUEUED:
                continue
            self._states[path] = TaskState.PROBING
            started.append(path)
            available -= 1
        return started

    def mark_waiting_decision(self, path):
        self._states[path] = TaskState.WAITING_DECISION
```

- [x] **Step 4: Add tests for transitions and batch completion**

Cover:

```python
def test_terminal_states_finish_batch(self):
    schedule = BatchSchedule(["a.mp4", "b.mp4"])
    schedule.fill_slots(2)
    schedule.mark_terminal("a.mp4", TaskState.SUCCESS)
    schedule.mark_terminal("b.mp4", TaskState.SKIPPED)
    self.assertTrue(schedule.is_finished)

def test_stop_cancels_queued_and_active_files(self):
    schedule = BatchSchedule(["a.mp4", "b.mp4"])
    schedule.fill_slots(1)
    schedule.cancel_all()
    self.assertEqual(schedule.state_of("a.mp4"), TaskState.CANCELLED)
    self.assertEqual(schedule.state_of("b.mp4"), TaskState.CANCELLED)
```

Implement `mark_encoding`, `mark_terminal`, `cancel_all`, `is_finished`, `queued_count`, and `waiting_count`.

- [x] **Step 5: Run tests and commit**

Run:

```powershell
uv run python -m unittest tests.test_transcode_schedule -v
git -c safe.directory=A:/Code/MagicalGirlWorkshop add workers/transcode_schedule.py tests/test_transcode_schedule.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "feat: add batch transcode schedule"
```

Expected: all schedule tests pass.

### Task 3: Add automatic concurrency decisions

**Files:**
- Create: `workers/concurrency_policy.py`
- Create: `tests/test_concurrency_policy.py`

- [x] **Step 1: Write failing tests for manual and automatic limits**

Add:

```python
import unittest

from workers.concurrency_policy import (
    ConcurrencyMode,
    DynamicConcurrencyPolicy,
    ResourceSnapshot,
)


HEALTHY = ResourceSnapshot(
    cpu_percent=35.0,
    available_memory=8 * 1024**3,
    total_memory=16 * 1024**3,
)


class DynamicConcurrencyPolicyTests(unittest.TestCase):
    def test_manual_mode_uses_requested_limit(self):
        policy = DynamicConcurrencyPolicy(
            mode=ConcurrencyMode.MANUAL,
            manual_limit=4,
        )
        self.assertEqual(policy.target_concurrency, 4)

    def test_auto_mode_starts_at_one_and_caps_at_three(self):
        policy = DynamicConcurrencyPolicy(mode=ConcurrencyMode.AUTO)
        self.assertEqual(policy.target_concurrency, 1)
        self.assertEqual(policy.auto_max, 3)
```

- [x] **Step 2: Verify RED**

Run:

```powershell
uv run python -m unittest tests.test_concurrency_policy -v
```

Expected: import failure.

- [x] **Step 3: Implement enums, snapshots, and fixed limits**

Create immutable `ResourceSnapshot` and `ConcurrencyDecision` data classes. Validate manual limits to `1–4`, set auto maximum to `3`, and expose `target_concurrency`.

- [x] **Step 4: Add failing tests for stable-window upgrades**

Use short injected windows:

```python
def test_auto_mode_trials_next_level_after_stable_baseline(self):
    policy = DynamicConcurrencyPolicy(
        mode=ConcurrencyMode.AUTO,
        warmup_seconds=10,
        window_seconds=10,
        cooldown_seconds=10,
    )

    policy.observe(0, {"a": 1.0}, HEALTHY)
    decision = policy.observe(20, {"a": 1.0}, HEALTHY)

    self.assertEqual(decision.target_concurrency, 2)
    self.assertIn("trial", decision.reason)

def test_trial_is_accepted_when_total_throughput_improves_15_percent(self):
    policy = prepared_two_way_trial()

    policy.observe(30, {"a": 0.65, "b": 0.65}, HEALTHY)
    decision = policy.observe(50, {"a": 0.65, "b": 0.65}, HEALTHY)

    self.assertEqual(decision.target_concurrency, 2)
    self.assertTrue(decision.accepted)
```

The helper creates a policy whose one-way baseline is `1.0` and whose target has entered a two-way trial.

- [x] **Step 5: Implement stable observations**

The implementation must:

- Ignore probing-only calls represented by an empty speed map.
- Reset the observation window when the set of encoding task IDs changes unexpectedly.
- Store the accepted throughput baseline for each level.
- Start a trial only after a stable accepted-level window.
- Accept a trial when total median throughput improves by at least `15%`.
- Reject and blacklist the trial level when improvement is below `15%`.

- [x] **Step 6: Add failing overload tests**

Cover:

```python
def test_hardware_resource_error_reduces_target_immediately():
    policy = policy_at_target(3)
    decision = policy.observe(
        100,
        {"a": 0.4, "b": 0.4, "c": 0.4},
        HEALTHY,
        hardware_resource_error=True,
    )
    self.assertEqual(decision.target_concurrency, 2)

def test_low_memory_reduces_target():
    policy = policy_at_target(2)
    low_memory = ResourceSnapshot(
        cpu_percent=50,
        available_memory=512 * 1024**2,
        total_memory=16 * 1024**3,
    )
    self.assertEqual(
        policy.observe(100, {"a": 0.5, "b": 0.5}, low_memory)
        .target_concurrency,
        1,
    )

def test_paused_observation_does_not_advance_window():
    policy = DynamicConcurrencyPolicy(
        mode=ConcurrencyMode.AUTO,
        warmup_seconds=10,
        window_seconds=10,
    )
    policy.observe(0, {"a": 1.0}, HEALTHY)
    policy.observe(100, {"a": 1.0}, HEALTHY, paused=True)
    self.assertEqual(policy.target_concurrency, 1)
```

Also verify manual mode reduces from `4` to `3` after an explicit hardware resource error but does not react to ordinary speed changes. Implement high CPU, low memory, throughput regression, resource error, cooldown, and pause behavior.

- [x] **Step 7: Run and commit**

Run:

```powershell
uv run python -m unittest tests.test_concurrency_policy -v
uv run ruff check workers/concurrency_policy.py tests/test_concurrency_policy.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop add workers/concurrency_policy.py tests/test_concurrency_policy.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "feat: add dynamic concurrency policy"
```

### Task 4: Add progress, output conflict, and cache isolation helpers

**Files:**
- Create: `workers/transcode_paths.py`
- Create: `workers/batch_progress.py`
- Create: `tests/test_transcode_paths.py`
- Create: `tests/test_batch_progress.py`

- [x] **Step 1: Write failing output-path tests**

Cover overwrite, remain, save-as, case-insensitive collision, and cross-overwrite:

```python
def test_same_basename_in_save_as_is_rejected(tmp_path):
    inputs = [
        tmp_path / "one" / "movie.mp4",
        tmp_path / "two" / "movie.mkv",
    ]
    conflicts = find_output_conflicts(
        inputs,
        save_mode="Save As",
        export_dir=tmp_path / "out",
    )
    self.assertEqual(len(conflicts), 1)
```

- [x] **Step 2: Verify RED and implement path helpers**

Run:

```powershell
uv run python -m unittest tests.test_transcode_paths -v
```

Create:

```python
@dataclass(frozen=True)
class TaskPaths:
    task_dir: str
    ab_av1_dir: str
    temp_output: str
    final_output: str
```

Implement:

- `build_final_output(input_path, save_mode, export_dir)`
- `find_output_conflicts(inputs, save_mode, export_dir)`
- `create_session_root(cache_root, batch_id)`
- `create_task_paths(session_root, task_id, final_output)`
- `cleanup_stale_sessions(cache_root, active_session_ids, min_age_seconds)`

Use `os.path.abspath`, `os.path.normcase`, and `os.path.normpath` for comparisons.
The cleanup helper may delete only directories named `mgw-session-*` whose batch ID is not active and whose last modification time is older than the supplied threshold.

- [x] **Step 3: Write failing weighted-progress tests**

Cover:

```python
def test_progress_is_weighted_by_duration():
    result = calculate_batch_progress(
        progresses={"a": 100, "b": 50},
        durations={"a": 100, "b": 300},
        terminal_files=set(),
    )
    self.assertEqual(result, 62)

def test_terminal_failures_count_as_finished():
    result = calculate_batch_progress(
        progresses={"a": 20, "b": 0},
        durations={"a": 100, "b": 100},
        terminal_files={"a", "b"},
    )
    self.assertEqual(result, 100)
```

Also test unknown durations use the median known duration, and all-unknown durations use an arithmetic average. Add a stale-session test that creates one active session, one recent inactive session, and one old inactive session; only the old inactive directory may be removed.

- [x] **Step 4: Implement progress helpers and commit**

Implement:

- `map_probe_progress(strategy_index, strategy_count)`
- `map_encode_progress(ffmpeg_percent)`
- `calculate_batch_progress(progresses, durations, terminal_files)`

Run:

```powershell
uv run python -m unittest tests.test_transcode_paths tests.test_batch_progress -v
git -c safe.directory=A:/Code/MagicalGirlWorkshop add workers/transcode_paths.py workers/batch_progress.py tests/test_transcode_paths.py tests/test_batch_progress.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "feat: add transcode path and progress helpers"
```

### Task 5: Add Windows CPU and memory sampling

**Files:**
- Create: `workers/system_metrics.py`
- Create: `tests/test_system_metrics.py`

- [x] **Step 1: Write failing calculation tests**

Keep Windows calls behind injected readers:

```python
def test_cpu_usage_uses_idle_and_total_deltas():
    sampler = WindowsResourceSampler(
        times_reader=sequence_reader(
            (100, 1000, 500),
            (150, 1100, 600),
        ),
        memory_reader=lambda: (8 * 1024**3, 16 * 1024**3),
    )
    sampler.sample()
    result = sampler.sample()
    self.assertEqual(result.cpu_percent, 75.0)
```

The tuple is `(idle, kernel, user)` and CPU percentage is calculated from deltas while accounting for idle time being included in kernel time.

- [x] **Step 2: Verify RED and implement**

Implement `GetSystemTimes` and `GlobalMemoryStatusEx` with `ctypes`, returning the same `ResourceSnapshot` used by `concurrency_policy.py`.

- [x] **Step 3: Run Windows smoke test and commit**

Run:

```powershell
uv run python -m unittest tests.test_system_metrics -v
uv run python -c "from workers.system_metrics import WindowsResourceSampler; print(WindowsResourceSampler().sample())"
git -c safe.directory=A:/Code/MagicalGirlWorkshop add workers/system_metrics.py tests/test_system_metrics.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "feat: sample Windows resource pressure"
```

Expected: CPU is in `0–100`, available memory is positive, and tests pass.

### Task 6: Adapt `EncoderWorker` for one-file coordinated execution

**Files:**
- Modify: `workers/encoder.py`
- Modify: `tests/test_ffmpeg_retry.py`
- Modify: `tests/test_ab_av1_result.py`
- Create: `tests/test_encoder_coordination_contract.py`

- [x] **Step 1: Write failing coordination-contract tests**

Inspect the worker source and instantiate it without starting FFmpeg:

```python
class EncoderCoordinationContractTests(unittest.TestCase):
    def test_worker_exposes_stage_and_speed_signals(self):
        self.assertTrue(hasattr(EncoderWorker, "stage_signal"))
        self.assertTrue(hasattr(EncoderWorker, "encoding_speed_signal"))

    def test_coordinated_worker_does_not_manage_system_awake(self):
        worker = EncoderWorker({
            "selected_files": ["a.mp4"],
            "manage_system_awake": False,
        })
        self.assertFalse(worker.manage_system_awake)

    def test_worker_uses_precomputed_task_paths(self):
        source = inspect.getsource(EncoderWorker.run)
        self.assertIn("task_paths", source)
        self.assertNotIn("os.listdir(cache_dir)", source)
```

- [x] **Step 2: Verify RED**

Run:

```powershell
uv run python -m unittest tests.test_encoder_coordination_contract -v
```

- [x] **Step 3: Add the coordination contract**

Add:

```python
stage_signal = Signal(str, str)
encoding_speed_signal = Signal(str, float)
resource_error_signal = Signal(str, str)
```

Read these config fields:

- `task_paths`: serialized `TaskPaths`.
- `manage_system_awake`: defaults to `True` for backward compatibility.
- `log_prefix`: file name used when coordinator relays logs.

Behavior changes:

- Emit `PROBING` before ab-av1.
- Emit `ENCODING` before FFmpeg.
- Parse FFmpeg `speed=x` and emit a numeric speed.
- Emit `resource_error_signal` when the final FFmpeg failure matches hardware resource exhaustion markers.
- Use `task_paths.temp_output`, `task_paths.ab_av1_dir`, and `task_paths.final_output`.
- Delete only `task_paths.task_dir` in `finally`.
- Call `set_system_awake` only when `manage_system_awake` is true.

- [x] **Step 4: Preserve existing fallback behavior**

Run:

```powershell
uv run python -m unittest tests.test_ffmpeg_retry tests.test_ab_av1_result tests.test_encoder_coordination_contract -v
```

Expected: existing 25 tests and new contract tests pass.

- [x] **Step 5: Commit**

```powershell
git -c safe.directory=A:/Code/MagicalGirlWorkshop add workers/encoder.py tests/test_ffmpeg_retry.py tests/test_ab_av1_result.py tests/test_encoder_coordination_contract.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "refactor: prepare encoder worker for coordination"
```

### Task 7: Implement `EncodingCoordinator`

**Files:**
- Create: `workers/coordinator.py`
- Modify: `workers/__init__.py`
- Create: `tests/test_coordinator.py`

- [ ] **Step 1: Write failing manual scheduling tests using a fake worker**

Inject `worker_factory`:

```python
class FakeWorker:
    def __init__(self, config):
        self.config = config
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_manual_coordinator_starts_only_requested_workers():
    coordinator = EncodingCoordinator(
        batch_config=batch_config(files=["a", "b", "c"]),
        worker_factory=FakeWorker,
        timer_factory=FakeTimer,
    )
    coordinator.start()
    self.assertEqual(len(coordinator.active_workers), 2)
```

The batch config uses manual concurrency `2`.

- [ ] **Step 2: Verify RED and implement basic coordinator**

`EncodingCoordinator(QObject)` exposes signals compatible with the current UI:

```python
log_signal = Signal(str, str)
progress_total_signal = Signal(int)
progress_current_signal = Signal(int)
file_progress_signal = Signal(str, int)
file_stats_signal = Signal(str, str, str)
file_status_signal = Signal(str, str)
finished_signal = Signal()
ask_error_decision = Signal(str, str, str)
concurrency_status_signal = Signal(str)
```

The error signal arguments are `(task_id, title, content)`.

Implement:

- Output conflict preflight before any worker starts.
- Batch and task ID creation.
- Per-task config with one selected file and one `TaskPaths`.
- Active worker registry.
- Slot refill when workers finish or enter error waiting.
- Exactly one `finished_signal`.
- `isRunning()` compatibility for existing UI checks.
- `wait(timeout_ms)` that waits for all active worker threads during application shutdown.
- Batch-level system-awake activation at start and release after the final worker exits.
- Final session-root cleanup after all task directories are gone.

- [ ] **Step 3: Add failing error-queue tests**

Cover:

- First error emits a dialog request.
- Second error waits without another dialog.
- Resolving first emits the second.
- Waiting task is excluded from active slots.
- `stop` decision stops every active worker and cancels queued files.
- Duplicate errors for the same task are ignored.

- [ ] **Step 4: Implement error FIFO**

Add:

```python
def receive_error_decision(self, task_id, decision):
    if task_id != self._current_error_task:
        return
    if decision == "stop":
        self.stop()
        return
    worker = self._workers_by_task[task_id]
    worker.receive_decision("continue")
    self._current_error_task = None
    self._show_next_error()
```

For `continue`, call the matching worker's `receive_decision("continue")` and mark skipped when it exits. For `stop`, stop the whole batch.

- [ ] **Step 5: Add automatic-policy integration tests**

Inject fake time, metrics, and policy. Verify:

- Coordinator passes only encoding speeds to policy.
- A policy target increase starts one new queued worker.
- A policy target decrease does not stop active workers.
- A resource error is reported to the policy immediately.
- Pause stops timers and worker progression; resume restarts evaluation.

- [ ] **Step 6: Implement policy timer and progress aggregation**

Every five seconds:

- Sample Windows resources.
- Send active encoding speeds to policy.
- Apply target changes.
- Emit concurrency status.
- Recompute duration-weighted overall progress.

- [ ] **Step 7: Run and commit**

Run:

```powershell
uv run python -m unittest tests.test_coordinator -v
uv run ruff check workers/coordinator.py tests/test_coordinator.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop add workers/coordinator.py workers/__init__.py tests/test_coordinator.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "feat: coordinate concurrent encoding tasks"
```

### Task 8: Connect settings and the main window

**Files:**
- Modify: `config.py`
- Modify: `ui/interfaces.py`
- Modify: `ui/main_window.py`
- Modify: `i18n/locales/en_US.py`
- Modify: `i18n/locales/ja_JP.py`
- Modify: `i18n/locales/zh_CN.py`
- Modify: `i18n/locales/zh_TW.py`
- Create: `tests/test_concurrency_settings.py`

- [ ] **Step 1: Write failing configuration tests**

Assert:

```python
self.assertEqual(DEFAULT_SETTINGS["transcode_concurrency_mode"], "auto")
self.assertEqual(DEFAULT_SETTINGS["transcode_concurrency"], "2")
```

Inspect `AdvancedSettingsInterface` for a mode combo and manual spin box with range `1–4`.

- [ ] **Step 2: Verify RED and add settings UI**

Add:

- Mode combo values: `auto`, `manual`.
- Manual spin range: `1–4`.
- Manual spin enabled only when mode is `manual`.
- Save and load both settings.
- Rename the existing thread label to “元数据读取并发数”.
- Add matching keys to all four locales.

- [ ] **Step 3: Replace direct worker creation**

In `MainWindow.start_task`:

```python
self.worker = EncodingCoordinator(config, parent=self)
```

Add the two concurrency settings to the batch config. Connect coordinator signals, including:

```python
self.worker.ask_error_decision.connect(self.on_worker_error)
self.worker.concurrency_status_signal.connect(
    self.lbl_current.setText
)
```

Update `on_worker_error(task_id, title, content)` so the 30-second timer calls:

```python
self.worker.receive_error_decision(task_id, decision)
```

Pause, stop, close-event, and completion continue to call the coordinator's public methods. Remove the old `self.worker.finished.connect(self.worker.deleteLater)` connection because the coordinator is a `QObject`, not a `QThread`; connect only `finished_signal`.

- [ ] **Step 4: Run UI contract and locale tests**

Run:

```powershell
uv run python -m unittest tests.test_concurrency_settings -v
uv run python .\check_lang.py
uv run python -m compileall ui workers i18n config.py
```

- [ ] **Step 5: Commit**

```powershell
git -c safe.directory=A:/Code/MagicalGirlWorkshop add config.py ui/interfaces.py ui/main_window.py i18n tests/test_concurrency_settings.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "feat: expose transcode concurrency controls"
```

### Task 9: Migrate the release from 1.3.1 to 1.4.0

**Files:**
- Modify: `config.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `README_JP.md`
- Modify: `CHANGELOG.md`
- Move: `docs/releases/Releases1.3.1.md` to `docs/releases/Releases1.4.0.md`

- [ ] **Step 1: Write a failing version consistency test**

Create or extend `tests/test_version.py`:

```python
def test_all_release_versions_are_1_4_0(self):
    self.assertEqual(VERSION, "1.4.0")
    self.assertIn('version = "1.4.0"', Path("pyproject.toml").read_text())
    self.assertTrue(Path("docs/releases/Releases1.4.0.md").exists())
    self.assertFalse(Path("docs/releases/Releases1.3.1.md").exists())
```

- [ ] **Step 2: Verify RED and migrate release files**

Set version `1.4.0`, run `uv lock`, rename the release file, and merge the unreleased `v1.3.1` changelog entry into `v1.4.0`.

The release notes must include:

- CUDA-first NVENC decoding and CPU decode fallback.
- Strict subtitle retry classification.
- Correct ab-av1 result handling.
- QSV/NVENC/AMF concurrent file processing.
- Manual `1–4` and automatic `1–3` modes.
- Error FIFO, isolated task caches, output collision prevention, and weighted progress.

- [ ] **Step 3: Run and commit**

```powershell
uv run python -m unittest tests.test_version -v
git -c safe.directory=A:/Code/MagicalGirlWorkshop add config.py pyproject.toml uv.lock README.md README_EN.md README_JP.md CHANGELOG.md docs/releases tests/test_version.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop commit -m "docs: prepare v1.4.0 release"
```

### Task 10: Full verification and real concurrent smoke tests

**Files:**
- Verify all changed files

- [ ] **Step 1: Run the complete test suite**

```powershell
uv run python -m unittest discover -s tests -v
```

Expected: all tests pass with zero failures.

- [ ] **Step 2: Run compilation, lint, locales, and diff checks**

```powershell
uv run python -m compileall workers tests ui i18n config.py
uv run ruff check workers tests config.py i18n\locales
uv run python .\check_lang.py
git -c safe.directory=A:/Code/MagicalGirlWorkshop diff --check
```

- [ ] **Step 3: Run single-file compatibility smoke tests**

Using the temporary 20-second sample video, run the coordinator with concurrency `1` and NVENC. Verify:

- ab-av1 returns a trusted CRF.
- FFmpeg uses CUDA decode.
- The output is AV1 and larger than 1 KiB.
- Only the current task cache directory is removed.

Run QSV and AMF only when dependency detection reports them available; otherwise record them as hardware-unavailable rather than failed.

- [ ] **Step 4: Run a real two-file concurrency smoke test**

Create two distinct copies of the temporary sample in a temporary source directory. Run manual concurrency `2` in save-as mode and verify:

- Two workers overlap in time.
- Both outputs exist and pass `ffprobe`.
- No output path collisions occur.
- Each worker uses a separate task directory.
- Session cleanup leaves no task residue.

- [ ] **Step 5: Run automatic-policy coordinator smoke test**

Use injected short windows with real worker speed events to verify the coordinator can move from target `1` to `2` without terminating the first worker. Do not wait for production 60/90/120-second windows in this test.

- [ ] **Step 6: Review final repository state**

```powershell
git -c safe.directory=A:/Code/MagicalGirlWorkshop status --short
git -c safe.directory=A:/Code/MagicalGirlWorkshop log --oneline -12
git -c safe.directory=A:/Code/MagicalGirlWorkshop diff origin/main...HEAD --stat
```

Confirm no test videos, temporary cache directories, generated binaries, or unrelated files are tracked.
