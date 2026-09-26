# 架构总览（从 AGENTS.md §3 移出）

## 文件地图

```
main.py                 入口；设置 AppUserModelID、高 DPI、全局字体，实例化 MainWindow
config.py               全局常量：版本(VERSION)、编码器名(ENC_QSV/ENC_NVENC/ENC_AMF)、
                        默认参数、DEFAULT_SETTINGS、ENCODER_CONFIGS、像素格式常量
utils.py                工具函数：resource_path()、get_subprocess_flags()、to_long_path()、
                        配置/缓存路径 (get_default_cache_dir)
check_lang.py           i18n 一致性校验脚本（--check 只读模式）

ui/
  main_window.py        主窗口（FluentWindow）；混合 UI + 业务逻辑；约 1,258 行
  interfaces.py         子界面：MediaInfo / Profile / Credits / Settings，各自实现 retranslate_ui()
  common.py             可复用 UI 组件：DragDropMixin、DroppableListWidget、ClickableBodyLabel 等
  config_manager.py     配置读写服务（config.ini 读取/保存/合并/重置），不操作 UI 控件
  file_list_manager.py  FileListManager：文件列表状态 + 时长/缩略图 worker 队列
  log_manager.py        LogManager：日志缓冲队列与分批刷新（queue.Queue，无锁）
  settings_controller.py 设置编排（加载/保存/恢复默认/主题切换/设置页保存请求）
  home_ui_builder.py    主页布局构建器（header/内容区/卡片/状态栏/日志区/footer）
  welcome_wizard.py     初次运行欢迎向导（MessageBoxBase 子类）

workers/                所有后台线程，均继承 BaseWorker(QThread)
  base.py               BaseWorker：is_running 标志 + stop()
  encoder.py            EncoderWorker：VMAF 探测 + FFmpeg 转码（核心）；约 1,105 行
  command_builder.py    FFmpeg / ab-av1 命令构造纯函数（不导入 Qt/config）
  coordinator.py        EncodingCoordinator：批次调度、并发槽管理、错误队列
  transcode_controller.py TranscodeController：Coordinator 的无 UI 门面（facade）
  concurrency_policy.py DynamicConcurrencyPolicy：自适应并发算法（手动 1-4，自动最高 3）
  analyzer.py           DurationWorker / ThumbnailWorker / AnalysisWorker
  media_report.py       ffprobe JSON -> 媒体报告 HTML（纯渲染，字段全转义）
  dependency.py         DependencyWorker：启动时检查 ffmpeg + GPU 编码器可用性
  ffmpeg_retry.py       错误分类（硬件设备/字幕）+ 降级重试状态机
  transcode_paths.py    TaskPaths、输出路径构造、find_output_conflicts()、会话隔离
  transcode_schedule.py BatchSchedule + TaskState 状态机
  batch_progress.py     批次加权进度计算
  ab_av1_result.py      ab-av1 输出解析（CRF/VMAF 候选 + 质量回退）
  output_strategy.py    输出落盘策略（移动/备份/恢复，路径统一经 to_long_path()）
  system_metrics.py     Windows CPU/内存采样（ctypes + GetSystemTimes）

i18n/
  translator.py         Translator：pkgutil 动态加载 locales，config.ini 持久化语言选择
  locales/              zh_CN / zh_TW / en_US / ja_JP，每个文件含 translation dict + language_name

tests/                  unittest 风格；用 FakeSignal/FakeWorker 隔离 Qt
tools/                  二进制：ffmpeg.exe / ffprobe.exe / ab-av1.exe（不入 git，但仓库已提供）
installer/              Inno Setup 脚本 (.iss)
.github/workflows/      autobuild.yml（打包发版）、verify.yml（lint + 测试 + i18n 校验）
docs/                   FAQ、VMAF 指南、硬件自测、Release notes、ROADMAP.md
```

## 关键数据流

1. 用户在 `MainWindow` 拖入/选择文件 -> `DurationWorker` 异步探测时长/元数据 -> `ThumbnailWorker` 生成缩略图
2. 点击开始 -> 构造 `config` dict -> `EncodingCoordinator.start()`
3. Coordinator 按 `BatchSchedule` + `DynamicConcurrencyPolicy.target_concurrency` 填充并发槽
4. 每个槽创建一个 `EncoderWorker`：先用 `ab-av1` 探测 VMAF 最优 CRF，再用 `ffmpeg` 转码
5. 失败时经 `ffmpeg_retry.py` 分类，按硬件解码降级 / 字幕丢弃顺序重试（最多 3 次）
6. 信号层层回传：Worker -> Coordinator -> MainWindow -> UI 更新

## 并发模型

- **不是 asyncio**，而是 Qt 的 `QThread` + `Signal/Slot` 跨线程通信
- `EncodingCoordinator` 在主线程运行，`EncoderWorker` 在各自线程运行
- 并发上限：手动 1-4（`concurrency_policy.py` 中 `max(1, min(4, manual_limit))`），
  自动从 1 起根据吞吐量/CPU/内存动态调整，最高 3（`auto_max=3`）
- 并发降级**不会**中止已运行的任务，只影响后续填充

## 缓存与输出隔离

- 每个批次创建独立 `mgw-session-<uuid>` 目录（`SESSION_PREFIX`），每个文件在其下创建
  `task-<id>` 子目录，避免并发任务互删缓存
- `transcode_paths.find_output_conflicts()` 会在开工前检测多输入写同一输出的风险，**不要**绕过
- 临时输出文件统一命名 `output.temp.mkv`，最终通过 `shutil.move` 原子替换；
  跨盘失败的回退逻辑在 `workers/output_strategy.py`

## 错误降级顺序

`ffmpeg_retry.py` 的三阶段重试是**互不重复**的组合（每类降级只触发一次）：

1. 硬件解码设备失败 -> 切 CPU 软件解码（编码仍用 NVENC 等）
2. 字幕流错误 -> 丢弃字幕
3. 二者可按任意顺序组合

不要把“硬件资源错误”（OOM / 设备忙）和“硬件设备初始化失败”混淆：前者由
`is_hardware_resource_error()` 识别并走 `resource_error_signal` 触发并发降级；
后者走 `next_retry_state()` 的重试降级。

## 进度计算

批次进度按**视频时长加权**（`batch_progress.calculate_batch_progress`），探测阶段占 0-15%
（`map_probe_progress`），编码阶段占 15-100%（`map_encode_progress`，即 `round(15 + percent * 0.85)`）。
修改进度映射时注意这两个区间。
