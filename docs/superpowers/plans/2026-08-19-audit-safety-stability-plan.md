# 审计安全与稳定性修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复五项审计安全/稳定性问题，同时将直接相关逻辑拆成可测试的小 helper，避免误报成功、误删文件、启动阻塞和 HTML 外部输入污染。

**Architecture:** 保留现有 PySide6/QThread 和 EncoderWorker 公共信号契约。把输出落盘重试与安全替换收口为 `workers/encoder.py` 内的纯职责 helper，把进程超时回收收口为 `workers/dependency.py` helper，把缓存清理继续集中在 `workers/transcode_paths.py`，把报告动态值转义集中在 `workers/analyzer.py`。主窗口只改为调用已有安全清理函数，不做配置/日志大拆分。

**Tech Stack:** Python 3.12、PySide6、标准库 `unittest`、subprocess、shutil、html.escape、Ruff、uv。

## Global Constraints

- 仅支持 Python `>=3.12,<3.13`，不得引入 3.13+ 语法。
- 所有用户可见字符串继续使用 `tr()`，本轮不新增语言键。
- Worker 线程不得直接操作 UI，只通过现有 Signal/Slot。
- Windows 子进程继续传递 `creationflags=get_subprocess_flags()`。
- 不修改 `tools/*.exe`，不引入 HEVC，不进行 `main_window.py` 配置/日志系统的大规模重构。
- 每个新增行为必须有标准库 `unittest` 回归测试。

---

### Task 1: 输出路径磁盘冲突检查

**Files:**
- Modify: `workers/transcode_paths.py:48-87`
- Modify: `tests/test_transcode_paths.py`

**Interfaces:**
- Consumes: `build_final_output()`、`SAVE_MODE_OVERWRITE`、输入路径列表和 `export_dir`。
- Produces: `find_output_conflicts()` 继续返回 `tuple[OutputConflict, ...]`，新增覆盖模式下“输出目标已存在且不是当前输入”的冲突。

- [ ] **Step 1: 写覆盖模式已有同名目标的失败测试**

在 `tests/test_transcode_paths.py` 增加测试：创建临时目录中的 `movie.mp4` 与已有 `movie.mkv`，调用 `find_output_conflicts([movie.mp4], SAVE_MODE_OVERWRITE, "")`，断言返回一个冲突，且冲突包含两个路径。

- [ ] **Step 2: 运行目标测试确认失败**

运行：`uv run python -m unittest tests.test_transcode_paths.TranscodePathTests.test_overwrite_rejects_existing_different_extension_target -v`

预期：失败，因为当前实现只检查批次内输入，不检查磁盘已有目标。

- [ ] **Step 3: 实现最小冲突规则**

在 `find_output_conflicts()` 遍历每个输入时，对 `SAVE_MODE_OVERWRITE` 计算规范化输入/输出：当输出存在且规范化输出不等于规范化输入时，将当前输入和输出路径作为冲突参与者；避免对输出等于当前输入的 `.mkv` 文件报告冲突。

- [ ] **Step 4: 运行路径测试确认通过**

运行：`uv run python -m unittest tests.test_transcode_paths -v`

预期：全部通过。

- [ ] **Step 5: 运行 Ruff 检查本任务文件**

运行：`uv run ruff check workers/transcode_paths.py tests/test_transcode_paths.py`

预期：通过。

---

### Task 2: 安全输出落盘 helper 与失败状态

**Files:**
- Modify: `workers/encoder.py:844-983`
- Modify: `tests/test_encoder.py`

**Interfaces:**
- Consumes: `_handle_output()` 现有参数与信号。
- Produces: 新增模块级 `_move_with_retries(source, destination, replace_existing, retries=3)`，返回 `bool`；`_handle_output()` 仅在落盘成功后发送 success。

- [ ] **Step 1: 写非覆盖移动失败测试**

增加测试桩，使 `shutil.move` 连续三次抛出 `OSError`，并调用现有 worker 的 `_handle_output()`；断言返回值表示错误路径、`file_status_signal` 最后一次为 `"error"`、没有发送成功状态，且预先存在的目标文件仍存在。

- [ ] **Step 2: 运行目标测试确认失败**

运行：`uv run python -m unittest tests.test_encoder.EncoderWorkerTests.test_output_move_failure_does_not_report_success -v`

预期：失败，因为当前非覆盖分支三次失败后仍继续发 success。

- [ ] **Step 3: 实现 `_move_with_retries()`**

在 `workers/encoder.py` 模块级增加 helper：默认最多 3 次；`replace_existing=False` 时绝不主动删除目标，直接调用 `shutil.move()`；`replace_existing=True` 时使用 `os.replace()` 或等价替换行为；每次失败短暂等待，最终返回 `False`，不静默把失败当成功。

- [ ] **Step 4: 重写 `_handle_output()` 的非覆盖分支**

调用 helper 并检查返回值。返回 `False` 时抛出 `OSError(tr("log.encoder.error_move"...))` 或进入现有统一错误分支；只有成功才发送 success 日志、统计和状态。覆盖模式保留源文件 `.bak` 保护流程，并通过 helper 避免无关目标的先删后移。

- [ ] **Step 5: 运行 Encoder 测试确认通过**

运行：`uv run python -m unittest tests.test_encoder -v`

预期：现有测试与新增回归测试全部通过。

- [ ] **Step 6: 运行 Ruff 检查本任务文件**

运行：`uv run ruff check workers/encoder.py tests/test_encoder.py`

预期：通过。

---

### Task 3: 缓存清理收口

**Files:**
- Modify: `ui/main_window.py:2050-2090`（启动自动清理调用处）
- Modify: `workers/transcode_paths.py:118-147`（必要时补充安全边界）
- Modify: `tests/test_transcode_paths.py`
- Modify: `tests/test_ui_components.py` 或新增 `tests/test_cache_cleanup.py`

**Interfaces:**
- Consumes: `cleanup_stale_sessions(cache_root, active_session_ids, min_age_seconds, now)`。
- Produces: 启动自动清理只删除旧的 `mgw-session-*` 目录；普通 `ab-av1-*` 文件/目录不会被删除。

- [ ] **Step 1: 写普通 ab-av1 目录保留测试**

在路径测试中创建过期的 `mgw-session-old` 和过期的 `ab-av1-user-data` 目录，调用 `cleanup_stale_sessions()`，断言只删除 session 目录，普通目录仍存在。

- [ ] **Step 2: 运行目标测试确认清理边界**

运行：`uv run python -m unittest tests.test_transcode_paths.TranscodePathTests.test_cleanup_keeps_user_ab_av1_directory -v`

预期：若直接调用 helper，当前 helper 已应通过；随后定位主窗口是否绕过 helper，并为调用路径补测试或实现。

- [ ] **Step 3: 将主窗口启动清理改为调用 `cleanup_stale_sessions()`**

删除主窗口中按 `.temp.mkv`、`.ab-av1-` 和 `"ab-av1" in name` 的宽泛删除循环，导入并调用 `cleanup_stale_sessions(cache_dir, active_session_ids=(), min_age_seconds=24 * 60 * 60)`；保留现有日志/异常处理语义，不新增用户可见文案。

- [ ] **Step 4: 运行缓存相关测试与 Ruff**

运行：`uv run python -m unittest tests.test_transcode_paths -v` 和 `uv run ruff check ui/main_window.py workers/transcode_paths.py tests/test_transcode_paths.py`

预期：全部通过。

---

### Task 4: 依赖探测超时终止与回收

**Files:**
- Modify: `workers/dependency.py:70-220`
- Modify: `tests/test_dependency.py`（若不存在则创建）

**Interfaces:**
- Consumes: `subprocess.Popen` 对象和现有 `gpu_timeout`。
- Produces: `_communicate_with_timeout(proc, timeout)`；正常时返回 `(stdout, stderr)`，超时时 kill、回收输出并抛出/返回明确的超时结果供调用方记录失败。

- [ ] **Step 1: 写 fake process 超时测试**

创建可控 fake process：第一次 `communicate(timeout=...)` 抛出 `subprocess.TimeoutExpired`，记录 `kill()`，第二次 `communicate()` 返回字节输出；断言 helper 调用了 kill 且完成二次 communicate。

- [ ] **Step 2: 运行目标测试确认失败**

运行：`uv run python -m unittest tests.test_dependency -v`

预期：失败，因为 helper 尚不存在。

- [ ] **Step 3: 实现 `_communicate_with_timeout()`**

捕获 `subprocess.TimeoutExpired`，调用 `proc.kill()`，无 timeout 再调用 `proc.communicate()` 回收 stdout/stderr，然后重新抛出 `TimeoutExpired` 或返回 `(None, None)`；选择与现有外层 `except Exception` 兼容的明确异常路径，并确保调用方继续后续设备探测而不是阻塞。

- [ ] **Step 4: 替换 QSV/NVENC/HEVC 探测调用**

将各处 `proc.communicate(timeout=gpu_timeout)` 与 `proc_hevc.communicate(timeout=gpu_timeout)` 替换为 helper。保留现有错误日志和硬件能力判定，不改变编码器选择策略。

- [ ] **Step 5: 运行依赖测试与全套测试**

运行：`uv run python -m unittest tests.test_dependency -v`，再运行：`uv run python -m unittest discover -s tests -v`

预期：全部通过。

---

### Task 5: 媒体分析 HTML 转义

**Files:**
- Modify: `workers/analyzer.py:180-250`
- Modify: `tests/test_analyzer.py`

**Interfaces:**
- Consumes: ffprobe 返回的路径、format、stream 和 tags 动态值。
- Produces: 模块级 `_escape_html_value(value)`，返回 `html.escape(str(value))`；报告中的动态字段均经过该 helper。

- [ ] **Step 1: 写恶意路径与 metadata 测试**

让 fake ffprobe 返回包含 `<script>`、`&`、引号的路径和 metadata，调用报告生成逻辑；断言报告中没有原始 `<script>` 标签，且包含 `&lt;script&gt;` 和 `&amp;`。

- [ ] **Step 2: 运行目标测试确认失败**

运行：`uv run python -m unittest tests.test_analyzer.AnalysisWorkerTests.test_report_escapes_external_html_values -v`

预期：失败，因为当前动态字段直接拼接 HTML。

- [ ] **Step 3: 实现转义 helper 并替换动态插值**

导入 `html`，实现 `_escape_html_value()`；对 filepath、format 字段、stream 字段、metadata/tag 字段逐一应用。固定标签与翻译模板不转义。

- [ ] **Step 4: 运行分析测试与 Ruff**

运行：`uv run python -m unittest tests.test_analyzer -v` 和 `uv run ruff check workers/analyzer.py tests/test_analyzer.py`

预期：全部通过。

---

### Task 6: 全量验证与文档状态同步

**Files:**
- Modify: `docs/ROADMAP.md`（仅同步已完成的 EncoderWorker 拆分和本轮安全修复状态）
- Modify: `docs/superpowers/specs/2026-08-19-audit-safety-stability-design.md`（如实现细节与设计有必要的准确性更新）

- [ ] **Step 1: 运行完整验证命令**

运行：

```bash
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check .
uv run python check_lang.py
```

预期：所有命令退出码为 0。

- [ ] **Step 2: 检查工作树和改动范围**

运行：`git status --short` 与 `git diff --stat`，确认没有修改 `tools/*.exe`，没有无关大规模重构。

- [ ] **Step 3: 更新路线图状态**

将 `EncoderWorker.run()` 拆分标记、Phase 1 安全修复对应项和测试数量/状态更新为实际结果；不提前标记尚未完成的类型检查或覆盖率目标。

- [ ] **Step 4: 形成最终变更摘要**

记录测试数量、Ruff、格式和语言检查结果；若任何命令失败，报告真实失败输出，不声称已完成。
