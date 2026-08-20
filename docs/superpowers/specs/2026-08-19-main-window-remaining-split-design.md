# MainWindow 剩余职责拆分设计

日期：2026-08-19

## 目标

完成 `ui/main_window.py` 的剩余三块职责拆分，在不改变现有用户行为和 Qt 信号链的前提下，将文件列表、日志、转码生命周期从主窗口移出，使主窗口最终缩减到 1500 行以内。

## 方案

采用独立 manager/controller 类，通过显式 callbacks 连接主窗口。管理器不持有 `MainWindow`，不直接访问主窗口的业务字段；需要更新 UI 时调用注入的回调或发出 Qt 信号。主窗口继续负责布局、对话框、InfoBar、翻译和控件启停。

### FileListManager

`ui/file_list_manager.py` 提供 `FileListManager`，管理：

- `selected_files`、`path_to_item`、`file_metadata`
- 时长/缩略图缓存与有界 worker 队列
- 文件/目录扫描、列表行创建、删除和清空
- 文件进度、统计、状态图标更新
- 拖放区域视觉状态

构造函数接收列表控件、占位符、计数标签、线程限制回调、日志回调、任务运行状态回调和列表变更回调。所有 worker 仍在 Qt 主线程创建并通过信号更新 manager；manager 不启动新的线程模型。清空确认和 InfoBar 保留在主窗口包装方法中，manager 提供 `clear()` 和 `remove()` 原子操作。

主窗口保留 `add_source_paths`、`handle_dropped_paths`、选择文件/目录对话框和用户提示作为薄包装，转码配置通过 manager 的快照获取。

### LogManager

`ui/log_manager.py` 提供 `LogManager`，内部使用标准库 `queue.Queue` 接收 `(timestamp, message, level)`，替换主窗口的 `QMutex + list`。`flush()` 在主线程定时器回调中取出一批消息并更新传入的 `TextEdit`，保留现有主题颜色、级别图标、日志上限和翻译行为。管理器不创建或拥有窗口定时器；主窗口创建 `QTimer` 并连接 `flush()`，这样关闭窗口时生命周期清晰。

为保持兼容，`log(message, level)` 和 `process_log_queue()` 仍由主窗口提供一行转发方法，已有 worker 信号连接不变。

### TranscodeController

`workers/transcode_controller.py` 提供 `TranscodeController`，包装 `EncodingCoordinator` 的创建、启动、暂停、继续、停止、错误决策和关闭等待。它只接收一个配置构建回调和 UI 回调字典，不访问 Qt 控件。Coordinator 的原始信号转发到回调：日志、总进度、当前进度、文件进度/统计/状态、完成、错误、并发状态。

主窗口的 `start_task` 负责校验控件输入并构建配置，controller 负责创建/启动 coordinator 和生命周期状态；主窗口继续负责按钮、组合框和进度控件的启停。`pause_task`、`stop_task`、`on_finished` 变为薄包装。依赖检查线程不并入 controller，仍由主窗口单独管理，避免把外部依赖探测和转码批次混为一体。

## 迁移顺序

1. 先实现并测试 `FileListManager` 的纯状态和 Qt 行更新接口，接入主窗口。
2. 再实现并测试 `LogManager`，接入定时刷新和现有日志调用。
3. 最后实现并测试 `TranscodeController`，迁移 Coordinator 信号绑定和任务生命周期。
4. 为拆分模块建立包目录及 `__init__.py` 导出，避免在顶层模块引入循环依赖。
5. 更新路线图并执行全量 unittest、Ruff、语言校验。

## 兼容性与风险控制

- 不修改 Coordinator、EncoderWorker 的信号签名。
- 不让 worker 线程直接操作 UI。
- 不新增用户可见字符串；保留原有 `tr()` 调用。
- 每一块迁移后先运行对应测试，再运行全量测试。
- manager 使用显式回调和快照，避免通过 `parent` 隐式读取 `MainWindow` 字段。
