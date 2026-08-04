# AGENTS.md

> 本文件为 AI 编码代理（Codex / GPT / Claude 等）在本仓库工作时提供上下文与约定。
> 人类贡献者也可参考，正式的人类贡献指南见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 1. 项目简介

**魔法少女工坊 (Magical Girl Workshop)** 是一款 Windows 桌面应用，基于 VMAF 智能驱动 AV1 硬件转码，专为 NAS 用户与"仓鼠党"设计，目标是在肉眼无损画质下将影视库体积缩小 30%-50%。

- **技术栈**：Python 3.12（严格锁定）、PySide6、QFluentWidgets、FFmpeg、ab-av1
- **打包**：Nuitka standalone -> 7z 便携版 + Inno Setup 安装版
- **平台**：仅 Windows 10/11（大量使用 `ctypes.windll`，未做跨平台抽象）
- **依赖管理**：uv（`uv.lock` 锁定）
- **许可**：GPL-3.0
- **当前版本**：v1.4.0（见 `config.py` 中的 `VERSION`）

---

## 2. 常用命令

所有命令在项目根目录执行。本项目用 [uv](https://github.com/astral-sh/uv) 管理依赖与虚拟环境。

### 环境准备

```bash
uv sync                 # 安装运行时 + 开发依赖（含 nuitka/ruff/zstandard）
uv sync --no-dev        # 仅安装运行时依赖（CI/打包用）
```

### 运行

```bash
uv run python main.py
```

> ⚠️ 运行需要 `tools/` 目录下存在 `ffmpeg.exe`、`ffprobe.exe`、`ab-av1.exe`。仓库默认提供 essentials 版本。

### Lint 与格式化

```bash
uv run ruff check . --fix
uv run ruff format .
```

提交前**必须**通过这两条命令。Ruff 配置目前直接使用默认值（`pyproject.toml` 中无 `[tool.ruff]` 段）。

### 测试

```bash
uv run python -m unittest discover -s tests -v
# 或
uv run python -m pytest tests/
```

测试使用标准库 `unittest` 风格（非 pytest fixture 风格），但 pytest 可直接运行。测试**不依赖**真实 ffmpeg / GPU，核心逻辑通过 `FakeWorker` / `FakeSignal` 等桩对象隔离。

### 国际化校验

```bash
uv run python check_lang.py
```

校验所有 `i18n/locales/*.py` 的键是否齐全、占位符是否一致，并可自动补齐缺失键。**修改任何 locale 文件后必须运行此命令。**

### 打包（本地复现 CI）

打包流程较重，建议参考 `.github/workflows/autobuild.yml`。核心步骤：

```bash
# 读取版本
$version = uv run python -c "from config import VERSION; print(VERSION)"

# Nuitka standalone 编译
uv run --locked --with nuitka python -m nuitka main.py `
  --standalone --windows-console-mode=disable `
  --enable-plugin=pyside6 --assume-yes-for-downloads `
  --windows-icon-from-ico=logo.ico `
  --include-data-file=logo.ico=logo.ico `
  --include-data-file=LingMoe404.ico=LingMoe404.ico `
  --include-package=i18n `
  --output-dir=build/nuitka `
  --output-filename=MagicalGirlWorkshop.exe
```

---

## 3. 架构总览

```
main.py                 入口；设置 AppUserModelID、高 DPI、全局字体，实例化 MainWindow
config.py               全局常量：版本、编码器名、默认参数、DEFAULT_SETTINGS、ENCODER_CONFIGS
utils.py                工具函数：资源路径、subprocess flags、长路径、配置/缓存路径
check_lang.py           i18n 一致性校验脚本

ui/
  main_window.py        主窗口（FluentWindow）；超大文件，混合 UI + 业务逻辑
  interfaces.py         子界面：MediaInfo / Profile / Credits / Settings
  common.py             可复用 UI 组件：DragDropMixin、DroppableListWidget 等
  __init__.py

workers/                所有后台线程，均继承 BaseWorker(QThread)
  base.py               BaseWorker：is_running 标志 + stop()
  encoder.py            EncoderWorker：VMAF 探测 + FFmpeg 转码（核心，超大）
  coordinator.py        EncodingCoordinator：批次调度、并发槽管理、错误队列
  concurrency_policy.py DynamicConcurrencyPolicy：自适应并发算法
  analyzer.py           DurationWorker / ThumbnailWorker / AnalysisWorker
  dependency.py         DependencyWorker：启动时检查 ffmpeg + GPU 编码器可用性
  ffmpeg_retry.py       错误分类（硬件设备/字幕/资源）+ 三阶段降级重试
  transcode_paths.py    TaskPaths、输出路径构造、冲突检测、会话隔离
  transcode_schedule.py BatchSchedule + TaskState 状态机
  batch_progress.py     批次加权进度计算
  ab_av1_result.py      ab-av1 输出解析（CRF/VMAF 候选 + 质量回退）
  system_metrics.py     Windows CPU/内存采样（ctypes + GetSystemTimes）

i18n/
  translator.py         Translator：pkgutil 动态加载 locales，config.ini 持久化语言选择
  locales/              zh_CN / zh_TW / en_US / ja_JP，每个文件含 translation dict + language_name

tests/                  unittest 风格；用 FakeSignal/FakeWorker 隔离 Qt
tools/                  二进制：ffmpeg.exe / ffprobe.exe / ab-av1.exe（不入 git，但仓库已提供）
installer/              Inno Setup 脚本 (.iss)
.github/workflows/      autobuild.yml：Nuitka 编译 + 7z + Inno Setup，产出 Release 资产
docs/                   FAQ、VMAF 指南、硬件自测、Release notes、ROADMAP.md
```

### 关键数据流

1. 用户在 `MainWindow` 拖入/选择文件 -> `DurationWorker` 异步探测时长/元数据 -> `ThumbnailWorker` 生成缩略图
2. 点击开始 -> 构造 `config` dict -> `EncodingCoordinator.start()`
3. Coordinator 按 `BatchSchedule` + `DynamicConcurrencyPolicy.target_concurrency` 填充并发槽
4. 每个槽创建一个 `EncoderWorker`：先用 `ab-av1` 探测 VMAF 最优 CRF，再用 `ffmpeg` 转码
5. 失败时经 `ffmpeg_retry.py` 分类，按硬件解码降级 / 字幕丢弃顺序重试（最多 3 次）
6. 信号层层回传：Worker -> Coordinator -> MainWindow -> UI 更新

### 并发模型

- **不是 asyncio**，而是 Qt 的 `QThread` + `Signal/Slot` 跨线程通信
- `EncodingCoordinator` 在主线程运行，`EncoderWorker` 在各自线程运行
- 并发上限：手动 1-4，自动从 1 起根据吞吐量/CPU/内存动态调整，最高 3
- 并发降级**不会**中止已运行的任务，只影响后续填充

---

## 4. 编码约定

### 4.1 通用

- **Python 版本严格 3.12**：`requires-python = ">=3.12,<3.13"`，因 Nuitka 打包兼容性。不要引入 3.13+ 语法。
- **Ruff** 是唯一 lint/format 工具，无 mypy/pyright 配置。行宽等用 Ruff 默认。
- 注释用中文（与现有代码一致），关键算法处说明"为什么"而非"做什么"。
- 二进制大文件（`tools/*.exe`、`*.ico`）已通过 `.gitignore` 中的 `*.exe` 规则处理，但仓库已历史提交了 tools 下的 exe，**不要**再新增大二进制。

### 4.2 国际化（i18n）—— 高优先级约定

- **所有面向用户的字符串必须走 `tr()`**，绝不硬编码中文/英文。
- 键名采用点分层级：`home.settings_card.vmaf.label`、`log.encoder.success_overwrite`。
- 修改/新增键后，必须同步更新**全部四个** locale 文件：`zh_CN.py`、`zh_TW.py`、`en_US.py`、`ja_JP.py`。
- 占位符用 `str.format` 风格：`tr("log.encoder.success", encode_duration=x, total_duration=y)`，占位符名必须跨语言一致。
- 改完跑 `check_lang.py` 校验。
- 语言模块靠 `pkgutil.iter_modules` 动态发现，新增语言只需在 `i18n/locales/` 加文件并定义 `translation` + `language_name`，无需改注册表。

### 4.3 UI

- 组件优先继承 `qfluentwidgets`，保持 Win11 Fluent Design 风格。
- 主题色固定为 Bilibili 粉 `#FB7299`（`setThemeColor`）。
- 多语言/主题切换需同时同步 4 个子界面的 combo（见 `MainWindow.on_language_changed` / `on_theme_changed` 的同步逻辑）。
- 新增界面需实现 `retranslate_ui()` 方法并在 `MainWindow.retranslate_ui()` 中调用。

### 4.4 后台线程

- 所有 worker 继承 `BaseWorker`，用 `self.is_running` 做停止标志。
- 重写 `stop()` 时先清理子进程（`taskkill /F /T /PID`）再调用 `super().stop()`。
- 跨线程通信只用 `Signal.emit`，**绝不**直接操作 UI 控件。
- Windows 子进程必须传 `creationflags=get_subprocess_flags()`（`CREATE_NO_WINDOW`）避免弹黑窗。
- 路径用 `to_long_path()` 处理 Windows 260 字符限制。

### 4.5 配置持久化

- 配置存 `config.ini`（exe 同级），用 `configparser`。
- `DEFAULT_SETTINGS` 是字符串值的字典（即使数字也存 str），读取时按需转换。
- 新增配置项要在 `DEFAULT_SETTINGS` 注册默认值，并在 `load_settings_to_ui` / `save_settings` 中处理。

---

## 5. 重要陷阱与注意事项

### 5.1 `main_window.py` 与 `encoder.py` 是技术债

这两个文件分别约 3000 行 / 760 行，混合了大量职责。修改时**务必先定位相关方法**，避免误改无关逻辑。路线图（`docs/ROADMAP.md` Phase 1）计划拆分，拆分前请勿大规模重构。

### 5.2 Nuitka 打包约束

- `i18n` 包必须用 `--include-package=i18n` 显式包含，否则 `pkgutil` 动态加载在编译后失效。
- 资源文件用 `resource_path()` 解析，它兼容 PyInstaller `_MEIPASS` 和 Nuitka 两种打包方式。
- `tools/` 下的 exe 在打包时由 CI 单独复制到产物目录（见 `autobuild.yml` 步骤七），不进 Nuitka 编译。

### 5.3 硬件编码器差异

三种编码器（QSV/NVENC/AMF）参数差异巨大，集中在 `config.py` 的 `ENCODER_CONFIGS` 和 `encoder.py` 的命令构造逻辑：

- QSV：`av1_qsv`，`-global_quality:v`，preset 1-7（1 慢 7 快），`p010le` 10-bit
- NVENC：`av1_nvenc`，`-cq`，preset p7-p1（p7 慢 p1 快），`-b:v 0` 解除码率限制
- AMF：`av1_amf`，`-qvbr_quality_level`，preset 映射 quality/balanced/speed，**仅 8-bit**（`yuv420p`），且 ab-av1 原生不支持 AMF，AMD 模式强制用 CPU（SVT-AV1 -> AOM-AV1）探测

修改编码参数前务必对照 `README.md` 的"编码器参数对比"表。

### 5.4 并发与缓存隔离

- 每个批次创建独立 `mgw-session-<uuid>` 目录，每个文件在其下创建 `task-<id>` 子目录，避免并发任务互删缓存。
- `transcode_paths.find_output_conflicts()` 会在开工前检测多输入写同一输出的风险，**不要**绕过此检查。
- 临时输出文件统一命名 `output.temp.mkv`，最终通过 `shutil.move` 原子替换。

### 5.5 错误降级顺序

`ffmpeg_retry.py` 的三阶段重试是**互不重复**的组合：

1. 硬件解码设备失败 -> 切 CPU 软件解码（编码仍用 NVENC 等）
2. 字幕流错误 -> 丢弃字幕
3. 二者可按任意顺序组合，但每类降级只触发一次

不要把"硬件资源错误"（OOM / 设备忙）和"硬件设备初始化失败"混淆：前者走 `resource_error_signal` 触发并发降级，后者走重试降级。

### 5.6 进度计算

批次进度按**视频时长加权**（`batch_progress.calculate_batch_progress`），探测阶段占 0-15%，编码阶段占 15-100%。修改进度映射时注意 `map_probe_progress` / `map_encode_progress` 的区间。

---

## 6. 测试约定

- 测试位于 `tests/`，`unittest` 风格，类继承 `unittest.TestCase`。
- **不依赖真实 Qt 事件循环 / GPU / ffmpeg**：用 `FakeSignal`（记录 emit）和 `FakeWorker`（可控生命周期）隔离。
- `EncodingCoordinator` 可用 `timer_factory`、`metrics_sampler`、`clock`、`awake_setter` 注入假实现，便于测试时间相关逻辑。
- 新增 worker 逻辑时，优先为其编写单元测试，至少覆盖正常路径 + 一个错误路径。
- 当前**无 UI 测试、无 encoder.py 测试、无集成测试**——这是已知缺口（见 ROADMAP Phase 1.3）。

---

## 7. 提交与 PR 规范

- 分支从 `main` 切出：`feat/xxx`、`fix/xxx`、`docs/xxx`、`refactor/xxx`。
- 提交前：`ruff check . --fix` + `ruff format .` + 全部测试通过 + `check_lang.py` 无报错。
- PR 描述中**注明是否 AI 辅助生成**及所用模型/prompt（项目是 AI-Augmented Development 实验项目，此为硬性要求）。
- 版本号在 `config.py` 的 `VERSION` 和 `pyproject.toml` 的 `version` 两处维护，发版时同步更新并写 `docs/releases/ReleasesX.X.X.md` + `CHANGELOG.md`。
- CI（`autobuild.yml`）在 push 到 main（非文档）或手动触发时自动编译并产出 Release 资产，注意 push 前确认不会触发非预期的全量构建。

---

## 8. 不要做的事

- ❌ 不要硬编码面向用户的中文/英文字符串，必须走 `tr()`。
- ❌ 不要在 worker 线程直接操作 UI 控件，只用 `Signal`。
- ❌ 不要用 `asyncio` 替换现有 QThread 模型（会破坏 Qt 集成）。
- ❌ 不要引入 3.13+ 语法或放宽 `requires-python`（Nuitka 兼容性）。
- ❌ 不要把 `tools/*.exe` 当作源码修改对象，它们是外部二进制依赖。
- ❌ 不要在 `except Exception: pass` 中静默吞错误，至少记录日志。
- ❌ 不要绕过 `find_output_conflicts` 直接写输出，会引发并发覆盖。
- ❌ 不要在没有测试覆盖的情况下大规模重构 `encoder.py` / `main_window.py`。

---

## 9. 相关文档

- [README.md](README.md) — 项目主页（中文）
- [CONTRIBUTING.md](CONTRIBUTING.md) — 人类贡献指南
- [docs/ROADMAP.md](docs/ROADMAP.md) — 技术优化路线图（Phase 1-4）
- [docs/FAQ.md](docs/FAQ.md) — 常见问题
- [docs/VMAF_GUIDE.md](docs/VMAF_GUIDE.md) — VMAF 调优指南
- [docs/HARDWARE_CHECK.md](docs/HARDWARE_CHECK.md) — 硬件兼容性自测
- [CHANGELOG.md](CHANGELOG.md) — 版本更新日志

---

> 🌟 本文件随项目演进持续更新。当你发现某条约定在实践中不够清晰或已被打破，请同步修订本文件。
