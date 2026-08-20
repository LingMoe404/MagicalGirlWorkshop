# 审计安全与稳定性修复设计

日期：2026-08-19
范围：v1.4.0 后续 Phase 1 安全与稳定性问题

## 目标

修复代码审计中发现的五项问题，避免转码过程误报成功、覆盖无关文件、误删缓存目录、依赖探测超时阻塞，以及媒体分析报告中的外部输入污染 HTML。实现保持现有 PySide6/QThread 架构，不引入 HEVC 或大型重构。

## 设计

### 1. 输出落盘与磁盘冲突

`workers/transcode_paths.py` 的 `find_output_conflicts()` 在现有批次内部冲突检查之外，检查输出路径上的现有文件：

- 同一规范化输出由多个输入产生时，报告冲突。
- 输出路径与批次内另一输入相同时，报告冲突。
- 覆盖模式下，只有输出路径等于当前输入路径时允许已存在目标；输入扩展名变化产生的既有 `.mkv` 目标视为冲突。
- 非覆盖模式下，既有输出文件不直接在协调器阶段报错，以保留现有“生成后替换目标”的行为，但落盘失败不得报成功。

`EncoderWorker._handle_output()` 的落盘流程保证：

- 非覆盖模式只有 `shutil.move()` 成功后才发送成功日志、统计和状态信号。
- 移动失败时不预先删除已有目标；三次失败后走统一错误分支。
- 覆盖模式避免删除与当前输入无关的既有目标；源文件替换流程失败时尽可能恢复备份，并发送错误状态。

### 2. 缓存清理边界

启动自动清理统一使用 `workers.transcode_paths.cleanup_stale_sessions()`，只处理缓存根目录下名称以 `mgw-session-` 开头的旧目录，并跳过活动 session。移除对任意包含 `ab-av1` 子串的文件或目录的递归删除。

### 3. 依赖探测超时

`workers/dependency.py` 增加进程通信 helper。调用 `communicate(timeout=...)` 时若抛出 `subprocess.TimeoutExpired`，立即 `kill()`，再次 `communicate()` 回收 stdout/stderr，然后将该探测视为失败并继续后续检测。QSV、NVENC 及 HEVC 探测统一使用此 helper。

### 4. HTML 动态值转义

`workers/analyzer.py` 对路径、容器信息、视频/音频/字幕流字段及 ffprobe metadata 等外部值调用 `html.escape()`，内部生成的标签、样式和固定翻译文本保持原样。HTML 报告仍通过现有 `setHtml()` 展示。

## 测试设计

新增或扩展标准库 `unittest` 测试，覆盖：

1. 非覆盖模式三次移动失败时发送 error 而非 success。
2. 非覆盖模式移动失败时不删除既有目标。
3. 覆盖模式输入 `movie.mp4` 且已有 `movie.mkv` 时，在开工前报告冲突。
4. 缓存清理删除旧 `mgw-session-*`，但保留普通 `ab-av1-*` 目录。
5. 依赖探测超时会 kill 子进程并完成回收。
6. 媒体分析报告会转义恶意路径和 metadata。

## 验收标准

- 所有新增测试通过。
- 现有测试全部通过。
- `uv run ruff check .` 通过。
- `uv run ruff format --check .` 通过。
- `uv run python check_lang.py` 通过。
- 不新增面向用户的硬编码字符串，不改变现有语言键。
