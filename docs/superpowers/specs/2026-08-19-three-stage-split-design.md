# 三阶段职责拆分设计

日期：2026-08-19
范围：EncoderWorker 输出策略、AnalysisWorker 媒体报告、MainWindow ConfigManager

## 目标

按既定顺序将三个高耦合职责拆成独立、可测试模块，同时保持现有用户行为、Qt 信号契约、配置文件格式和多语言行为不变。

## 总体原则

- 保留 `EncoderWorker._handle_output()`、`AnalysisWorker.report_signal`、`MainWindow.global_settings` 和 `MainWindow.encoder_settings` 的外部兼容接口。
- 新模块优先使用标准库和纯函数，不依赖 Qt 事件循环。
- 每一段迁移先写独立测试，再替换调用点；迁移完成后删除重复实现。
- 不修改 `tools/*.exe`、不引入 HEVC、不改变 config.ini 的 section 名称和键名。

## 阶段一：输出策略模块

新增 `workers/output_strategy.py`，负责最终文件落盘和恢复，不负责日志或 Qt 信号。

### 接口

```python
def move_with_retries(source, destination, replace_existing=False, retries=3) -> bool

def save_non_overwrite_output(temp_output, final_output) -> None

def save_overwrite_output(source_path, temp_output, final_output) -> None
```

- `move_with_retries()` 保留当前同盘 `os.replace()`、跨盘 `EXDEV` 回退 `shutil.move()` 的行为。
- `save_non_overwrite_output()` 不预先删除目标，移动失败抛出 `OSError`。
- `save_overwrite_output()` 对源文件等于最终目标的情况使用 `.bak`，成功后删除备份，失败时恢复；源文件与最终目标不同的情况替换目标并在成功后删除源文件。
- Worker 只负责校验临时文件、计算耗时、调用策略、发出成功/错误信号。

## 阶段二：媒体报告模块

新增 `workers/media_report.py`，负责把 ffprobe JSON 数据渲染为报告 HTML。

### 接口

```python
def build_media_report(data: dict, filepath: str, is_dark: bool = False) -> tuple[str, bool]
```

模块负责：

- 主题颜色选择。
- 路径、format、stream、tags 等外部值的 HTML 转义。
- 容器、视频、音频、字幕区块生成。
- MKV + AV1 完美形态标记和 `should_hide` 结果。
- 保持现有翻译键和 HTML 内容语义。

`AnalysisWorker.run()` 只负责构造 ffprobe 命令、收集输出、解码 JSON、调用 `build_media_report()`，然后发出现有 `report_signal(str, bool)`。

## 阶段三：ConfigManager

新增 `ui/config_manager.py`，负责配置文件读写和默认值合并，不操作 UI 控件。

### 接口

```python
class ConfigManager:
    def __init__(self, config_path=None): ...
    def load(self) -> tuple[dict, dict]: ...
    def save(self, settings: dict, encoder_settings: dict) -> None: ...
    def merge_settings(self, updates: dict) -> dict: ...
    def reset(self) -> tuple[dict, dict]: ...
```

行为约束：

- 默认路径仍由 `get_config_path()` 提供；测试可注入临时路径。
- `load()` 从 `[Settings]` 加载全局设置，从 `[Encoder:<name>]` 加载编码器设置，并以 `DEFAULT_SETTINGS` / `ENCODER_CONFIGS` 为基线合并。
- `save()` 保持现有 section 名、键名、字符串值和布尔值格式。
- `merge_settings()` 读取当前配置后合并局部更新，并返回完整全局设置；不自动写文件。
- `reset()` 返回默认全局设置和默认编码器设置，不自动写文件；由 MainWindow 决定何时保存和刷新 UI。
- MainWindow 保留 UI 值到字典的转换、提示框、主题/语言联动，但删除 `configparser` 直接调用和 config.ini 文件读写。

## 测试设计

### 输出策略

- 非覆盖模式成功移动。
- 非覆盖模式移动失败不删除既有目标。
- 覆盖源文件时成功替换并删除备份。
- 覆盖失败时恢复源文件备份。
- 跨磁盘 `EXDEV` 回退到 `shutil.move()`。

### 媒体报告

- 容器、视频、音频、字幕报告保持关键字段。
- 恶意 filepath、format_long_name、stream tag 被转义。
- MKV + AV1 返回 `should_hide=True` 并包含标记。
- 普通 MP4/H264 不显示标记。

### ConfigManager

- 不存在配置文件时返回默认全局与编码器配置。
- 保存后重新加载能保留 Settings 与 Encoder section。
- 已有配置只覆盖对应键，缺失键补默认值。
- 局部更新只改变指定键。
- reset 返回深拷贝，修改返回值不会污染全局常量。

## 验收标准

- 三个独立模块均有测试文件或对应测试模块覆盖。
- 现有全部测试继续通过。
- `uv run ruff check .`、`uv run ruff format --check .`、`uv run python check_lang.py` 通过。
- `main_window.py` 不再直接导入或使用 `configparser`。
- `AnalysisWorker.run()` 不再包含大段 HTML 拼接。
- `_handle_output()` 只保留校验、策略调用和信号编排，不再包含具体备份/移动算法。
