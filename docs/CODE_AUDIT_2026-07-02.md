# 代码审计报告 - 2026-07-02

审计对象：MagicalGirlWorkshop v1.4.0  
审计范围：转码执行、输出路径处理、并发协调、缓存清理、依赖检测、媒体信息展示与现有测试。  
审计方式：人工代码审查 + 现有单元测试 + Ruff 静态检查。  

## 结论摘要

本次审计未修改业务源码。现有单元测试全部通过，但发现 2 个高风险文件安全/数据安全问题、2 个中风险稳定性问题、1 个低风险 UI 注入问题。Ruff 当前未通过，主要是风格和维护性问题。

优先处理顺序建议：

1. 修复非覆盖模式移动失败后仍报成功的问题。
2. 修复覆盖模式可能删除同名现有 `.mkv` 的问题。
3. 收紧启动自动缓存清理的删除范围。
4. 修复依赖检测超时后没有 kill 子进程的问题。
5. 对媒体分析报告中的路径与 ffprobe 字段做 HTML 转义。

## 发现

### P1: 非覆盖模式可能失败但报成功，并可能先删除已有目标文件

位置：

- `workers/encoder.py:700`
- `workers/encoder.py:703`
- `workers/encoder.py:708`

问题：

`SAVE_MODE_REMAIN` 和 `SAVE_MODE_SAVE_AS` 分支会重试三次 `shutil.move(lp_temp, lp_dest)`，但没有记录移动是否成功。三次移动都失败后，代码仍继续发送成功日志和 `file_status_signal(..., "success")`。

更严重的是，移动前会执行：

```python
if os.path.exists(lp_dest): os.remove(lp_dest)
shutil.move(lp_temp, lp_dest)
```

如果目标文件已存在，且删除成功但移动失败，旧目标文件会丢失，同时 UI 仍可能显示任务成功。

影响：

- 用户以为文件已成功生成，实际输出文件可能不存在。
- 已有目标文件可能被删除。
- 批处理状态与真实文件状态不一致。

建议：

- 为非覆盖模式增加 `success = False`。
- 仅在 `shutil.move()` 成功后设置 `success = True` 并发送成功状态。
- 三次失败后抛出或进入统一错误分支。
- 避免先删目标再移动；优先移动到同目录临时替换名，或使用更安全的 replace/rename 流程。

### P1: 覆盖模式可能删除同名无关 `.mkv`

位置：

- `workers/transcode_paths.py:35`
- `workers/encoder.py:686`
- `workers/encoder.py:688`

问题：

`SAVE_MODE_OVERWRITE` 会把任意输入统一输出为同目录同 basename 的 `.mkv`：

```python
output_name = f"{base_name}.mkv"
```

如果输入是 `movie.mp4`，输出目标会是 `movie.mkv`。当前 `find_output_conflicts()` 只检测本批次输入之间的冲突，不检测磁盘上是否已经存在同名 `movie.mkv`。随后覆盖逻辑会删除 `lp_dest`，移动新输出，再删除原始输入。

触发场景：

同一目录存在：

- `movie.mp4` 作为本次输入
- `movie.mkv` 是用户已有的另一个文件

启动覆盖模式后，`movie.mkv` 会被替换，`movie.mp4` 也会被删除。

影响：

- 可能静默破坏用户已有文件。
- “覆盖源文件”的语义对非 `.mkv` 输入不等于只替换源文件。

建议：

- 覆盖模式下，如果输出扩展名与输入扩展名不同，并且目标 `.mkv` 已存在且不是当前输入，应在启动前报冲突。
- 或者覆盖模式始终先把源文件重命名为备份，再将输出移动到源文件的最终路径，并明确 UI 文案说明容器扩展名变化。
- 为该场景补充单元测试。

### P2: 启动自动缓存清理的删除范围过宽

位置：

- `ui/main_window.py:2068`
- `ui/main_window.py:2073`
- `ui/main_window.py:2080`

问题：

启动自动清理使用用户配置的缓存目录，然后删除顶层名称满足以下条件的文件或目录：

```python
f.endswith(".temp.mkv") or f.startswith(".ab-av1-") or "ab-av1" in f
```

其中 `"ab-av1" in f` 范围过宽，匹配后对目录执行 `shutil.rmtree(..., ignore_errors=True)`。

影响：

- 如果用户把缓存目录设置为较宽的目录，任何顶层名称包含 `ab-av1` 的正常目录都可能被递归删除。
- `ignore_errors=True` 会隐藏部分失败和异常状态，不利于审计。

建议：

- 只清理应用自有目录前缀，例如 `mgw-session-*`。
- 避免 substring 匹配目录名。
- 对清理目标做路径边界校验，确保目标位于缓存根目录之下。
- 手动清理和自动清理使用同一套安全清理函数。

### P2: GPU 依赖探测超时后可能仍阻塞

位置：

- `workers/dependency.py:73`
- `workers/dependency.py:94`
- `workers/dependency.py:114`
- `workers/dependency.py:132`

问题：

依赖检测中多处使用：

```python
with subprocess.Popen(...) as proc:
    proc.communicate(timeout=gpu_timeout)
```

如果 `communicate()` 超时，会抛出 `subprocess.TimeoutExpired`。当前代码只在外层捕获 `Exception` 并记录日志，没有先 kill 子进程。由于仍在 `with Popen(...)` 上下文里，退出上下文时可能等待子进程结束，导致超时保护失效。

影响：

- 启动时硬件探测可能卡住。
- 关闭窗口时依赖检测线程也可能无法快速退出。

建议：

- 捕获 `subprocess.TimeoutExpired` 后执行 `proc.kill()`，再 `proc.communicate()` 回收输出。
- 封装一个带超时和强制终止的 probe helper。
- 为 timeout 场景添加测试。

### P3: 媒体分析 HTML 未转义外部输入

位置：

- `workers/analyzer.py:209`
- `workers/analyzer.py:222`
- `workers/analyzer.py:242`
- `ui/interfaces.py:207`

问题：

媒体分析报告将文件路径和 ffprobe 输出字段直接拼入 HTML，并通过 `setHtml()` 渲染。文件名、路径、容器元数据、stream tag 等都属于外部输入。

影响：

- 恶意文件名或元数据可能污染报告 UI。
- 当前看主要是 UI 展示风险，但仍建议修复。

建议：

- 对所有来自路径和 ffprobe 的字符串字段使用 `html.escape()`。
- 保留内部生成的标签和样式，只转义动态值。

## 静态检查

命令：

```powershell
uv run ruff check .
```

结果：失败，报告 107 个问题。

主要类型：

- 未使用导入，例如 `main.py`、`ui/interfaces.py`、`workers/encoder.py`。
- 单行多语句，例如 `if x: return`。
- 裸 `except`。
- 无占位符的 f-string。

这些问题大多是维护性问题，不等同于本次发现的运行时数据安全问题。建议在修复高风险问题后单独做一次 Ruff 清理。

## 单元测试

命令：

```powershell
uv run python -m unittest discover -v
```

结果：通过。

统计：

- Ran 83 tests
- OK

说明：

现有测试覆盖了 ab-av1 解析、批量进度、并发策略、协调器、重试策略、路径冲突、系统指标和打包配置等模块。但本次 P1/P2 问题没有被现有测试覆盖。

## 建议补充的测试

1. `SAVE_MODE_REMAIN` / `SAVE_MODE_SAVE_AS` 下，目标移动连续失败时应标记 error，不应发送 success。
2. 非覆盖模式下目标文件已存在，移动失败时不应删除已有目标文件。
3. 覆盖模式下输入 `movie.mp4` 且同目录已有 `movie.mkv`，启动前应报冲突。
4. 自动缓存清理只删除 `mgw-session-*` 等应用自有目录，不删除普通 `ab-av1-*` 用户目录。
5. 依赖检测 timeout 后必须 kill 子进程。
6. 媒体分析报告中的路径和 ffprobe 字段应 HTML 转义。

