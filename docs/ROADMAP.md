# 🗺️ 魔法少女工坊 · 技术优化路线图

> **文档版本**: 1.1  
> **更新日期**: 2026-08-20  
> **对应版本**: v1.4.0  
> **状态**: 📋 规划中 → 🔄 进行中 → ✅ 已完成

---

## 总览

本路线图将魔法少女工坊的后续发展分为 **四个阶段（Phase）**，每个阶段聚焦于不同的目标。从最紧迫的代码质量改进开始，逐步扩展到新功能、生态建设和长期架构升级。

| 阶段 | 主题 | 时间线建议 | 主要目标 |
|------|------|-----------|---------|
| **Phase 1** | 🧹 代码重构与质量提升 | 近期 | 可维护性、可测试性 |
| **Phase 2** | 🚀 核心功能增强 | 短期 | 用户覆盖、体验提升 |
| **Phase 3** | 🌐 生态与扩展 | 中期 | 自动化、远程控制 |
| **Phase 4** | 🏗️ 架构现代化 | 长期 | 可扩展性、跨平台 |

---

## Phase 1：🧹 代码重构与质量提升

> **目标**：降低维护成本，提升测试覆盖率，堵住已知隐患。

### 1.1 巨型文件拆分

| 任务 | 文件 | 当前大小 | 拆分方案 | 优先级 | 状态 |
|------|------|---------|---------|--------|------|
| `MainWindow` 分解 | `ui/main_window.py` | ~3000 行 / 110KB | 拆分为 `FileListManager`、`ConfigManager`、`LogManager`、`TranscodeController`、`HomeUiBuilder`、`SettingsController`、`WelcomeWizard` 等 Controller/Builder | 🔴 最高 | ✅ 已完成（当前 1258 行） |
| `EncoderWorker.run()` 拆分 | `workers/encoder.py` | ~760 行 / 40KB | 拆分为 `_probe_vmaf()`、`_execute_ffmpeg()`、`_handle_output()`、`_cleanup()`；输出策略已抽至 `workers/output_strategy.py` | 🔴 最高 | ✅ 已完成 |
| 配置逻辑抽取 | `ui/main_window.py` 中的配置部分 | ~500 行 | 抽取独立 `ConfigManager` 类，管理 config.ini 读写、迁移、缓存 | 🟡 高 | ✅ 已完成 |
| 文件列表抽取 | `ui/main_window.py` 中的文件列表部分 | ~500 行 | 抽取独立 `FileListManager`，管理扫描、去重、worker 队列和列表状态 | 🟡 高 | ✅ 已完成 |
| 日志系统抽取 | `ui/main_window.py` 中的日志部分 | ~200 行 | 抽取独立 `LogManager` 类，线程安全队列 + 定时刷新 | 🟡 高 | ✅ 已完成 |
| 转码控制抽取 | `ui/main_window.py` 中的转码生命周期部分 | ~250 行 | 抽取 `TranscodeController` 门面，复用 `EncodingCoordinator` 调度逻辑 | 🟡 高 | ✅ 已完成 |
| 主页布局抽取 | `ui/main_window.py` 中的 UI 构建部分 | ~500 行 | 抽取 `home_ui_builder.py`，集中构建主页控件并注入管理器 | 🟡 高 | ✅ 已完成 |
| 设置与欢迎流程抽取 | `ui/main_window.py` 中的设置/向导部分 | ~500 行 | 抽取 `SettingsController` 与 `WelcomeWizard`，保留主窗口薄转发 | 🟡 高 | ✅ 已完成 |
| 媒体报告渲染抽取 | `workers/analyzer.py` 中的 HTML 报告 | ~170 行 | 抽取独立 `media_report.py` 纯渲染模块 | 🟡 高 | ✅ 已完成 |

**验收标准**：
- [x] `main_window.py` 缩减至 1500 行以内（当前 1258 行）
- [x] `encoder.py` 的 `run()` 方法缩减至 200 行以内
- [x] 每个拆分模块通过所属包的 `__init__.py` 导出（`ui` / `workers`）

### 1.1.1 文件规模与职责治理（持续治理阶段）

> **定位**：这不是一次性"所有文件压到 300 行以内"的运动，而是长期执行的治理规则。
> 规模阈值是**预警指标**，不是绝对法律；任何拆分决定都必须先通过职责检查清单。

#### 治理目标

1. 每个文件围绕一个清晰的核心职责，能在一句话内说清"这个文件为什么存在"。
2. 高内聚、低耦合：经常因同一种需求一起变化的代码放在一起。
3. 避免两个极端：不制造 God Class，也不制造几十个几十行的小碎片文件。
4. 让"下一个改动"更容易定位、更容易写测试，而不是让 LOC 平均值好看。

#### 适用范围

- **适用**：`ui/`、`workers/`、根目录业务脚本（`main.py`、`utils.py`、`check_lang.py`）。
- **豁免**（合理例外，仅登记不强制拆分）：
  - `i18n/locales/*.py`——声明式翻译表；
  - `config.py`——静态常量与编码器配置表；
  - `tests/`——按行为/场景拆分而非按行数（见"测试代码"节）；
  - `tools/auto_screenshot.py`——独立开发工具，不随主程序打包；
  - 纯声明式 UI 布局代码（如 `home_ui_builder.py` 的 `_init_*` 系列）——优先抽取重复模式，而非机械切行。

#### 规模阈值（预警指标）

| 对象 | 理想 | 开始审查 | 优先拆分 | 原则上限 |
|------|------|---------|---------|---------|
| 普通 Python 文件 | 150–300 行 | 400 行 | 500 行 | 700 行 |
| Manager 类 | 150–300 行 | 400 行 | 500 行 | ~500 行 |
| Controller/UI Controller | 100–250 行 | 300 行 | 400 行 | ~400 行 |
| GUI View / 声明式布局 | 150–350 行 | 450 行 | 600 行 | ~600 行 |
| 函数 / 方法 | 10–50 行 | 80 行 | 120 行 | 120 行 |
| 类 | 50–300 行 | 300–400 行 | 400 行 | 600 行 |
| 类的 public method 数 | ≤ 15 | 16–20 | > 20 | — |

#### 是否应该拆分：检查清单

满足以下**全部**条件才拆：

1. 能说清文件的单一核心职责，且拆出的部分有**独立的变化原因**（不是因为"太长"）；
2. 拆出的部分与保留部分之间的耦合可以收敛为少量参数/回调/信号（不需要互访大量内部状态）；
3. 拆出部分可以**独立测试**（纯函数、独立类、或可注入假实现）；
4. 不跨 Qt 线程边界制造新的直接调用（worker 不碰 UI，只有 Signal）；
5. 拆分后不产生 < 80 行且无独立变化原因的碎片文件。

#### 拆分前检查

- [ ] 已定位该文件最近 3 次变更的 diff，确认拆分边界与实际变化簇吻合；
- [ ] 已为现有行为写回归测试（测试先行，先锁定行为再动结构）；
- [ ] 确认无循环导入风险（`ui` 不反向依赖 `ui.main_window`）；
- [ ] 确认不需要改动 `tr()` 键与 locale 文件（若需要，先跑 `check_lang.py` 建立绿色基线）。

#### 拆分后检查

- [ ] `uv run python -m unittest discover -s tests` 全绿，测试数不少于拆分前；
- [ ] `uv run ruff check . && uv run ruff format --check .` 通过；
- [ ] `uv run python check_lang.py` 无报错（若涉及 i18n）；
- [ ] 新模块通过所属包 `__init__.py` 导出，或明确不导出并说明理由；
- [ ] 文件职责注释（模块 docstring）更新，一句话说清职责；
- [ ] git 提交粒度：一个拆分 = 一个提交，可独立 revert。

#### 防止过度拆分的规则

1. **禁止按行数机械切割**。一个 400 行的纯函数集合如果职责单一、变化簇一致，不需要拆。
2. **禁止"提取即转发"泛滥**。若 MainWindow 式薄转发层已存在，不再为降 LOC 继续抽委托方法。
3. **碎片合并**：少于 80 行、无独立测试、无独立变化原因的模块，应合并回宿主文件。
4. **public method 数量比 LOC 更重要**：方法数是职责数量更好的代理指标（见下方"当前判断"）。
5. 例外登记制：确需超阈值的文件（如声明式布局），在代码审计文档中登记理由，不强制拆。

#### 代码合并检查

出现以下信号时优先**合并**而非继续拆：

- 两个模块总在同一个提交里一起变；
- A 模块需要 import B，B 又通过回调/属性注入引用 A 的宿主；
- 一个类的方法一半以上是对另一个对象的单行转发。

#### 验收标准

- [ ] 全项目无 700 行以上普通业务文件（声明式布局、测试、翻译表除外）；
- [ ] 单个类的 public method ≤ 20（MainWindow 的 70 个是历史遗留，逐步收敛）；
- [ ] 新增代码 review 时执行本清单，无需一次性清完存量；
- [ ] 每季度（或每个 minor 版本）跑一次规模扫描脚本，只在"开始审查"阈值以上且职责混合时报新问题。

#### 当前基线（2026-08-20，AST 扫描）

| 文件 | 行数 | 类/主要结构 | public method | 主要问题 |
|------|------|------------|--------------|---------|
| `ui/main_window.py` | 1258 | `MainWindow` 1200 行 | **70** | 转发泛滥（约 25 个单行委托）；仍有启动校验、缓存清理、卡片样式等业务孤岛 |
| `workers/encoder.py` | 1151 | `EncoderWorker` 1098 行 | 5 | `_execute_ffmpeg` 388 行、`_probe_vmaf` 247 行——命令构造/进程循环/进度解析混在一个方法 |
| `ui/interfaces.py` | 800 | 4 个界面类 | 3–10/类 | 4 份几乎相同的页头构建 + 主题/语言 combo 重复代码 |
| `ui/home_ui_builder.py` | 663 | 14 个模块级函数 | — | 声明式布局；`_init_settings_card` 156 行 / `_init_action_card` 114 行 |
| `ui/file_list_manager.py` | 574 | `FileListManager` 542 行 | **24** | `update_selected_count` 131 行实为"整行控件构建"；时长/缩略图两套 worker 队列近乎重复 |
| `workers/coordinator.py` | 479 | `EncodingCoordinator` 446 行 | 10 | 内聚良好（调度引擎），无 God Class 风险 |
| `ui/settings_controller.py` | 467 | `SettingsController` 430 行 | 13 | 3 个变化原因（存取/重置迁移/主题同步）；`restore_defaults` 119 行 |
| `workers/dependency.py` | 281 | `DependencyWorker.run` 248 行 | 1 | 长方法：6 个步骤 + 3 段近乎相同的 GPU 探测骨架 |

### 1.1.2 后续拆分任务（按优先级）

> 原则：先修"阻塞干净检出/CI/运行"的问题，再处理职责混合且有自然边界的文件，然后是可测试性与线程边界，最后才是纯粹的体积问题。以下任务均要求**测试先行**，并遵守 1.1.1 的检查清单。

#### P0：无（工作区已干净，无阻塞性问题）

经核实 `git status` 为空、`docs/superpowers/` 计划/设计文档与全部测试均已被 git 跟踪、302 项 unittest 全绿、ruff 与 `check_lang.py` 通过。当前不存在阻塞干净检出、打包或运行的模块/依赖问题。**P0 置空**。

#### P1：职责明显混合、风险高、影响主流程

**P1-1 `workers/encoder.py` 命令构造与进度解析抽取**（预计 2–3 个小提交）

- 文件路径：`workers/encoder.py`（1151 行）
- 当前职责：VMAF 探测 + ffmpeg 命令构造 + 子进程管理 + 进度解析 + 输出落盘 + 信号发射，全部内联在一个类中。
- 发现的问题：
  - `_execute_ffmpeg`（388 行）内部混合了 5 类子职责：音频参数构造（523–553）、色彩/HDR 参数（583–635）、按编码器的视频参数（QSV/NVENC/AMF，637–668）、字幕 map 参数（673–679）、进程读循环与进度正则解析（704–782）；
  - `_probe_vmaf` 与 `_execute_ffmpeg` 的子进程读循环骨架（kill/pause/readline/poll）几乎逐行重复（约 40 行 × 2）；
  - 所有构造逻辑与信号发射交织，无法脱离 Qt 对象单测。
- 建议的职责边界：**纯函数模块**（不导入 Qt、不发信号、可独立单测），模仿已有 `output_strategy.py` / `ffmpeg_retry.py` 的模式：
  - `workers/command_builder.py`：`build_audio_args()`、`build_color_args()`、`build_video_encoder_args()`、`build_subtitle_map_args()`、`build_ab_av1_search_cmd()`、`resolve_encoder()`（约 180 行）；
  - `workers/progress_parser.py`：`parse_ffmpeg_progress_line()`（Duration/time=/speed= 正则，约 60 行）；
  - `_execute_ffmpeg`/`_probe_vmaf` 保留信号发射与 `is_running`/`is_paused`/`current_proc` 状态，缩为编排层（目标各 ≤ 150 行）。
- 不建议拆分的部分：信号发射、`stop()`/`set_paused()`/`receive_decision()`、`run()` 的任务循环、`_handle_output`（已薄）、重试决策（已在 `ffmpeg_retry.py`）。
- 依赖变化：`workers/encoder.py` 新增两个同包导入；`workers/__init__.py` 可选导出。无 Qt 依赖新增。
- 测试策略：先为现有命令行构造写快照测试（构造期不改动行为，仅断言参数序列），抽取时测试随代码迁移。`tests/test_encoder.py`（617 行）已有 20 项编码器测试可作回归网。
- 风险：命令参数顺序变化导致 ffmpeg 行为漂移；缓解：逐参数断言 + 迁移既有测试。
- 回滚方式：单提交 revert（每个抽取 = 一个独立提交）。
- 验收命令：`uv run ruff check . && uv run python -m unittest discover -s tests && uv run python check_lang.py`

**P1-2 `ui/interfaces.py` 页头重复代码抽取**（1 个提交）

- 文件路径：`ui/interfaces.py`（800 行）
- 当前职责：4 个子界面（媒体信息/作者/设置/鸣谢）各自构建几乎相同的页头（标题 + 语言 combo + 主题 combo）与主题条目重译。
- 发现的问题：4 份约 11 行的页头构建 + 4×3 行 combo 重译完全重复；`SettingsController.on_theme_changed` 还按属性名字符串反向触达 4 个界面的私有 combo——改一个页头要动 5 处。
- 建议的职责边界：`ui/page_header.py`：`build_page_header(parent) -> (title_label, combo_lang, combo_theme)` + `retranslate_theme_combo()`，或 `PageHeaderMixin`。
- 不建议拆分的部分：4 个界面类本身（各自内聚）；`MediaInfoInterface` 的 worker 生命周期（独立 feature widget）。
- 依赖变化：`ui/interfaces.py` 导入新模块；无 workers 依赖。
- 测试策略：`tests/test_ui_components.py` 已有 DroppableListWidget 等测试，参照新增页头构造/重译测试（2–3 项）。
- 风险：combo 信号连接时序变化导致主题/语言同步失效；缓解：保留原信号连接顺序。
- 回滚方式：单提交 revert。
- 验收命令：同 P1-1。

**P1-3 `ui/file_list_manager.py` 行构建与队列模板抽取**（1–2 个提交）

- 文件路径：`ui/file_list_manager.py`（574 行）
- 当前职责：目录扫描/去重/列表状态 + 时长与缩略图两套 worker 队列 + 整行列表控件构建 + 进度/状态更新。
- 发现的问题：`update_selected_count`（131 行）名义是"更新计数"，实际构建完整的 QListWidgetItem 行控件（含内联样式），每次增删都全量执行；时长/缩略图两套队列方法（6+5 个）近乎重复；public method 达 24 个。
- 建议的职责边界：
  - 拆出 `_build_item_widget(path) -> tuple[item, widget]`（行构建，约 110 行），`update_selected_count` 缩为计数 + 可见性切换（约 10 行）；
  - 引入通用 `_TaskQueue` 处理 process/start/finished/get 四件套，两套队列收敛为配置差异。
- 不建议拆分的部分：`add_source_paths` 的扫描/去重、`update_file_progress/stats/status` 的状态机、拖拽边框状态。
- 依赖变化：无新增外部依赖；可选把行构建移入 `ui/list_item_factory.py`。
- 测试策略：`tests/test_file_list_manager.py`（19 项）回归；新增行构建快照测试（控件层级 + 样式键存在性）。
- 风险：行控件对象名（objectName）被 `update_file_stats` 等方法 findChild 依赖，重命名会断链；缓解：对象名保持不变 + 专项测试断言 findChild 可达。
- 回滚方式：单提交 revert。
- 验收命令：同 P1-1。

#### P2：可测试性、边界和异常处理改进

**P2-1 `workers/dependency.py` 探测步骤分解**

- 文件路径：`workers/dependency.py`（281 行）
- 发现的问题：`run()` 248 行，内含 6 个顺序步骤：配置读取、可执行文件存在性、ffmpeg 编码器清单、QSV 探测、NVENC 探测（含旧卡回退，约 84 行）、AMF 探测。三段 GPU 探测共享几乎相同的 Popen → `_communicate_with_timeout` → returncode 判断骨架。
- 建议边界：拆 `_load_gpu_timeout()`、`_check_missing_deps() -> list`、`_read_encoder_list() -> str`、`_probe_encoder(cmd, gpu_timeout) -> (ok, err_msg)`（QSV/NVENC/AMF 复用）+ `_probe_nvenc_compat()`。`run()` 缩为约 40 行编排。
- 测试策略：`tests/test_dependency.py` 当前仅 1 项测试（35 行）——先补步骤级单测再重构。
- 风险：NVENC 旧卡回退分支是真实硬件差异逻辑，必须保持探测顺序与错误消息不变。
- 验收命令：同 P1-1。

**P2-2 `ui/settings_controller.py` 职责收敛**

- 文件路径：`ui/settings_controller.py`（467 行）
- 发现的问题：3 个变化原因（配置存取 / 重置与迁移 / 主题同步）；`restore_defaults` 119 行；"InfoBar 提示 + 按钮文字闪烁"模式重复 3 次；`on_theme_changed` 反向触达 4 个界面。
- 建议边界：抽 `_flash_saved()` 私有辅助；把 `restore_defaults` 分解为 `_reset_widgets()` / `_sync_settings_interface_after_reset()` 命名步骤；主题同步与 P1-2 的页头抽取联动（combo 归页头管后，反向触达自然消失）。**不建议**单独抽 ThemeController 类（避免过度拆分，等 P1-2 完成后重估）。
- 测试策略：`tests/test_settings_controller.py`（9 项）回归 + 新增 restore_defaults 分解后行为不变测试。
- 验收命令：同 P1-1。

**P2-3 宽泛异常捕获清单化（ROADMAP 1.4 的执行细化）**

- 现状扫描：生产代码中 26 处 `except Exception`（绝大多数已加 `# noqa: BLE001` 且有日志），真正静默吞错（`S110`）已清零。
- 建议边界：不求一次性替换，按文件清单化：`workers/encoder.py` 11 处 → 改为 `OSError`/`subprocess.SubprocessError`/`json.JSONDecodeError` 等具体类型；`ui/main_window.py` 2 处、`workers/analyzer.py` 5 处依次跟进。每替换一处配一条失败路径测试。
- 验收命令：`grep -rn "except Exception" --include="*.py" ui/ workers/ | wc -l` 逐版本下降。

#### P3：低风险结构优化（可延后）

**P3-1 `ui/main_window.py` 继续瘦身（缓步进行）**

- 1258 行 / 70 个 public method 中约 25 个是单行转发。继续拆分收益递减，**只做三件事**：
  1. `start_task` 内的 16 键 config dict 构造（994–1018 行）移入 `SettingsController.build_job_config()`；
  2. 缓存清理（`clear_cache_files` + `auto_clean_cache_startup`，约 63 行）收敛为一个 `CacheCleaner`（可并入 ConfigManager 或独立小模块），消除 substring 匹配隐患；
  3. `_update_card_style`（55 行 QSS 模板）移入设置/主题侧。
- 不做：为降 LOC 继续抽委托方法。`retranslate_ui`、信号接线、几何同步、`closeEvent` 关停序列留在窗口壳层。

**P3-2 `ui/home_ui_builder.py` 长函数细分**

- 声明式布局豁免区。仅当需要修改时顺势拆 `_init_settings_card`（156 行）为 `_init_encoder_card` / `_init_preset_card` 等。不主动开工。

**P3-3 `workers/coordinator.py` 平台代码外移**

- 内聚良好，唯一理由把 `ctypes` 唤醒调用与指标采样移到 `system_metrics.py` 侧。改动收益小，随下次触碰该文件时顺带处理。

**P3-4 测试提速**

- 全量 302 项测试需 379 秒，主要耗时在 `tests/test_encoder.py`、`tests/test_output_strategy.py`、`tests/test_log_manager.py` 的 `time.sleep` 重试路径。将这些 sleep 参数化（模块级常量 → 可注入），目标全量 < 180 秒。

#### 暂不处理（明确延期项）

| 文件 | 行数 | 理由 |
|------|------|------|
| `ui/interfaces.py` 的 `ProfileInterface.init_ui`（178 行） | 800 行文件 | 纯声明式布局 + 内联样式，零逻辑零线程，拆分无收益 |
| `ui/home_ui_builder.py` 整体 | 663 | 单一职责（构建主页布局），变化原因单一 |
| `workers/coordinator.py` | 479 | 调度引擎内聚，18 个私有方法是良好分解的信号 |
| `tools/auto_screenshot.py` | 367 | 独立开发工具，不入主程序包 |
| `i18n/locales/*.py` | 298×4 | 翻译表，声明式例外 |
| 测试文件（>300 行的 8 个） | ≤ 617 | 测试代码豁免；按行为拆分，不按行数 |

#### 1.1.2 依赖顺序

```
P1-1 encoder 纯函数抽取 ──(无依赖)──> 可与 P1-2 并行
P1-2 页头抽取 ──> P2-2 settings_controller 主题联动收敛
P1-3 行构建抽取 ──(无依赖，可独立)
P2-1 dependency 分解 ──(无依赖)
P2-3 异常清单化 ──> 跟随各 P1 任务顺带执行
P3-* ──> 空闲期或顺手处理
```

### 1.1.3 分阶段实施计划（可独立验证的小步）

> 每一步一个提交，提交前必须三绿：`ruff` + `unittest`（测试数不减）+ `check_lang.py`。

#### 步骤 S1：encoder 命令构造抽取（对应 P1-1，第 1/3 提交）

1. **目标**：`workers/command_builder.py` 落地，`_execute_ffmpeg` 的参数构造段（原 577–685 行）改为调用纯函数，行为零变化。
2. **先阅读**：`workers/encoder.py`（459–846 行）、`workers/output_strategy.py`（纯函数模式参照）、`config.py` 的 `ENCODER_CONFIGS`、`tests/test_encoder.py`。
3. **修改**：`workers/encoder.py`、新增 `workers/command_builder.py`、`tests/test_command_builder.py`（新增）、`workers/__init__.py`（可选导出）。
4. **不修改**：`workers/ffmpeg_retry.py`、`workers/output_strategy.py`、`ui/**`、`i18n/**`、`config.py`。
5. **实现步骤**：
   a. 先写测试：为 QSV/NVENC/AMF 三种编码器各写一条命令构造断言（锁定当前参数序列），另加音频/色彩/字幕参数各一条；此时测试直接对 `_execute_ffmpeg` 内联逻辑的行为做快照（可通过现有 FakeProc 测试桩捕获 argv）；
   b. 将参数构造逐段平移为纯函数（保持参数顺序逐字不变）；
   c. `_execute_ffmpeg` 改为调用，删除内联段；
   d. 跑三绿。
6. **测试先行**：是（步骤 a 先行，测试失败/通过基线明确后才动生产代码）。
7. **预期新增测试**：6–10 项（三编码器 + 音频/色彩/字幕/ab-av1 探测命令）。
8. **验证**：`uv run ruff check . && uv run ruff format . && uv run python -m unittest discover -s tests && uv run python check_lang.py`。
9. **locale 更新**：不需要（无用户可见字符串变化）。
10. **Qt 线程边界**：不涉及。纯函数模块禁止导入 PySide6。
11. **风险与回滚**：参数顺序漂移--靠逐参数断言防护；单提交 revert。
12. **完成判定**：`_execute_ffmpeg` ≤ 250 行；新模块无 Qt import；三绿。

#### 步骤 S2：进度解析抽取（对应 P1-1，第 2/3 提交）

1. **目标**：`workers/progress_parser.py` 承接 Duration/`time=`/`speed=` 正则解析（原 727–776 行），`_execute_ffmpeg` 只保留信号发射。
2. **先阅读**：`workers/encoder.py` 读循环段、`workers/batch_progress.py`（`map_encode_progress` 区间约定）。
3. **修改**：`workers/encoder.py`、新增 `workers/progress_parser.py`、新增 `tests/test_progress_parser.py`。
4. **不修改**：`workers/batch_progress.py` 的映射区间（AGENTS.md 5.6 红线）。
5. **实现步骤**：先写解析函数的表驱动测试（含异常行、超时长行、无 duration 回退），再平移正则；信号发射点保持在 EncoderWorker。
6. **预期新增测试**：8–12 项。
7. **验证/locale/线程边界**：同 S1；解析函数为纯函数。
8. **风险与回滚**：进度区间映射错位--表驱动测试锁定 15%/100% 边界；单提交 revert。
9. **完成判定**：`_execute_ffmpeg` ≤ 180 行；进度断言测试通过。

#### 步骤 S3：探测命令与编码器映射抽取（对应 P1-1，第 3/3 提交）

1. **目标**：`build_ab_av1_search_cmd()` 与 `resolve_encoder()` 入 `command_builder.py`，`_probe_vmaf` 缩至 ≤ 150 行，`run()` 的编码器映射段（原 1019–1041 行）改调用。
2. **先阅读**：`workers/ab_av1_result.py`、`workers/encoder.py` 211–457 行。
3. **修改/不修改**：同 S1 模式。
4. **测试**：为 ab-av1 命令（硬件/CPU 策略差异、`max_crf` 63/51 分支）与三编码器 preset 映射写断言，6–10 项。
5. **风险**：AMF 无 ab-av1 探测的特殊分支（AGENTS.md 5.3）必须保持。
6. **完成判定**：`workers/encoder.py` ≤ 750 行且类内无参数拼装内联块；三绿。

#### 步骤 S4：interfaces 页头抽取（对应 P1-2）

1. **目标**：消除 4 份重复页头，`ui/interfaces.py` 减重约 60 行，主题/语言 combo 归属统一。
2. **先阅读**：`ui/interfaces.py` 全文、`ui/settings_controller.py` 的 `on_theme_changed`（411–424 行）、`tests/test_ui_components.py`、`tests/test_credits_interface.py`。
3. **修改**：`ui/interfaces.py`、新增 `ui/page_header.py`（或并入 `ui/common.py`）、`ui/__init__.py`、相关测试。
4. **不修改**：`ui/main_window.py` 的 combo 接线循环（等 S7 联动）、`i18n/**`。
5. **实现步骤**：先写页头构造 + 重译测试；抽 `build_page_header()`；4 个界面替换调用；确认 `objectName`/信号名不变。
6. **预期新增测试**：2–4 项。
7. **locale**：不需要。
8. **Qt 线程边界**：UI 主线程内，无 worker 参与。
9. **风险**：主题切换同步回归--用现有 `on_theme_changed` 手动路径 + 新增页头测试防护；单提交 revert。
10. **完成判定**：`grep -c "combo_theme" ui/interfaces.py` 从 ~8 降到 ≤ 2；三绿。

#### 步骤 S5：file_list_manager 行构建抽取（对应 P1-3）

1. **目标**：`update_selected_count` 只做计数；行构建独立成 `_build_item_widget`。
2. **先阅读**：`ui/file_list_manager.py` 299–429 行、`tests/test_file_list_manager.py`（19 项）。
3. **修改**：`ui/file_list_manager.py`、`tests/test_file_list_manager.py`。
4. **不修改**：行内控件的 `objectName`（`update_file_stats` 等靠 findChild 定位）、`ui/common.py`。
5. **实现步骤**：先写"新增文件后行控件存在且 findChild 可达"测试；再拆方法；保持 `update_selected_count` 的调用点签名不变（MainWindow 转发层无需改动）。
6. **预期新增测试**：3–5 项。
7. **locale/线程边界**：不需要 / UI 主线程。
8. **风险**：行构建时序（`get_file_duration` 触发点）变化导致探测不触发；专项测试断言新增行后 duration 队列被填充。
9. **完成判定**：`update_selected_count` ≤ 20 行；三绿。

#### 步骤 S6：dependency 探测分解（对应 P2-1）

1. **目标**：`run()` 缩至约 40 行编排；三段 GPU 探测共用 `_probe_encoder()`。
2. **先阅读**：`workers/dependency.py` 全文、`tests/test_dependency.py`。
3. **修改**：`workers/dependency.py`、`tests/test_dependency.py`（先从 1 项扩到 6–8 项：缺失 exe、超时 kill、三编码器探测成败、NVENC 旧卡回退）。
4. **不修改**：`utils.py` 的 `tool_path()`、探测命令的参数与顺序、错误日志文案（涉及 locale 的部分保持键不变）。
5. **风险**：超时 kill 逻辑（审计 P2 修复）被破坏--测试必须覆盖 TimeoutExpired 分支。
6. **完成判定**：`run()` ≤ 60 行；新增测试全过；三绿。

#### 步骤 S7：settings_controller 收敛 + MainWindow 三件套（对应 P2-2 / P3-1）

1. **目标**：`restore_defaults` 分解、`_flash_saved` 去重、`start_task` 的 config 构造移入 `SettingsController.build_job_config()`、缓存清理收敛、`_update_card_style` 迁移。
2. **先阅读**：`ui/settings_controller.py`、`ui/main_window.py`（510–654、869–932、958–1037 行）、`tests/test_settings_controller.py`、`tests/test_main_window_transcode_integration.py`。
3. **修改**：`ui/settings_controller.py`、`ui/main_window.py`、对应测试。
4. **不修改**：`config.py` 的 `DEFAULT_SETTINGS` 键名、`ui/config_manager.py` 的迁移逻辑、`workers/**`。
5. **实现步骤**：每半件一个小提交（7a config 构造迁移 / 7b 缓存清理 / 7c 主题样式迁移），每步先补行为锁定测试。
6. **预期新增测试**：5–8 项（config dict 键完整性、缓存清理只删 `.temp.mkv`、主题样式调用）。
7. **locale**：缓存清理若调整文案需同步 4 个 locale 并跑 `check_lang.py`。
8. **线程边界**：`build_job_config` 为纯读取，在主线程调用，无风险。
9. **完成判定**：`ui/main_window.py` ≤ 1100 行且 public method ≤ 60；`SettingsController.restore_defaults` ≤ 60 行；三绿。

#### 步骤 S8：异常类型化清单推进（对应 P2-3）

1. **目标**：按文件分批把 `except Exception` 换成具体类型，每批一个提交。
2. **顺序**：`workers/encoder.py`（11 处）→ `workers/analyzer.py`（5 处）→ `ui/main_window.py`（2 处）→ 其余。
3. **规则**：每替换一处，配套一条失败路径测试（构造对应异常，断言日志/信号行为）；无法收窄的保留 `# noqa: BLE001` 并注释原因。
4. **完成判定**：`grep -rn "except Exception" workers/ ui/ main.py utils.py | grep -v noqa | wc -l` 为 0 或每处有注释理由。

#### 步骤 S9：测试提速（对应 P3-4，收尾）

1. **目标**：全量测试 < 180 秒。
2. **方法**：`tests/test_encoder.py`、`tests/test_output_strategy.py`、`tests/test_log_manager.py` 中的 `time.sleep` 改为可注入短延迟（模块级常量 + monkeypatch），重试逻辑测试用假时钟。
3. **不修改**：生产代码的重试间隔默认值。
4. **完成判定**：`time uv run python -m unittest discover -s tests` < 180s 且 302+ 项全绿。

### 1.2 类型注解补全

| 任务 | 范围 | 优先级 |
|------|------|--------|
| 核心工具函数 | `utils.py` 全部函数添加参数/返回类型 | 🟡 高 |
| 工作线程 | `workers/` 下所有类的 `__init__` 和公开方法 | 🟡 高 |
| 配置常量 | `config.py` 全部常量添加类型标注 | 🟢 中 |
| 接口定义 | `ui/interfaces.py` 的 UI 组件方法 | 🟢 中 |

**验收标准**：
- [ ] `pyright --level strict` 通过率 ≥ 90%
- [ ] CI 中增加类型检查步骤

### 1.3 测试覆盖率提升

| 任务 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| `EncoderWorker` 单元测试 | ✅ 完成 | 已添加输出落盘失败、跨磁盘回退、重试与编码流程测试；当前编码器测试覆盖 22 项 | 🔴 最高 |
| `AnalysisWorker` 单元测试 | ✅ 完成 | 已添加媒体报告渲染、缩略图生成、时长解析和错误路径测试 | 🟡 高 |
| UI 组件测试 | ✅ 完成 | 已添加文件列表、日志、主页布局、设置控制器、欢迎向导和转码接入测试 | 🟡 高 |
| 集成测试 | ✅ 完成 | 已添加 MainWindow 与文件列表、日志、转码控制器的接入回归测试 | 🟢 中 |
| 现有测试增强 | ✅ 完成 | 已补齐路径冲突、缓存清理边界、依赖探测超时回收、媒体报告 HTML 转义与配置百分号回归测试；当前全套测试 302 项 | 🟢 中 |

**工具建议**：`pytest` + `pytest-qt` + `pytest-mock`

**验收标准**：
- [ ] 整体测试覆盖率 ≥ 70%（当前已验证 302 项测试通过，覆盖率尚未统计）
- [ ] 每个核心模块有至少一个测试文件
- [ ] CI 中测试步骤在 5 分钟内完成

### 1.4 异常处理细化

> 2026-08-19 已完成本轮输出落盘失败状态、依赖探测超时回收、缓存清理边界和报告 HTML 转义修复；宽泛异常捕获的全量替换仍未完成。

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 替换宽泛 `except Exception` | 将 `utils.py`、`encoder.py`、`ui/main_window.py` 中的宽泛捕获改为具体异常类型 | 🟡 高 |
| 错误日志增强 | 在捕获异常时记录完整的 traceback 到日志 | 🟢 中 |
| 用户友好的错误提示 | 区分"可恢复错误"和"致命错误"，UI 提示更具体 | 🟢 中 |

**验收标准**：
- [ ] 项目中不再有 `except Exception: pass` 的静默吞错误模式
- [ ] 所有异常捕获至少输出一条日志

### 1.5 并发安全加固

| 任务 | 说明 | 优先级 |
|------|------|--------|
| 日志队列线程安全 | 使用 `queue.Queue` 替代 `list + QMutex` | 🟡 高 |
| 文件列表操作保护 | 对 `self.selected_files`、`self.path_to_item` 等共享状态的写操作加锁 | 🟢 中 |
| 编码器状态一致性 | 审查 `coordinator.py` 中 `_workers_by_task` / `_task_by_path` 的并发访问 | 🟢 中 |

**验收标准**：
- [ ] 在极端并发场景（4 路同时编码 + 用户频繁操作 UI）下不出现竞态崩溃

---

## Phase 2：🚀 核心功能增强

> **目标**：扩大用户覆盖，提升编码体验，补齐核心功能缺口。

### 2.1 HEVC 编码支持 🔥

**动机**：RTX 30 系及以下、Intel 11-12 代核显、AMD RX 6000 系及以下**不支持 AV1 硬件编码**，但支持 HEVC。添加 HEVC 支持可以将用户基数扩大 3-5 倍。

| 任务 | 说明 | 工作量估计 |
|------|------|-----------|
| `config.py` 增加编码器常量 | 新增 `ENC_NVENC_HEVC`、`ENC_QSV_HEVC`、`ENC_AMF_HEVC` | 🔹 小 |
| 编码器配置表扩展 | `ENCODER_CONFIGS` 中为每个 HEVC 编码器添加 `pix_fmt`、`preset`、`ICQ` 映射 | 🔹 小 |
| UI 编码器选择 | 下拉框增加 HEVC 选项，分组显示（AV1 / HEVC） | 🔹 小 |
| `encoder.py` 编码参数构造 | 根据编码器类型选择正确的 FFmpeg 编码器名称和参数 | 🔹🔹 中 |
| 色彩/色深适配 | HEVC 支持 10-bit 编码（`p010le`），与 AV1 保持一致 | 🔹 小 |
| 文档更新 | README 增加 HEVC 支持说明和硬件要求 | 🔹 小 |

**验收标准**：
- [ ] 三种硬件平台（Intel/NVIDIA/AMD）的 HEVC 编码均可正常工作
- [ ] HEVC 编码的 VMAF 探测与 AV1 策略一致
- [ ] 用户可一键切换编码器类型

### 2.2 预设管理器（Profile Manager）

**动机**：当前 Light/Balanced/Heavenly 三种预设是硬编码的，用户无法自定义。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 预设数据结构定义 | 定义 `EncodingProfile` 数据类，包含所有编码参数 | 🔹 小 |
| 预设存储 | 使用 JSON 格式存储预设文件，支持导入/导出 | 🔹🔹 中 |
| UI 预设选择器 | 在设置卡片中增加预设下拉框 + 管理按钮 | 🔹🔹 中 |
| 预设管理对话框 | 新建、编辑、删除、重命名预设的对话框界面 | 🔹🔹🔹 大 |
| 预设与编码器绑定 | 允许为不同编码器（AV1/HEVC/QSV/NVENC）保存独立预设 | 🔹🔹 中 |

**验收标准**：
- [ ] 用户可以从 UI 保存、加载、编辑预设
- [ ] 预设可以导出为 `.json` 文件与他人分享
- [ ] 内置预设（Light/Balanced/Heavenly）不可删除但可重置

### 2.3 按文件独立参数设置

**动机**：用户可能希望为不同文件设置不同 VMAF 目标或编码参数。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 文件列表右键菜单 | 增加"单独设置参数"选项 | 🔹 小 |
| 参数覆盖对话框 | 显示当前文件的可调参数（VMAF、预设、偏移、色彩模式等） | 🔹🔹 中 |
| 参数覆盖存储 | 在 `file_metadata` 中存储每个文件的覆盖参数 | 🔹 小 |
| 编码器读取覆盖参数 | `EncoderWorker` 读取文件级别的参数覆盖 | 🔹 小 |

**验收标准**：
- [ ] 文件列表中的每个文件可以独立设置 VMAF、预设、偏移
- [ ] 参数覆盖不会影响其他文件
- [ ] 有"清除所有覆盖"和"重置为默认"的批量操作

### 2.4 定时任务与自动操作增强

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 定时开始编码 | 指定时间自动启动转码队列 | 🔹🔹 中 |
| 完成后休眠 | 增加"完成后休眠"选项（与关机并列） | 🔹 小 |
| 通知集成 | 完成后弹出 Windows 通知、可选 Bark/Webhook 推送 | 🔹🔹 中 |
| 完成后自定义脚本 | 允许用户指定批处理脚本在编码完成后执行 | 🔹 小 |

**验收标准**：
- [ ] 定时器在指定时间准确触发编码
- [ ] 所有通知方式在编码完成后成功发送

### 2.5 编码统计与历史

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 统计数据库 | 使用 SQLite 记录每次编码任务的文件名、大小变化、编码时间、速度、参数 | 🔹🔹 中 |
| 历史记录界面 | 新增"编码历史"界面，显示历史任务列表 | 🔹🔹🔹 大 |
| 统计导出 | 支持导出为 CSV/HTML 报告 | 🔹 小 |
| 文件对比视图 | 显示原片和编码后的文件大小、码率、VMAF 对比 | 🔹🔹 中 |

**验收标准**：
- [ ] 每次编码完成后自动记录统计信息
- [ ] 用户可以查看、搜索、过滤历史记录
- [ ] 统计信息可以在软件重装后保留（使用标准路径存储）

---

## Phase 3：🌐 生态与扩展

> **目标**：让工具更自动化、可远程控制、与 NAS 生态深度集成。

### 3.1 热文件夹监视（Watch Folder）

**动机**：NAS 用户的核心需求——丢文件进去自动编码。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 文件系统监视 | 使用 `watchdog` 库监控指定文件夹 | 🔹🔹 中 |
| UI 热文件夹管理 | 新增热文件夹设置界面（添加/删除/启用/禁用） | 🔹🔹 中 |
| 文件筛选规则 | 文件扩展名过滤、最小文件大小、文件年龄（避免处理正在复制的文件） | 🔹🔹 中 |
| 完成后动作 | 配置编码完成后：删除源文件、移动到归档目录、或原地保留 | 🔹 小 |
| 系统托盘集成 | 最小化到系统托盘，后台运行监视 | 🔹🔹🔹 大 |

**验收标准**：
- [ ] 热文件夹在 30 秒内检测到新文件并自动加入队列
- [ ] 大文件复制期间不会触发处理（等待文件写入完成）
- [ ] 支持同时监视多个文件夹

### 3.2 Web 远程控制面板

**动机**：NAS 通常无头运行，Web 控制是 NAS 用户最自然的交互方式。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 轻量级 Web 服务器 | 使用 FastAPI 或 Quart 在软件中嵌入 HTTP 服务器 | 🔹🔹🔹 大 |
| WebSocket 实时推送 | 推送编码进度、日志、并发状态 | 🔹🔹🔹 大 |
| 前端控制面板 | 响应式 Web 界面：任务列表、进度条、日志、控制按钮 | 🔹🔹🔹🔹 超大 |
| API 认证 | 简单的 Token 或 Basic Auth 认证 | 🔹🔹 中 |
| 开机自启 Web 服务 | 配置选项：启动时自动开启 Web 服务器 | 🔹 小 |

**前端技术选型建议**：
- **轻量方案**：HTML + HTMX + Chart.js（无需构建工具）
- **完整方案**：Vue 3 + Vite + Tailwind CSS（需要 npm 构建）

**验收标准**：
- [ ] 手机和桌面浏览器均可访问控制面板
- [ ] 实时进度延迟 < 2 秒
- [ ] 可以从 Web 界面启动、暂停、停止转码

### 3.3 元数据与媒体库深度集成

**动机**：Emby/Plex/Jellyfin 用户希望编码后的文件直接可被媒体库识别。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 编码后媒体库刷新 | 编码完成后触发 Emby/Plex/Jellyfin 的库刷新 API | 🔹🔹 中 |
| 文件名标准化 | 提供文件名模板配置（如 `{title} ({year}).mkv`） | 🔹 小 |
| NFO 文件生成 | 可选生成 Kodi/Emby 兼容的 NFO 元数据文件 | 🔹🔹 中 |
| 硬链接支持 | 支持在目标目录创建硬链接而非复制文件，节省空间 | 🔹 小 |

**验收标准**：
- [ ] 编码完成后自动通知 Emby 刷新库
- [ ] 文件名模板支持自定义变量

### 3.4 编码队列持久化

**动机**：软件意外关闭后，当前编码队列丢失。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 队列序列化 | 关机时将当前队列状态保存到 JSON | 🔹 小 |
| 启动恢复 | 启动时检测是否有未完成的队列，询问用户是否恢复 | 🔹 小 |
| 断点续传增强 | 对已部分完成的文件，跳过或重新处理 | 🔹🔹 中 |

**验收标准**：
- [ ] 软件崩溃后重新启动，队列完整恢复
- [ ] 已完成编码的文件不会重复处理

---

## Phase 4：🏗️ 架构现代化

> **目标**：为长期发展奠定基础，解决可扩展性、跨平台和性能瓶颈。

### 4.1 插件系统

**动机**：允许社区贡献新的编码器后端、滤镜、输出目标。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 插件接口定义 | 定义 `EncoderPlugin`、`FilterPlugin`、`OutputPlugin` 抽象基类 | 🔹🔹🔹 大 |
| 插件发现与加载 | 使用 `importlib` + 约定目录动态加载插件 | 🔹🔹 中 |
| 插件管理 UI | 插件列表、启用/禁用、配置界面 | 🔹🔹🔹 大 |
| 示例插件 | 提供一个示例插件（如软件编码器 `libsvtav1`）作为参考 | 🔹🔹 中 |

**验收标准**：
- [ ] 第三方开发者可以编写一个 50 行 Python 文件的插件并加载
- [ ] 插件可以贡献新的编码器、滤镜或输出目标

### 4.2 分布式编码支持

**动机**：对于大型 NAS 库，单机编码速度不够快。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 分布式任务分发 | 主节点将编码任务分发给多个工作节点 | 🔹🔹🔹🔹🔹 **超大** |
| 工作节点代理 | 工作节点上运行的轻量级代理程序 | 🔹🔹🔹🔹 大 |
| 任务结果收集 | 主节点收集编码结果并处理输出 | 🔹🔹🔹 大 |
| 节点状态监控 | 在 UI 中显示各工作节点的状态、负载、温度 | 🔹🔹🔹 大 |

**注意**：这是一个长期愿景，属于实验性功能。第一版可以使用简单的 SSH + rsync 分发模式。

### 4.3 跨平台支持（Linux）

**动机**：很多 NAS 系统运行 Linux（如 Unraid、TrueNAS、Debian）。

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 平台抽象层 | 将 Windows 特定的 API 调用（`ctypes.windll`、`taskkill`）抽象为平台接口 | 🔹🔹🔹 大 |
| GPU 检测 | 使用 `pynvml`、`pyamdgpu` 等跨平台 GPU 检测库 | 🔹🔹 中 |
| 替代 UI 后端 | Linux 上可能无法使用 QFluentWidgets 的 Mica 特效，需要降级方案 | 🔹🔹🔹 大 |
| 打包分发 | 提供 AppImage 或 Flatpak 包 | 🔹🔹 中 |
| Wayland 兼容性 | 确保在 Wayland 会话下正常运行 | 🔹🔹 中 |

**注意**：跨平台支持是重大工程，建议在 Phase 4 后期评估需求后再决定是否投入。

### 4.4 性能优化专项

| 任务 | 说明 | 工作量 |
|------|------|--------|
| 缩略图缓存优化 | 使用 LRU 缓存 + 磁盘缓存，减少重复 ffmpeg 调用 | 🔹🔹 中 |
| 文件列表虚拟化 | 当文件数量超过 100 时，使用虚拟滚动提高 UI 响应速度 | 🔹🔹🔹 大 |
| 日志系统性能 | 使用环形缓冲区（Ring Buffer）替代线性增长列表，控制内存占用 | 🔹 小 |
| 启动速度优化 | 延迟加载非必要模块，懒加载界面 | 🔹🔹 中 |
| 内存使用优化 | 使用 `memory_profiler` 分析内存热点，优化大文件列表场景 | 🔹🔹 中 |

**验收标准**：
- [ ] 500+ 文件列表时 UI 滚动不卡顿
- [ ] 软件启动时间 < 3 秒（从双击到界面显示）
- [ ] 编码过程中内存占用不超过 512MB（不含 ffmpeg 子进程）

---

## 附录

### A. 优先级速查表

| 项目 | 影响力 | 工作量 | 优先级 |
|------|--------|--------|--------|
| 🧹 文件规模与职责治理（1.1.1 持续规则） | 高 | 小 | **持续** |
| 🧹 encoder 命令/进度抽取（S1–S3） | 高 | 中 | **P1** |
| 🧹 interfaces 页头去重（S4） | 中 | 小 | **P1** |
| 🧹 FileListManager 行构建抽取（S5） | 中 | 小 | **P1** |
| 🧹 dependency 探测分解（S6） | 中 | 小 | **P2** |
| 🧹 settings_controller 收敛（S7） | 中 | 中 | **P2** |
| 🧹 异常类型化（S8） | 中 | 中 | **P2** |
| 🧹 测试提速（S9） | 低 | 小 | **P3** |
| 🚀 HEVC 编码支持 | 最高 | 小 | **P0（功能线）** |
| 🧪 测试覆盖率提升 | 高 | 中 | **P0（功能线）** |
| 📋 预设管理器 | 高 | 中 | **P1（功能线）** |
| 🔍 类型注解补全 | 中 | 中 | **P1（功能线）** |
| 🗓️ 定时任务增强 | 中 | 中 | **P1（功能线）** |
| 📁 热文件夹监视 | 高 | 大 | **P2（功能线）** |
| 🌐 Web 远程控制 | 高 | 超大 | **P2（功能线）** |
| 📊 编码统计历史 | 中 | 大 | **P2（功能线）** |
| 🔌 插件系统 | 中 | 超大 | **P3** |
| 🖥️ 跨平台 Linux | 中 | 超大 | **P3** |
| 🔄 分布式编码 | 低 | 极大 | **P4** |

> 注：重构线（1.1.1–1.1.3，P0–P3 无阻塞项）与功能线（HEVC 等）可并行推进；重构线各步骤不改用户可见行为，功能线开工前应先完成对应的 P1 重构以获得测试保护网。

### B. 依赖关系图

```
Phase 1 (代码质量)
    │
    ├──→ 巨型文件拆分 ──→ 更容易添加新功能
    ├──→ 测试覆盖率提升 ──→ 安全重构的前提
    └──→ 异常处理细化 ──→ 更可靠的编码流程
                │
                ▼
Phase 2 (功能增强)
    │
    ├──→ HEVC 支持 ──→ 扩大用户基础
    ├──→ 预设管理器 ──→ 用户体验升级
    ├──→ 热文件夹 ──→ 自动化基础
    └──→ 编码统计 ──→ 数据驱动优化
                │
                ▼
Phase 3 (生态扩展)
    │
    ├──→ Web 控制面板 ──→ 远程使用
    ├──→ 媒体库集成 ──→ NAS 生态
    └──→ 队列持久化 ──→ 可靠性提升
                │
                ▼
Phase 4 (架构现代化)
    │
    ├──→ 插件系统 ──→ 社区扩展
    ├──→ 跨平台 ──→ 更多平台
    └──→ 分布式 ──→ 性能突破
```

### C. 技术债务跟踪

| 技术债务项 | 引入版本 | 计划修复阶段 | 状态 |
|-----------|---------|-------------|------|
| `main_window.py` 过大 | v1.0.0 | Phase 1 | ✅ 已完成 |
| `encoder.py` 的巨型 `run()` | v1.0.0 | Phase 1 | ✅ 已完成 |
| 宽泛异常捕获 | v1.0.0 | Phase 1.1.3 S8 | 🔄 部分修复（静默吞错已清零，26 处宽泛捕获待类型化） |
| 缺少类型注解 | v1.0.0 | Phase 1 | 📋 待办 |
| 缺失 HEVC 编码器 | v1.0.0 | Phase 2 | 📋 待办 |
| 硬编码预设配置 | v1.0.0 | Phase 2 | 📋 待办 |
| 无队列持久化 | v1.0.0 | Phase 3 | 📋 待办 |
| `encoder.py` 职责混合（命令构造/进度解析内联） | v1.0.0 | Phase 1.1.2 P1-1 | 📋 待办（S1–S3） |
| `interfaces.py` 页头 4 份重复 | v1.2.0 | Phase 1.1.2 P1-2 | 📋 待办（S4） |
| `FileListManager` 行构建藏于计数方法 | v1.4.0 | Phase 1.1.2 P1-3 | 📋 待办（S5） |
| `DependencyWorker.run` 长方法 | v1.0.0 | Phase 1.1.2 P2-1 | 📋 待办（S6） |
| 测试套件过慢（379s/302 项） | v1.4.0 | Phase 1.1.2 P3-4 | 📋 待办（S9） |

### D. 贡献指南

如果你希望参与路线图中的某个任务，请参考以下流程：

1. 在 GitHub Issues 中搜索对应任务的标签（如 `roadmap-phase1`）
2. 在 Issue 下留言说明你希望参与
3. Fork 仓库并创建特性分支
4. 提交 PR 并关联对应 Issue
5. 等待 Code Review 和 CI 通过

---

> 🌟 **愿景**：让魔法少女工坊成为 NAS 用户和仓鼠党心中最强大、最易用的智能视频编码工具。  
> 每一行代码的优化，都是为了在保持画质的前提下，拯救更多珍贵的存储空间。  
> — **泠萌404 (Master)**
