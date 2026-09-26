# AGENTS.md

> AI 编码代理在本仓库工作时的上下文与约定，人类贡献者亦可参考（正式指南见 [CONTRIBUTING.md](CONTRIBUTING.md)）。
> 细节（文件地图、编码器参数、打包、流程）见按需 skill `.agents/skills/mgw-dev-workflow/`。

---

## 1. 项目简介

**魔法少女工坊 (Magical Girl Workshop)**：Windows 桌面应用，用 VMAF 智能驱动 AV1 硬件转码，目标是在肉眼无损画质下把影视库体积缩小 30%-50%。仅 Windows 10/11。

- **技术栈**：Python 3.12（严格锁定）、PySide6、QFluentWidgets、FFmpeg、ab-av1
- **打包/依赖**：Nuitka standalone -> 7z 便携版 + Inno Setup 安装版；uv（`uv.lock` 锁定）；GPL-3.0
- **当前版本**：v1.4.0（`config.py` 的 `VERSION`，与 `pyproject.toml` 的 `version` 同步）

---

## 2. 命令入口

所有命令在项目根目录执行；测试入口唯一为 `uv run python -m unittest`。

| 目的 | 命令 |
| --- | --- |
| 装依赖 | `uv sync`（CI/打包用 `uv sync --no-dev`） |
| 运行 | `uv run python main.py`（需 `tools/` 下 ffmpeg.exe / ffprobe.exe / ab-av1.exe） |
| Lint | `uv run ruff check . --fix` + `uv run ruff format .`（提交前必须） |
| 测试 | `uv run python -m unittest discover -s tests -v`（无第三方测试框架） |
| i18n | `uv run python check_lang.py --check`（改 locale 后必跑，非 0 即失败） |
| 打包 | Nuitka standalone -> 7z + Inno Setup；命令见 skill `references/packaging.md` |

Ruff 用默认配置（`pyproject.toml` 无 `[tool.ruff]` 段）。

---

## 3. 架构路由（改哪读哪）

文件地图、数据流、并发/缓存隔离、进度映射见 skill `references/architecture.md`。

| 改动路径 | 先读 | 验证 |
| --- | --- | --- |
| `workers/encoder.py` | 自身、`command_builder.py`、`tests/test_encoder.py` | `uv run python -m unittest tests.test_encoder tests.test_command_builder` |
| `workers/command_builder.py` | 自身、`config.py`、`tests/test_command_builder.py` | 同上，两模块名互换 |
| `workers/**`、`ui/**` | `workers/__init__.py`、`config.py`、`utils.py` | `uv run python -m unittest discover -s tests -p 'test_*.py'` |
| `i18n/locales/**`、`check_lang.py` | `i18n/locales/zh_CN.py`、`i18n/translator.py` | `uv run python check_lang.py --check` |
| `.github/workflows/**`、`installer/**` | `autobuild.yml`、`tests/test_packaging_config.py` | `uv run python -m unittest tests.test_packaging_config` |

链路记住三条：Worker -> Coordinator -> MainWindow 全经 `Signal`；缓存隔离 `mgw-session-<uuid>/task-<id>`；
批次进度按时长加权（探测 0-15%、编码 15-100%）。

---

## 4. 编码约定（硬规则）

- **Python 3.12 严格锁定**（`requires-python = ">=3.12,<3.13"`，Nuitka 兼容性）：不得引入
  3.13+ 语法或放宽约束。Ruff 是唯一 lint/format 工具，无 mypy/pyright。
- **i18n**：面向用户的字符串必须走 `tr()`，绝不硬编码中文/英文；键名点分层级
  （`home.settings_card.vmaf.label`）；改键必须同步 `i18n/locales/` 的 `zh_CN.py`、`zh_TW.py`、
  `en_US.py`、`ja_JP.py` 四个文件，占位符用 `str.format` 且名跨语言一致；改完跑 `check_lang.py`。
  新增语言加文件即可（`pkgutil` 动态发现）。
- **UI**：组件优先继承 `qfluentwidgets`；主题色固定 `#FB7299`；新增界面实现 `retranslate_ui()`
  并在 `MainWindow.retranslate_ui()` 调用；语言/主题切换同步 4 个子界面 combo。
- **后台线程**：worker 继承 `BaseWorker`、用 `self.is_running` 做停止标志；跨线程只用
  `Signal.emit`，绝不直接操作 UI 控件；Windows 子进程必须传 `creationflags=get_subprocess_flags()`
  （`CREATE_NO_WINDOW`）；路径用 `to_long_path()`；重写 `stop()` 先清理子进程
  （`taskkill /F /T /PID`）再调 `super().stop()`。
- **配置持久化**：存 `config.ini`（exe 同级，`configparser`）；`DEFAULT_SETTINGS` 是字符串值字典
  （数字也存 str，读取时转换）；新增项要注册默认值并在 `load_settings_to_ui` / `save_settings` 中处理。

---

## 5. 改前须知的陷阱

- **技术债文件**：`ui/main_window.py`（约 1,258 行）与 `workers/encoder.py`（约 1,105 行）混合大量
  职责；改前先定位相关方法，避免误改无关逻辑，无测试覆盖时不要大规模重构。
- **输出冲突**：不要绕过 `transcode_paths.find_output_conflicts()` 直接写输出（并发覆盖）；临时输出
  统一 `output.temp.mkv`，最终 `shutil.move` 原子替换。
- **降级顺序**：`ffmpeg_retry.py` 的降级互不重复（每类只触发一次）：硬件解码设备失败 -> 切 CPU
  软件解码（编码仍用硬件）；字幕流错误 -> 丢弃字幕；两者可按任意顺序组合。"硬件资源错误"（OOM/
  设备忙）走 `resource_error_signal` 触发并发降级，与设备初始化失败的重试降级不同。
- **编码器差异**：QSV/NVENC/AMF 的质量参数、预设范围、位深、ab-av1 支持度均不同，集中在
  `config.py` 的 `ENCODER_CONFIGS` 与 `workers/command_builder.py`；改前必读 skill
  `references/encoder-params.md` 并对照 `README.md` 参数对比表。
- **Nuitka 打包**：`i18n` 必须 `--include-package=i18n`，否则 `pkgutil` 动态加载编译后失效；资源用
  `resource_path()`；`tools/*.exe` 由 CI 复制，不要当源码修改。

---

## 6. 测试约定

- 标准库 `unittest` 风格，类继承 `unittest.TestCase`；仓库未安装第三方测试框架，勿引入 fixture 风格或依赖。
- **不依赖真实 Qt 事件循环 / GPU / ffmpeg**：用 `FakeSignal`（记录 emit）与 `FakeWorker`（可控生命
  周期）隔离；`EncodingCoordinator` 可注入 `timer_factory`、`metrics_sampler`、`clock`、`awake_setter`。
- 覆盖现状：UI、`test_encoder.py`（37 项）、`test_integration.py` 均已就位（后者需真实 ffmpeg，
  缺失时 SkipTest）；剩余缺口见 `docs/ROADMAP.md`（按需）。
- 新增 worker 逻辑优先补单元测试，至少覆盖正常路径 + 一个错误路径。

---

## 7. 提交与 PR 规范

- 分支从 `main` 切出（`feat/`、`fix/`、`docs/`、`refactor/` 前缀）；提交前必须 ruff check/format +
  全部测试通过 + `check_lang.py` 无报错。
- 版本号在 `config.py` 的 `VERSION` 和 `pyproject.toml` 的 `version` 两处维护，发版同步更新并写
  `docs/releases/ReleasesX.X.X.md` + `CHANGELOG.md`。
- PR 描述中**注明是否 AI 辅助生成**及所用模型/prompt（AI-Augmented Development 实验项目，硬性要求）。
- CI：`verify.yml` 跑 lint + 测试 + i18n 校验；`autobuild.yml` 在 push 到 main（非文档）或手动触发时
  全量编译，push 前确认不会触发非预期的全量构建。

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

## 9. 相关文档（按需查阅）

- [README.md](README.md) 主页（含"编码器参数对比"表）；[CONTRIBUTING.md](CONTRIBUTING.md) 人类贡献指南
- [docs/ROADMAP.md](docs/ROADMAP.md) 路线图（历史记录）；[docs/FAQ.md](docs/FAQ.md) 常见问题
- [docs/VMAF_GUIDE.md](docs/VMAF_GUIDE.md) VMAF 调优；[docs/HARDWARE_CHECK.md](docs/HARDWARE_CHECK.md) 硬件自测
- [CHANGELOG.md](CHANGELOG.md) 版本更新日志
