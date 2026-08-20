# MainWindow 剩余职责拆分实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `ui/main_window.py` 中的文件列表、日志和转码生命周期职责迁移到独立模块，并把主窗口缩减到 1500 行以内，同时保持现有 Qt 信号和用户行为。

**Architecture:** 使用三个独立组件：`ui/file_list_manager.py` 管理文件列表状态、Qt 行控件和分析 worker；`ui/log_manager.py` 使用 `queue.Queue` 管理日志并在主线程刷新日志控件；`workers/transcode_controller.py` 作为 `EncodingCoordinator` 的无 UI 门面。`MainWindow` 只保留 UI 布局、对话框/InfoBar、输入校验和薄转发方法，通过显式 callback 或信号连接组件。

**Tech Stack:** Python 3.12、PySide6、QFluentWidgets、标准库 `queue`、unittest、uv、Ruff。

## Global Constraints

- Python 版本严格为 `>=3.12,<3.13`。
- 不使用 asyncio；保持 QThread/QObject/Signal/Slot 模型。
- worker 线程不得直接操作 UI；所有 UI 更新经 Qt 信号或主线程回调。
- 所有新增用户可见文本必须使用 `tr()`；不新增硬编码用户文案。
- Windows 子进程必须保留 `creationflags=get_subprocess_flags()`。
- 不修改 `tools/*.exe`，不使用 destructive Git 命令。
- 每项迁移先补测试，再接入主窗口，完成后运行对应测试。
- 保留现有 `EncodingCoordinator` 信号签名和 `MainWindow` 对外方法名作为兼容转发。

---

### Task 1: FileListManager 状态与列表迁移

**Files:**
- Create: `ui/file_list_manager.py`
- Create: `tests/test_file_list_manager.py`
- Modify: `ui/main_window.py:256-270,938-1015,1707-2265,2719-2771`
- Modify: `ui/__init__.py`

**Interfaces:**
- `FileListManager(list_widget, placeholder, count_label, thread_limit_getter, status_text_callback=None, remove_callback=None)`
- `add_source_paths(paths) -> int`
- `clear() -> None`
- `remove_selected_file(file_path) -> None`
- `snapshot() -> tuple[list[str], dict]`
- `stop_workers() -> None`
- `update_file_progress(filepath, percent) -> None`
- `update_file_stats(filepath, speed, eta) -> None`
- `update_file_status(filepath, status) -> None`
- `selected_files`, `file_metadata`, `path_to_item`, `active_dur_workers`, `active_thumb_workers` remain readable properties for compatibility.

- [ ] **Step 1: Write failing manager tests**
  - Test recursive directory scanning filters `VIDEO_EXTS`, normalizes paths, deduplicates and returns the added count.
  - Test `snapshot()` returns copies and cannot mutate manager state.
  - Test removal and clear purge selected files, list rows, pending queues, caches and metadata.
  - Test worker queue de-duplicates duration/thumbnail requests and respects `thread_limit_getter`.
  - Test progress/status methods are no-ops for unknown paths and update named child widgets for known paths.
  - Use `QT_QPA_PLATFORM=offscreen`, fake duration/thumbnail workers and existing unittest conventions; do not require ffprobe or real media files.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run `uv run python -m unittest tests.test_file_list_manager -v`.
  - Expected: import/class failures because the manager is not implemented.

- [ ] **Step 3: Implement the manager**
  - Move the existing list row construction and worker queue logic with behavior-preserving code.
  - Inject the list widgets and callbacks instead of storing `MainWindow`.
  - Keep `selected_files` order equal to list row order.
  - Keep LRU thumbnail eviction and duration-to-thumbnail chaining.
  - Use `stop_workers()` for `closeEvent`; do not call UI methods from worker threads.

- [ ] **Step 4: Run focused tests**
  - Run `uv run python -m unittest tests.test_file_list_manager -v`.
  - Expected: all manager tests pass.

- [ ] **Step 5: Integrate thin MainWindow wrappers**
  - Instantiate the manager after the list widgets exist.
  - Replace direct state fields with manager properties or aliases only where existing code still reads them.
  - Keep dialog/InfoBar methods (`handle_dropped_paths`, `choose_source_folder`, `browse_files`, `clear_all_selected_files`, `add_source_paths_from_info`) in `MainWindow` as wrappers.
  - Connect Coordinator file signals to manager methods and keep the current status-bar callback for probe text.
  - Delegate `closeEvent` worker shutdown to `FileListManager.stop_workers()`.

- [ ] **Step 6: Run integration regression tests**
  - Run `uv run python -m unittest tests.test_config_manager tests.test_ui_components -v`.
  - Expected: existing MainWindow/config and UI component tests pass.

- [ ] **Step 7: Commit the task**
  - Run `uv run ruff check ui/file_list_manager.py tests/test_file_list_manager.py ui/main_window.py` and `uv run ruff format --check ...`.
  - Commit only the FileListManager files with `git add` and `git commit -m "refactor: extract file list manager"`.

---

### Task 2: LogManager 队列与刷新迁移

**Files:**
- Create: `ui/log_manager.py`
- Create: `tests/test_log_manager.py`
- Modify: `ui/main_window.py:272-277,1036-1048,2284-2384,1614-1623,2719-2771`
- Modify: `ui/__init__.py`

**Interfaces:**
- `LogManager(text_log=None, log_cap=LOG_MAX_BLOCKS, theme_fn=isDarkTheme, translate=tr)`
- `attach(text_log) -> None`
- `log(msg, level="info") -> None`
- `flush() -> None`
- `set_log_cap(blocks) -> None`
- `stop() -> None`

- [ ] **Step 1: Write failing log tests**
  - Test queue insertion with timestamps and levels.
  - Test `queue.Queue` consumption, half-cap trimming, HTML escaping, newline and double-space conversion.
  - Test light/dark color selection through injected `theme_fn`.
  - Test `flush()` with a fake text edit and exception-safe behavior; do not require a running window.
  - Test `set_log_cap()` and `stop()`.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run `uv run python -m unittest tests.test_log_manager -v`.
  - Expected: import/class failures.

- [ ] **Step 3: Implement LogManager**
  - Replace `QMutex + list` with `queue.Queue` and drain batches without holding a lock while touching widgets.
  - Preserve current HTML structure, colors, icons, cap trimming and cursor behavior.
  - Keep the timer owned by `MainWindow`; `LogManager.flush()` is the timer slot.
  - Keep the existing translated messages at call sites; do not add untranslated strings.

- [ ] **Step 4: Run focused tests**
  - Run `uv run python -m unittest tests.test_log_manager -v`.
  - Expected: all log manager tests pass.

- [ ] **Step 5: Integrate MainWindow wrappers**
  - Instantiate `LogManager` after `text_log` creation and connect the existing `QTimer` to `process_log_queue` wrapper or directly to `flush`.
  - Make `log()` and `process_log_queue()` one-line compatibility methods.
  - Update `on_settings_save_requested` to call `set_log_cap()` after `global_settings` changes.
  - Stop the manager/timer in `closeEvent`.

- [ ] **Step 6: Run regression checks**
  - Run `uv run python -m unittest tests.test_log_manager tests.test_config_manager -v`.
  - Run `uv run ruff check ui/log_manager.py tests/test_log_manager.py ui/main_window.py`.

- [ ] **Step 7: Commit the task**
  - Commit with `git add ui/log_manager.py tests/test_log_manager.py ui/main_window.py ui/__init__.py && git commit -m "refactor: extract log manager"`.

---

### Task 3: TranscodeController 生命周期迁移

**Files:**
- Create: `workers/transcode_controller.py`
- Create: `tests/test_transcode_controller.py`
- Modify: `ui/main_window.py:2451-2603,2719-2771`
- Modify: `workers/__init__.py`

**Interfaces:**
- `TranscodeController(parent=None, coordinator_factory=EncodingCoordinator)`
- `start(config) -> bool`
- `stop() -> None`
- `set_paused(paused) -> None`
- `decide_error(task_id, decision) -> None`
- `wait(timeout=None) -> bool`
- `shutdown(timeout=2000) -> bool`
- `is_running() -> bool`
- `is_paused -> bool`
- Signals mirroring `EncodingCoordinator`: `log_signal`, `progress_total_signal`, `progress_current_signal`, `file_progress_signal`, `file_stats_signal`, `file_status_signal`, `finished_signal`, `ask_error_decision`, `concurrency_status_signal`.

- [ ] **Step 1: Write failing controller tests**
  - Test `start(config)` creates a coordinator, connects every signal, starts it and returns running status.
  - Test repeated `start()` does not replace a running coordinator.
  - Test pause/resume/stop/error decision forwarding.
  - Test `finished_signal` clears the controller reference.
  - Test `wait()` and `shutdown()` forward to coordinator and return explicit booleans.
  - Use fake coordinator/signals; do not instantiate MainWindow or real workers.

- [ ] **Step 2: Run focused tests and confirm failure**
  - Run `uv run python -m unittest tests.test_transcode_controller -v`.
  - Expected: import/class failures.

- [ ] **Step 3: Implement controller facade**
  - Compose an `EncodingCoordinator` instance; do not duplicate scheduling algorithms.
  - Forward the exact existing signals and clear the reference only after `finished_signal`.
  - Make `start()` return `False` when coordinator is absent/not running after `start()`.
  - Keep stop asynchronous; `shutdown()` calls stop then wait for the requested timeout.
  - Do not include DependencyWorker in this first facade; preserve its independent MainWindow lifecycle unless tests demonstrate a safe subsequent migration.

- [ ] **Step 4: Run focused tests**
  - Run `uv run python -m unittest tests.test_transcode_controller -v`.
  - Expected: all controller tests pass.

- [ ] **Step 5: Integrate start/pause/stop/finish wrappers**
  - Keep `start_task` validation and config construction in MainWindow.
  - Replace direct `EncodingCoordinator` creation and signal binding with controller construction and signal binding.
  - Keep button state changes in MainWindow callbacks.
  - Route error decisions to `controller.decide_error()` and pause/stop to controller methods.
  - Delegate close-time encoding wait to `controller.shutdown(2000)`.

- [ ] **Step 6: Run coordinator and UI regressions**
  - Run `uv run python -m unittest tests.test_coordinator tests.test_transcode_controller tests.test_config_manager -v`.
  - Run `uv run ruff check workers/transcode_controller.py tests/test_transcode_controller.py ui/main_window.py`.

- [ ] **Step 7: Commit the task**
  - Commit with `git add workers/transcode_controller.py tests/test_transcode_controller.py ui/main_window.py workers/__init__.py && git commit -m "refactor: extract transcode controller"`.

---

### Task 4: Package exports, roadmap and whole-branch verification

**Files:**
- Create: `ui/file_list/__init__.py` only if package conversion is needed; otherwise export classes from `ui/__init__.py`
- Create: `ui/logging/__init__.py` only if package conversion is needed; otherwise export classes from `ui/__init__.py`
- Create: `workers/transcode/__init__.py` only if package conversion is needed; otherwise export class from `workers/__init__.py`
- Modify: `ui/__init__.py`
- Modify: `workers/__init__.py`
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: Add stable exports without cycles**
  - Export `ConfigManager`, `FileListManager`, and `LogManager` from `ui/__init__.py` only if importing them does not eagerly import `MainWindow`; keep `MainWindow` import ordering safe.
  - Export `TranscodeController`, `build_media_report` and output strategy public functions from the appropriate package modules without importing UI.
  - Prefer flat modules plus package-level exports; create subpackages only if needed to satisfy independent `__init__.py` without changing import paths.

- [ ] **Step 2: Update roadmap status**
  - Mark `MainWindow` and `LogManager` complete only after all three managers are integrated.
  - Mark the 1500-line and export acceptance criteria complete only if verified by commands.

- [ ] **Step 3: Run full verification**
  - Run `uv run python -m unittest discover -s tests -v` and require all tests to pass.
  - Run `uv run ruff check .`.
  - Run `uv run ruff format --check . --exclude docs/CODE_AUDIT_2026-07-02.md`.
  - Run `uv run python check_lang.py`.
  - Run `wc -l ui/main_window.py` and require output at or below 1500 lines.
  - Run `rg -n '^class (FileListManager|LogManager|TranscodeController)' ui workers` and verify each class is in its extracted module.

- [ ] **Step 4: Review changed files**
  - Run `git diff --stat` and `git diff --check`.
  - Confirm no `tools/*.exe` changes and no unrelated user files were reverted.
