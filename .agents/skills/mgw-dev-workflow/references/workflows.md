# 可复用流程（i18n / 版本发布 / 编码参数 / UI / 配置）

本文件把 `AGENTS.md` 中较长但非每轮必需的操作细节集中起来。**硬性规则以 `AGENTS.md` 为准**；
这里给的是按步骤执行的做法。

## 1. i18n 文案改动

1. 在代码中新增/修改键：所有面向用户的字符串必须走 `tr()`，绝不硬编码中文/英文。
2. 键名点分层级：`home.settings_card.vmaf.label`、`log.encoder.success_overwrite`。
3. 同步更新**全部四个** locale 文件：
   `i18n/locales/zh_CN.py`、`zh_TW.py`、`en_US.py`、`ja_JP.py`。
4. 占位符用 `str.format` 风格且跨语言一致：
   `tr("log.encoder.success", encode_duration=x, total_duration=y)`。
5. 校验（只读模式，退出码非 0 表示有问题）：

   ```bash
   uv run python check_lang.py --check
   ```

   去掉 `--check` 会进入自动补齐模式（可写入缺失键），修 key 时可用；提交前必须让
   `--check` 退出 0。
6. 新增语言只需在 `i18n/locales/` 加文件并定义 `translation` + `language_name`，
   `pkgutil.iter_modules` 会动态发现，无需改注册表。

## 2. 版本发布

1. 同步更新两处版本号：
   - `config.py` 的 `VERSION`
   - `pyproject.toml` 的 `version`
2. 写 `docs/releases/ReleasesX.X.X.md`（对照现有 Releases1.4.0.md 的格式）。
3. 更新 `CHANGELOG.md`（当前为 v1.4.0 / 2026-06-12 条目风格）。
4. 提交前跑完整验证：`ruff check . --fix`、`ruff format .`、
   `uv run python -m unittest discover -s tests`、`uv run python check_lang.py --check`。
5. 注意 push 到 main 会触发 `autobuild.yml` 全量编译；文档类改动不触发（见该 workflow 的
   路径过滤）。

## 3. 编码参数改动

见 `references/encoder-params.md`：改了 `config.py` / `command_builder.py` 后必须同步
`README.md` 参数对比表，并用 argv 快照测试锁定：
`uv run python -m unittest tests.test_command_builder tests.test_encoder`。

## 4. UI 约定

- 组件优先继承 `qfluentwidgets`，保持 Win11 Fluent Design 风格。
- 主题色固定为 Bilibili 粉 `#FB7299`（`setThemeColor`）。
- 多语言/主题切换需同时同步 4 个子界面的 combo（见 `MainWindow.on_language_changed` /
  `on_theme_changed` 的同步逻辑）。
- 新增界面需实现 `retranslate_ui()` 方法并在 `MainWindow.retranslate_ui()` 中调用。
- `ui/main_window.py` 与 `workers/encoder.py` 是**技术债**文件（分别约 1,258 行 / 1,105 行），
  混合大量职责。修改时**务必先定位相关方法**，避免误改无关逻辑；拆分计划见
  `docs/ROADMAP.md`（历史记录，**按需**查阅，不作为开工前必读）。
  在没有测试覆盖的情况下不要大规模重构这两个文件。

## 5. 配置持久化

- 配置存 `config.ini`（exe 同级），用 `configparser`；读写集中在 `ui/config_manager.py`。
- `DEFAULT_SETTINGS`（`config.py`）是**字符串值**的字典（即使数字也存 str），读取时按需转换。
- 新增配置项要在 `DEFAULT_SETTINGS` 注册默认值，并在 `load_settings_to_ui` / `save_settings`
  中处理（同时保留 `[Settings]` 与 `[Encoder:<name>]` section、键名、字符串值格式）。

## 6. 后台线程与子进程

- 所有 worker 继承 `BaseWorker`，用 `self.is_running` 做停止标志。
- 重写 `stop()` 时先清理子进程（`taskkill /F /T /PID`）再调用 `super().stop()`。
- 跨线程通信只用 `Signal.emit`，**绝不**直接操作 UI 控件。
- Windows 子进程必须传 `creationflags=get_subprocess_flags()`（`CREATE_NO_WINDOW`）避免弹黑窗。
- 路径用 `to_long_path()` 处理 Windows 260 字符限制。
