language_name = "简体中文"

# 这是一个充满“中二”风格（二次元/魔法设定）的语言文件。
# 右侧注释为实际对应的技术功能。
translation = {
    # -------------------------------------------------------------------------
    # Main Window (main.py)
    # -------------------------------------------------------------------------
    "app.title": "魔法少女工坊", # 应用主标题
    "app.subtitle": "AV1 硬件加速魔力驱动 · 绝对领域 Edition", # 应用副标题
    "app.welcome": "欢迎来到魔法少女工坊 ✨", # 欢迎信息
    "app.designed_by": "Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # 设计者和技术支持信息

    # -------------------------------------------------------------------------
    # Home Interface (view/home_interface.py)
    # -------------------------------------------------------------------------
    "home.title": "炼成祭坛", # 主页
    "home.header.title": "炼成祭坛", # 主页标题
    "home.header.subtitle": "AV1 硬件加速魔力驱动 · 绝对领域 Edition", # 主页副标题
    "home.header.theme_combo.auto": "世界线收束 (Auto)", # 主题：跟随系统
    "home.header.theme_combo.light": "光之加护 (Light)", # 主题：浅色模式
    "home.header.theme_combo.dark": "深渊凝视 (Dark)", # 主题：深色模式
    
    # Cache Card
    "home.cache_card.title": "魔力回路缓冲 (Cache)", # 缓存设置
    "home.cache_card.clear_button": "🧹 净化残渣", # 清除缓存
    "home.cache_card.path_placeholder": "ab-av1 临时文件存放处...", # 缓存路径输入框的占位符
    "home.cache_card.browse_button": "锁定坐标", # 浏览缓存路径按钮
    
    # Settings Card
    "home.settings_card.encoder.label": "魔力核心 (Encoder)", # 编码器选择 (QSV/NVENC/AMF)
    "home.settings_card.vmaf.label": "视界还原度 (VMAF)", # VMAF 目标画质评分
    "home.settings_card.bitrate.label": "共鸣频率 (Bitrate)", # 码率控制
    "home.settings_card.preset.label": "咏唱速度 (Preset)", # 编码预设 (速度 vs 画质)
    "home.settings_card.offset.label": "灵力偏移 (Offset)", # 硬件编码参数微调
    "home.settings_card.loudnorm.label": "音量均一化术式 (Loudnorm)", # 音频响度统一
    "home.settings_card.nv_aq.label.nvidia": "NVIDIA 感知增强 (AQ)", # NVIDIA AQ 设置标签
    "home.settings_card.nv_aq.label.amd": "AMD 预分析 (PreAnalysis)", # AMD 预分析设置标签
    "home.settings_card.nv_aq.label.intel": "Intel 深度分析 (Lookahead)", # Intel 深度分析设置标签
    "home.settings_card.nv_aq.on": "展开", # 开启 (Enable)
    "home.settings_card.nv_aq.off": "收束", # 关闭 (Disable)
    "home.settings_card.save_button": "💾 铭刻记忆 (Save)", # 保存设置
    "home.settings_card.reset_button": "↩️ 记忆回溯 (Reset)", # 重置设置
    "home.settings_card.loudnorm_mode.auto": "调和之咏 (智能绕行多声道)", # 自动 (Auto: 5.1/7.1 不进行响度均衡)
    "home.settings_card.loudnorm_mode.always": "归一之咏 (强制同调万物声)", # 强制开启 (Always)
    "home.settings_card.loudnorm_mode.disable": "寂静之咏 (保留原始声之貌)", # 禁用 (Disable)
    
    # Action Card
    "home.action_card.save_mode.save_as": "开辟新世界 (Save As)", # 另存为
    "home.action_card.save_mode.overwrite": "元素覆写 (Overwrite)", # 覆盖原文件
    "home.action_card.save_mode.remain": "元素保留 (Remain)", # 保留源文件
    "home.action_card.export_path_placeholder": "新世界坐标...", # 导出路径输入框的占位符
    "home.action_card.choose_button": "指定坐标", # 选择导出路径按钮
    "home.action_card.start_button": "✨ 缔结契约 (Start)", # 开始转码
    "home.action_card.pause_button": "⏳ 时空冻结 (Pause)", # 暂停
    "home.action_card.stop_button": " 契约破弃 (Stop)", # 停止
    
    # Source Card
    "home.source_card.title": "素材次元 (Source)", # 输入源设置
    "home.source_card.folder_button": "以文件夹之名", # 选择文件夹
    "home.source_card.file_button": "以文件之名", # 选择文件
    
    # File List Card
    "home.file_list_card.title": "次元空间 (List)", # 任务列表
    "home.file_list_card.clear_button": "归于虚无", # 清空列表
    "home.file_list_card.placeholder": "将素材投入炼成法阵...", # 文件列表的占位符
    "list.item.remove_button": "放逐", # 列表中移除文件按钮
    "list.item.duration_button": "窥探时间线", # 列表中查看时长按钮
    
    # Status Bar
    "home.status_bar.current_label": "当前炼成:", # 状态栏当前任务标签
    "home.status_bar.total_label": "总体进度:", # 状态栏总体进度标签

    # -------------------------------------------------------------------------
    # Media Info Interface (view/info_interface.py)
    # -------------------------------------------------------------------------
    "info.title": "真理之眼", # “真理之眼”页面标题
    "info.drop_card.title": "真理之眼 · 物质解析", # “真理之眼”页面拖放卡片标题
    "info.drop_card.hint": "将未知的遗物投入此地以窥探真理... (拖拽文件)", # “真理之眼”页面拖放卡片提示
    "info.text_edit.placeholder": "等待魔力注入... (Waiting for file drop)", # “真理之眼”页面文本框占位符
    "info.buttons.add_to_list": "纳入祭坛", # “真理之眼”页面添加到列表按钮
    "info.buttons.clear": "因果切断", # “真理之眼”页面清空按钮
    "info.buttons.copy": "拓印报告", # “真理之眼”页面复制报告按钮
    "info.analysis.in_progress": "✨ 正在窥探真理，请稍候...", # “真理之眼”页面分析中提示
    "info.infobar.copy_success.title": "拓印完成", # “真理之眼”页面复制成功提示标题
    "info.infobar.copy_success.content": "鉴定报告已拓印至记忆水晶 (剪贴板)。", # “真理之眼”页面复制成功提示内容
    
    # Report Content
    "info.report.title": "📜 物质真理鉴定书",
    "info.report.perfect_form": "✨ 已是完美形态 (Perfect Form)",
    "info.report.parse_error": "💥 解析失败 (Error):",
    "info.report.container_title": "📦 容器构造 (Container)",
    "info.report.format": "• 封印术式 (Format):",
    "info.report.size": "• 物质总量 (Size):",
    "info.report.duration": "• 时间轴跨度 (Duration):",
    "info.report.total_bitrate": "• 综合魔力流速 (Total Bitrate):",
    "info.report.stream_count": "• 构成元素数 (Stream Count):",
    "info.report.video_title": "👁️ 视觉投影 (Stream #{idx} - Video)",
    "info.report.codec": "• 构筑术式 (Codec):",
    "info.report.profile_level": "• 术式阶位 (Profile/Level):",
    "info.report.resolution": "• 视界解析度 (Resolution):",
    "info.report.pix_fmt": "• 粒子排列 (Pixel Format):",
    "info.report.color_space": "• 色彩领域 (Color Space):",
    "info.report.bitrate": "• 魔力流速 (Bitrate):",
    "info.report.audio_title": "🔊 听觉共鸣 (Stream #{idx} - Audio)",
    "info.report.sample_rate": "• 共鸣频率 (Sample Rate):",
    "info.report.sample_fmt": "• 波形精度 (Sample Format):",
    "info.report.channel_layout": "• 空间声场 (Channel Layout):",
    "info.report.subtitle_title": "📝 铭文记载 (Stream #{idx} - Subtitle)",
    "info.report.language": "• 铭文语种 (Language):",

    # -------------------------------------------------------------------------
    # Profile Interface (view/profile_interface.py)
    # -------------------------------------------------------------------------
    "profile.title": "观测者档案", # “观测者档案”页面标题
    "profile.card.author_desc": "「 🌙 上班族 | 🎥 UP主 | 🛠️ 喜欢数码 」", # “观测者档案”页面作者描述
    "profile.card.author_motto": "“在代码的海洋里寻找魔法，在数码的世界里观测真理。”", # “观测者档案”页面作者座右铭
    "profile.buttons.bilibili": "📺 哔哩哔哩", # “观测者档案”页面哔哩哔哩按钮
    "profile.buttons.youtube": "▶️ YouTube", # “观测者档案”页面YouTube按钮
    "profile.buttons.douyin": "🎵 抖音", # “观测者档案”页面抖音按钮
    "profile.buttons.github": "🐙 GitHub", # “观测者档案”页面GitHub按钮
    "profile.buttons.show_wizard": "✨ 重温入职向导", # “观测者档案”页面显示欢迎向导按钮

    # -------------------------------------------------------------------------
    # Credits Interface (view/credits_interface.py)
    # -------------------------------------------------------------------------
    "credits.title": "羁绊之证", # “羁绊之证”页面标题
    "credits.card.contributor_role": "术式构筑协力", # “羁绊之证”页面贡献者角色
    "credits.card.intro": "工坊升级改造贡献者，其伟绩如下：", # “羁绊之证”页面介绍
    "credits.contributions.item1.title": "新魔力循环系统", # “羁绊之证”页面贡献项1标题
    "credits.contributions.item1.desc": "优化魔力流动稳定性", # “羁绊之证”页面贡献项1描述
    "credits.contributions.item2.title": "固化核心咏唱基盘", # “羁绊之证”页面贡献项2标题
    "credits.contributions.item2.desc": "提升仪式稳定性", # “羁绊之证”页面贡献项2描述
    "credits.contributions.item3.title": "圣遗物框架升级", # “羁绊之证”页面贡献项3标题
    "credits.contributions.item3.desc": "拥抱开源与更强的力量", # “羁绊之证”页面贡献项3描述
    "credits.contributions.item4.title": "炼成物便携化封装", # “羁绊之证”页面贡献项4标题
    "credits.contributions.item4.desc": "灵体更小，召唤更快", # “羁绊之证”页面贡献项4描述
    "credits.contributions.item5.title": "重构炼成工具链", # “羁绊之证”页面贡献项5标题
    "credits.contributions.item5.desc": "支持更灵活的术式分发", # “羁绊之证”页面贡献项5描述
    "credits.contributions.item6.title": "自动化炼金工坊", # “羁绊之证”页面贡献项6标题
    "credits.contributions.item6.desc": "云端自动构筑与分发", # “羁绊之证”页面贡献项6描述
    "credits.card.footer": "特别鸣谢: PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # “羁绊之证”页面页脚

    # -------------------------------------------------------------------------
    # Welcome Wizard (view/welcome_wizard.py)
    # -------------------------------------------------------------------------
    "welcome.wizard.title": "欢迎来到魔法少女工坊 ✨", # 欢迎向导标题
    "welcome.wizard.page1.title": "初次见面，适格者！", # 欢迎向导第一页标题
    "welcome.wizard.page1.content": "这是一个专为 NAS 仓鼠党打造的 AV1 硬件转码工具。\n\n它能利用 Intel/NVIDIA/AMD 显卡的算力，将视频体积缩小 30%-50%，同时保持肉眼无损的画质。\n\n接下来，让我为您简单介绍几个关键设置...", # 欢迎向导第一页内容
    "welcome.wizard.page2.title": "1. 魔力核心 (Encoder)", # 欢迎向导第二页标题
    "welcome.wizard.page2.content": "这是转码引擎的选择。\n\n• Intel QSV: 适合 Arc 独显 / Ultra 核显。\n• NVIDIA NVENC: 适合 RTX 40 系。\n• AMD AMF: 适合 RX 7000 系 / RDNA 3 架构核显。\n\n程序启动时会自动检测您的硬件，通常无需手动更改。", # 欢迎向导第二页内容
    "welcome.wizard.page3.title": "2. 视界还原度 (VMAF)", # 欢迎向导第三页标题
    "welcome.wizard.page3.content": "这是决定画质的核心指标 (0-100)。\n\n• 95+: 极高画质，适合收藏。\n• 93 (默认): 黄金平衡点，肉眼无损，体积缩减显著。\n• 90: 高压缩比，适合移动端观看。\n\n建议保持默认 93.0。", # 欢迎向导第三页内容
    "welcome.wizard.page4.title": "3. 咏唱速度 (Preset)", # 欢迎向导第四页标题
    "welcome.wizard.page4.content": "平衡编码速度与压缩效率 (1-7)。\n\n• 数字越小 (1-3): 速度慢，体积更小，画质更好。\n• 数字越大 (5-7): 速度快，体积稍大。\n• 默认 4: 均衡之选。\n\n挂机洗版建议设为 3 或 4。", # 欢迎向导第四页内容
    "welcome.wizard.page5.title": "4. 灵力偏移 (Offset)", # 欢迎向导第五页标题
    "welcome.wizard.page5.content": "针对硬件编码器的微调参数。\n\n由于硬件编码器效率不同，我们需要对 CPU 探测出的参数进行修正。\n• AMD 默认 -6\n• NVIDIA 默认 -4\n• Intel 默认 -2\n\n这能确保最终画质接近您的 VMAF 预期。", # 欢迎向导第五页内容
    "welcome.wizard.next_button": "翻阅魔导书", # 欢迎向导下一页按钮
    "welcome.wizard.skip_button": "瞬间展开", # 欢迎向导跳过按钮
    "welcome.wizard.start_button": "开始炼成", # 欢迎向导开始按钮

    # -------------------------------------------------------------------------
    # Dialogs
    # -------------------------------------------------------------------------
    "dialog.clear_list.title": "确认要归于虚无吗？", # 清空列表确认对话框标题
    "dialog.clear_list.content": "此操作将从祭坛中移除所有待净化的异变体，因果律将被重置。确定要继续吗？", # 清空列表确认对话框内容
    "dialog.clear_list.yes_button": "确定 (Void)", # 清空列表确认对话框“是”按钮
    "dialog.clear_list.cancel_button": "取消 (Stay)", # 清空列表确认对话框“取消”按钮
    "dialog.clear_cache.title": "确认要肃清魔力残渣吗？", # 清除缓存确认对话框标题
    "dialog.clear_cache.content": "这些是炼成仪式中产生的混沌碎片 (*.temp.mkv)，继续留存可能会干扰世界线的稳定。\n\n目标区域：{path}\n\n一旦执行肃清，这些碎片将彻底归于虚无，无法找回。确定要发动净化术式吗？", # 清除缓存确认对话框内容
    "dialog.clear_cache.yes_button": "发动净化 (Purify)", # 清除缓存确认对话框“是”按钮
    "dialog.clear_cache.cancel_button": "维持结界", # 清除缓存确认对话框“取消”按钮
    "dialog.error.skip_button": "跳过并继续 (Skip)", # 错误对话框“跳过”按钮
    "dialog.error.stop_button": "紧急中断", # 错误对话框“停止”按钮
    "dialog.dependency_missing.title": "⚠️ 结界破损警告 (Critical Error)", # 依赖缺失对话框标题
    "dialog.dependency_missing.content": "呜哇！大事不好了！(>_<)\n工坊的魔力回路检测到了严重的断裂！\n\n以下核心圣遗物似乎离家出走了：\n{missing_files}\n\n没有它们，炼成仪式将无法进行！\n请尽快将它们召回至工坊目录！", # 依赖缺失对话框内容
    "dialog.dependency_missing.yes_button": "召唤支援", # 依赖缺失对话框“是”按钮
    "dialog.dependency_missing.cancel_button": "我明白了", # 依赖缺失对话框“取消”按钮
    "dialog.language_change.title": "世界线变动确认", # 语言更改对话框标题
    "dialog.language_change.content": "为了让世界线收束至新的语言领域，建议重启观测终端。", # 语言更改对话框内容
    "dialog.language_change.yes_button": "遵命", # 语言更改对话框“是”按钮
    "dialog.language_change.cancel_button": "片刻之后", # 语言更改对话框“取消”按钮
    "dialog.encoder.crash_title": "术式崩坏警告", # 编码器崩溃警告标题
    "dialog.encoder.crash_content": "任务 {fname} 遭遇未知错误。\n是否跳过此任务并继续？", # 编码器崩溃警告内容

    # -------------------------------------------------------------------------
    # InfoBars / Notifications
    # -------------------------------------------------------------------------
    "infobar.success.settings_saved.title": "记忆已铭刻", # 设置已保存成功提示标题
    "infobar.success.settings_saved.content": "当前术式参数已铭刻至虚空记忆 (config.ini)", # 设置已保存成功提示内容
    "infobar.success.files_added.title": "素材投入成功", # 文件已添加成功提示标题
    "infobar.success.files_added.content": "已将 {count} 个素材投入炼成阵。", # 文件已添加成功提示内容
    "infobar.success.drag_drop_added.content": "通过空间传送投入了 {count} 个素材。", # 拖拽添加文件成功提示内容
    "infobar.success.cache_cleared.title": "净化完成", # 缓存已清除成功提示标题
    "infobar.success.cache_cleared.content": "已清除 {count} 个魔力残渣！", # 缓存已清除成功提示内容
    "infobar.success.synced.title": "同步成功", # 同步成功提示标题
    "infobar.success.synced.content": "该物质已成功纳入祭坛！", # 同步成功提示内容
    "infobar.info.settings_reset.title": "记忆回溯成功", # 设置已重置提示标题
    "infobar.info.settings_reset.content": "参数已重置为初始形态", # 设置已重置提示内容
    "infobar.warning.no_files_selected.title": "魔力不足", # 未选择文件警告提示标题
    "infobar.warning.no_files_selected.content": "请先指定要净化的目标！", # 未选择文件警告提示内容
    "infobar.warning.no_export_dir.title": "坐标丢失", # 未选择导出目录警告提示标题
    "infobar.warning.no_export_dir.content": "当前为“开辟新世界”模式，请为新世界指定坐标！", # 未选择导出目录警告提示内容
    "infobar.warning.no_files_found.title": "素材探知失败", # 未找到文件警告提示标题
    "infobar.warning.no_files_found.content": "该次元未发现可炼成的素材。", # 未找到文件警告提示内容
    "infobar.warning.no_new_files_dropped.title": "投入失败", # 未添加新文件警告提示标题
    "infobar.warning.no_new_files_dropped.content": "投入的素材无效，或已存在于法阵中。", # 未添加新文件警告提示内容
    "infobar.warning.task_running.title": "术式进行中", # 任务正在运行警告提示标题
    "infobar.warning.task_running.content": "炼成仪式尚未结束，无法强行重置次元空间！", # 任务正在运行警告提示内容
    "infobar.warning.invalid_cache_path.title": "坐标无效", # 无效缓存路径警告提示标题
    "infobar.warning.invalid_cache_path.content": "请先指定有效的魔力缓冲区域...", # 无效缓存路径警告提示内容
    "infobar.warning.dependency_check_skipped.title": "魔力核心重检已跳过", # 依赖检查已跳过警告提示标题
    "infobar.warning.dependency_check_skipped.content": "当前正在进行炼成，停止任务后再执行记忆回溯可触发自检。", # 依赖检查已跳过警告提示内容
    "infobar.warning.hardware_unsupported.title": "圣遗物排斥反应", # 硬件不支持警告提示标题
    "infobar.warning.hardware_unsupported.content": "汝之圣遗物似乎无法与此地的魔力同调。(硬件不支持或驱动错误)", # 硬件不支持警告提示内容
    "infobar.warning.duplicate_dependency_check.content": "自检术式已在运行中，请勿重复咏唱。", # 重复依赖检查警告提示内容
    "infobar.error.vmaf_not_number.title": "术式构成错误", # VMAF 非数字错误提示标题
    "infobar.error.vmaf_not_number.content": "视界还原度必须由数字符文构成 (如 93.0)", # VMAF 非数字错误提示内容
    "infobar.error.cache_clear_failed.title": "净化术式反噬", # 清除缓存失败错误提示标题
    "infobar.copy_warning.title": "空空如也", # “真理之眼”页面复制警告提示标题
    "infobar.copy_warning.content": "还没有解析任何物质哦...", # “真理之眼”页面复制警告提示内容

    # -------------------------------------------------------------------------
    # Core / Worker / Logger
    # -------------------------------------------------------------------------
    "common.unknown_error": "不可名状之错误", # 通用未知错误
    "dependency.ffmpeg_desc": "核心术式构筑 (FFmpeg)", # FFmpeg 描述
    "dependency.ffprobe_desc": "真理之眼组件 (FFprobe)", # FFprobe 描述
    "dependency.ab_av1_desc": "极限咏唱触媒 (ab-av1)", # ab-av1 描述
    
    # Button States
    "button.start.in_progress": "✨ 奇迹发生中...", # 开始按钮进行中状态
    "button.save.saved": "✅ 已铭刻", # 保存按钮已保存状态
    "button.reset.restored": "✅ 已回溯", # 重置按钮已恢复状态
    "button.start.missing_components": "🚫 缺少组件", # 开始按钮缺少组件状态

    # Logs
    "log.system_ready": "系统就绪... {kaomoji}", # 系统就绪日志
    "log.dependency_check_start": ">>> 正在启动环境自检术式 (Initializing environment check)...", # 开始依赖检查日志
    "log.dependency_check_finished.success": ">>> 适格者认证通过：", # 依赖检查成功日志
    "log.dependency_check_finished.fail": ">>> 警告：未侦测到有效的 AV1 硬件编码器 (QSV/NVENC/AMF)。", # 依赖检查失败日志
    "log.autoselect_encoder": ">>> 已自动切换至 {encoder} 术式。", # 自动选择编码器日志
    "log.recalibrating": ">>> 正在重新校准魔力核心可用性 (Re-calibrating)...", # 重新校准日志
    "log.list_cleared": ">>> 祭坛已清空，所有因果律已重置。 (Voided)", # 列表已清空日志
    "log.task_pause": ">>> 固有结界已冻结 (Paused)...", # 任务暂停日志
    "log.task_resume": ">>> 时空流动已恢复...", # 任务恢复日志
    "log.task_stop_request": ">>> 正在请求中止...", # 请求停止任务日志
    "log.fatal_error_component_missing": ">>> 致命错误：关键组件缺失，系统已停摆。", # 组件缺失致命错误日志
    "log.dependency.qsv_failed": ">>> Intel QSV 自检未通过: {error}", # QSV 自检失败日志
    "log.dependency.qsv_exception": ">>> Intel QSV 检测异常: {error}", # QSV 检测异常日志
    "log.dependency.nvenc_unsupported_gpu": ">>> 提示: 检测到 NVIDIA 显卡，但该型号不支持 AV1 硬件编码 (需 RTX 40 系列)。", # NVENC 不支持日志
    "log.dependency.nvenc_failed": ">>> NVENC 自检未通过: {error}", # NVENC 自检失败日志
    "log.dependency.nvenc_exception": ">>> NVENC 检测异常: {error}", # NVENC 检测异常日志
    "log.dependency.amf_failed": ">>> AMD AMF 自检未通过: {error}", # AMF 自检失败日志
    "log.dependency.amf_exception": ">>> AMD AMF 检测异常: {error}", # AMF 检测异常日志
    "log.dependency.check_exception": ">>> 环境自检异常: {error}", # 环境自检异常日志
    "log.encoder.no_files_found": "侦测不到任何魔力残留... (｡•ˇ‸ˇ•｡)", # 未发现文件日志
    "log.encoder.tasks_found": "捕捉到 {total_tasks} 个待净化异变体！( •̀ ω •́ )y", # 发现任务日志
    "log.encoder.task_start": "[{i}/{total_tasks}] 正在对 {fname} 展开固有结界...", # 任务开始日志
    "log.encoder.skip_av1": " -> 此物质已是纯净形态 (AV1)，跳过~ (Pass)", # 跳过 AV1 日志
    "log.encoder.status_skipped": "✨ 跳过", # 状态：跳过
    "log.encoder.status_duration": "耗时: {total_duration:.2f}s", # 状态：耗时
    "log.encoder.ab_av1_fallback": " -> 尝试备用方案: {desc}...", # ab-av1 备用方案日志
    "log.encoder.ab_av1_start": " -> 正在推演最强术式 (ab-av1)...", # ab-av1 开始日志
    "log.encoder.ab_av1_probing": "    -> 探测中: {probe_crf} => VMAF: {vmaf_val}", # ab-av1 探测日志
    "log.encoder.ab_av1_success_offset_corrected": " -> 术式解析完毕 ({desc}): 原始CRF {cpu_crf} + 偏移 {offset} = {raw_icq} (已修正为{reason}限制 {best_icq}) [耗时: {search_duration:.1f}s]", # ab-av1 成功(修正)日志
    "log.encoder.ab_av1_success_offset": " -> 术式解析完毕 ({desc}): 原始CRF {cpu_crf} + 偏移 {offset} => 最终参数 {best_icq} [耗时: {search_duration:.1f}s]", # ab-av1 成功(偏移)日志
    "log.encoder.ab_av1_success": " -> 术式解析完毕 (ICQ): {best_icq} [耗时: {search_duration:.1f}s] (๑•̀ㅂ•́)و✧", # ab-av1 成功日志
    "log.encoder.ab_av1_failed": " -> 解析失败，强制使用基础术式 ICQ: {best_icq} (T_T)", # ab-av1 失败日志
    "log.encoder.ab_av1_error_log_header": "    [ab-av1 错误回溯]:", # ab-av1 错误头日志
    "log.encoder.icq_corrected": " -> 修正: 硬件编码器参数限制 ({icq} -> 51)", # ICQ 修正日志
    "log.encoder.ffmpeg_exception": " -> 魔力逆流: {error} (×_×)", # FFmpeg 异常日志
    "log.encoder.success_overwrite": " -> 净化完成！旧世界已被重写 (Overwrite) (ﾉ>ω<)ﾉ [压制: {encode_duration:.1f}s | 总耗时: {total_duration:.1f}s]", # 成功(覆盖)日志
    "log.encoder.error_move_overwrite": "无法替换源文件，可能被其他程序占用。", # 移动覆盖失败日志
    "log.encoder.success_remain": " -> 净化完成！元素已保留，优化体已生成 (Remain) (ﾉ>ω<)ﾉ [压制: {encode_duration:.1f}s | 总耗时: {total_duration:.1f}s]", # 成功(保留)日志
    "log.encoder.success_save_as": " -> 净化完成！新世界已确立 (Save As) (ﾉ>ω<)ﾉ [压制: {encode_duration:.1f}s | 总耗时: {total_duration:.1f}s]", # 成功(另存为)日志
    "log.encoder.status_done": "✅ 完成", # 状态：完成
    "log.encoder.error_move": " -> 封印仪式失败: {error} (T_T)", # 移动文件失败日志
    "log.encoder.ffmpeg_crash": " -> 术式失控 (Crash)... (T_T)", # FFmpeg 崩溃日志
    "log.encoder.cooling_down": " -> 正在冷却魔术回路 (Cooling down GPU)...", # 冷却日志
    "log.encoder.all_done": ">>> 奇迹达成！(๑•̀ㅂ•́)و✧", # 全部完成日志
    "log.encoder.stopped": ">>> 契约被强制切断。", # 停止日志
    "log.encoder.fatal_error": "世界线变动率异常 (Fatal): {error}", # 致命错误日志
    "log.encoder.info_multichannel": " -> 感知到多重声场 ({channels}ch)，已保持原样。", # 多声道信息日志
    "log.encoder.info_loudnorm_enabled": " -> 声场调和 (Loudnorm): 启用 ({mode})", # 响度均衡启用日志
    "log.encoder.info_loudnorm_skipped": " -> 声场调和 (Loudnorm): 跳过 ({mode})", # 响度均衡跳过日志
}
