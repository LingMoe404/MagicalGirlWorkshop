# 三阶段职责拆分实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 EncoderWorker 输出策略、AnalysisWorker 媒体报告和 MainWindow 配置读写拆成三个独立模块，同时保持现有行为、信号契约和配置格式不变。

**Architecture:** 新增 `workers/output_strategy.py`、`workers/media_report.py` 和 `ui/config_manager.py`。前两个模块提供纯文件/纯渲染函数，ConfigManager 提供可注入路径的配置服务；原有 Worker/MainWindow 只保留编排、UI 映射和信号发送。三个任务互相独立，完成后由主代理审查接口和运行全套验证。

**Tech Stack:** Python 3.12、标准库 `unittest`、`configparser`、`html`、`shutil`、PySide6、现有 `tr()` 与配置常量。

## Global Constraints

- Python 严格使用 `>=3.12,<3.13`，不得引入 3.13+ 语法。
- 不改变 `EncoderWorker._handle_output()` 返回值和信号行为。
- 不改变 `AnalysisWorker.report_signal(str, bool)` 契约。
- 不改变 `config.ini` 的 `[Settings]`、`[Encoder:<name>]` section、键名和字符串值格式。
- MainWindow 不再直接导入或调用 `configparser`；保留 `global_settings` 和 `encoder_settings` 属性供现有业务使用。
- 新模块不操作 UI 控件；Worker 线程不直接操作 UI。
- 所有用户可见字符串继续使用现有 `tr()`，本轮不新增语言键。
- 不修改 `tools/*.exe`，不引入 HEVC，不进行无关重构。

---

### Task 1: 输出策略模块

**Files:**
- Create: `workers/output_strategy.py`
- Modify: `workers/encoder.py:46-982`
- Modify: `tests/test_encoder.py`
- Create: `tests/test_output_strategy.py`

**Interfaces:**
- Consumes: 当前 `_move_with_retries()`、覆盖模式 `.bak` 保护流程、`TaskPaths` 输出路径。
- Produces:
  - `move_with_retries(source, destination, replace_existing=False, retries=3) -> bool`
  - `save_non_overwrite_output(temp_output, final_output) -> None`
  - `save_overwrite_output(source_path, temp_output, final_output) -> None`

- [ ] **Step 1: 写输出策略失败测试**

在 `tests/test_output_strategy.py` 覆盖：非覆盖成功移动；非覆盖移动三次失败抛 `OSError` 且目标不被删除；同路径覆盖成功后源文件替换且 `.bak` 清理；覆盖移动失败后源文件恢复；`os.replace()` 抛 `OSError(errno.EXDEV, ...)` 时回退 `shutil.move()`。

- [ ] **Step 2: 运行新测试确认失败**

运行：`uv run python -m unittest tests.test_output_strategy -v`

预期：因 `workers.output_strategy` 尚不存在而失败。

- [ ] **Step 3: 实现独立输出策略模块**

将当前 `move_with_retries` 逻辑迁移到新模块；实现两个保存策略。`save_non_overwrite_output()` 不得预先删除目标；`save_overwrite_output()` 必须区分源路径等于最终路径和跨目录输出，并在失败时恢复 `.bak`。新模块不导入 Qt、不发送信号。

- [ ] **Step 4: 运行 helper 测试确认通过**

运行：`uv run python -m unittest tests.test_output_strategy -v`

预期：全部通过。

- [ ] **Step 5: 迁移 EncoderWorker 调用点**

删除 `workers/encoder.py` 内的 `_move_with_retries()`，导入新模块的三个函数；将 `_handle_output()` 中覆盖/非覆盖分支替换为策略调用，仅保留临时文件校验、耗时计算、成功/错误信号。保持返回 `(False, file_paused_time)` 和错误交互逻辑不变。

- [ ] **Step 6: 运行编码器回归测试与 Ruff**

运行：`uv run python -m unittest tests.test_encoder -v` 和 `uv run ruff check workers/output_strategy.py workers/encoder.py tests/test_output_strategy.py tests/test_encoder.py`

预期：全部通过。

---

### Task 2: 媒体报告渲染模块

**Files:**
- Create: `workers/media_report.py`
- Modify: `workers/analyzer.py:226-428`
- Modify: `tests/test_analyzer.py`
- Create: `tests/test_media_report.py`

**Interfaces:**
- Consumes: ffprobe JSON 字典、文件路径和当前主题状态。
- Produces: `build_media_report(data: dict, filepath: str, is_dark: bool = False) -> tuple[str, bool]`。

- [ ] **Step 1: 写报告渲染失败测试**

在 `tests/test_media_report.py` 增加测试：基础容器/视频/音频/字幕字段存在；恶意 filepath 和 `format_long_name` 被转义；MKV + AV1 返回 `should_hide=True` 并包含完美形态标记；MP4 + H264 不显示标记。

- [ ] **Step 2: 运行新测试确认失败**

运行：`uv run python -m unittest tests.test_media_report -v`

预期：因 `workers.media_report` 尚不存在而失败。

- [ ] **Step 3: 迁移 HTML 构造逻辑**

将 `AnalysisWorker.run()` 中颜色选择、动态字段转义、容器段、流段和完美形态标记迁移到 `build_media_report()`；保持现有翻译键、HTML 结构语义和 `should_hide` 规则。新模块不启动 ffprobe、不访问 Qt 控件。

- [ ] **Step 4: 运行报告模块测试确认通过**

运行：`uv run python -m unittest tests.test_media_report -v`

预期：全部通过。

- [ ] **Step 5: 简化 AnalysisWorker.run()`**

保留 ffprobe 命令、进程回收、JSON 解码和异常 HTML；调用 `build_media_report(data, self.filepath, isDarkTheme())` 并发送 `report_signal`。删除原有大段 HTML 拼装和重复的 `_escape_html_value()`。

- [ ] **Step 6: 运行分析测试与 Ruff**

运行：`uv run python -m unittest tests.test_analyzer tests.test_media_report -v` 和 `uv run ruff check workers/media_report.py workers/analyzer.py tests/test_media_report.py tests/test_analyzer.py`

预期：全部通过。

---

### Task 3: ConfigManager

**Files:**
- Create: `ui/config_manager.py`
- Modify: `ui/main_window.py:1-1650`
- Modify: `tests/test_ui_components.py` 或 `tests/test_config_manager.py`
- Create: `tests/test_config_manager.py`

**Interfaces:**
- Consumes: `DEFAULT_SETTINGS`、`ENCODER_CONFIGS`、`get_config_path()`、现有 config.ini section 格式。
- Produces:
  - `ConfigManager(config_path=None)`
  - `load() -> tuple[dict, dict]`
  - `save(settings: dict, encoder_settings: dict) -> None`
  - `merge_settings(updates: dict) -> dict`
  - `reset() -> tuple[dict, dict]`

- [ ] **Step 1: 写 ConfigManager 失败测试**

在 `tests/test_config_manager.py` 覆盖：临时路径无文件返回默认值；save 后 load 保留 Settings 与 Encoder section；缺失键补默认；`merge_settings()` 只改变指定键；`reset()` 返回深拷贝且不污染 `DEFAULT_SETTINGS`/`ENCODER_CONFIGS`。

- [ ] **Step 2: 运行测试确认失败**

运行：`uv run python -m unittest tests.test_config_manager -v`

预期：因 `ui.config_manager` 尚不存在而失败。

- [ ] **Step 3: 实现 ConfigManager**

使用 `configparser.ConfigParser()` 保持当前序列化行为；`config_path=None` 时调用 `get_config_path()`；以 `DEFAULT_SETTINGS.copy()` 和 `copy.deepcopy(ENCODER_CONFIGS)` 为基线；读取 `[Settings]` 和 `[Encoder:<name>]`；保存所有配置值为字符串；`merge_settings()` 只合并并返回，不隐式写盘；`reset()` 返回新的深拷贝。

- [ ] **Step 4: 运行 ConfigManager 测试确认通过**

运行：`uv run python -m unittest tests.test_config_manager -v`

预期：全部通过。

- [ ] **Step 5: 迁移 MainWindow 初始化和保存路径**

在 MainWindow 初始化时创建 `self.config_manager`；将 `load_settings_to_ui()` 的文件读取改为 `self.config_manager.load()`；将 `save_settings_file()` 改为委托 `self.config_manager.save()`；将 `on_settings_save_requested()` 的直接 configparser 读取改为 `self.config_manager.merge_settings(settings)` 后保存。保留 UI 映射、提示、主题和语言联动。

- [ ] **Step 6: 迁移重置逻辑并删除直接 configparser 使用**

将 `reset_all_settings()` 使用 `self.config_manager.reset()`，然后刷新 UI 并保存；删除 `main_window.py` 的 `configparser` 导入和直接文件读写。确认 `rg -n "configparser|ConfigParser|get_config_path" ui/main_window.py` 不再匹配配置实现。

- [ ] **Step 7: 运行配置、UI 和 Ruff 测试**

运行：`uv run python -m unittest tests.test_config_manager tests.test_ui_components -v` 和 `uv run ruff check ui/config_manager.py ui/main_window.py tests/test_config_manager.py`

预期：全部通过。

---

### Task 4: 主代理集成审查与全量验证

**Files:**
- Modify: `docs/ROADMAP.md`（只同步已实际完成的拆分状态）
- Modify: `docs/superpowers/specs/2026-08-19-three-stage-split-design.md`（如最终接口有变）

- [ ] **Step 1: 审查三个新模块的接口和依赖**

运行：`rg -n "from workers\.output_strategy|from workers\.media_report|from ui\.config_manager|configparser|_handle_output|def run" workers ui`，确认 Worker/MainWindow 只保留编排，三个新模块没有 Qt UI 操作或循环依赖。

- [ ] **Step 2: 运行完整测试与静态检查**

运行：

```bash
uv run python -m unittest discover -s tests -v
uv run ruff check .
uv run ruff format --check . --exclude docs/CODE_AUDIT_2026-07-02.md
uv run python check_lang.py
```

预期：全部退出码为 0。

- [ ] **Step 3: 检查文件规模与工作树**

运行：`wc -l workers/encoder.py workers/analyzer.py ui/main_window.py workers/output_strategy.py workers/media_report.py ui/config_manager.py` 和 `git status --short`。确认拆分模块已创建，巨型方法明显缩短，未修改 `tools/*.exe`。

- [ ] **Step 4: 更新路线图**

仅将输出策略、媒体报告和 ConfigManager 标为已完成；不提前标记 MainWindow 全面拆分、类型检查、覆盖率目标或日志系统拆分。
