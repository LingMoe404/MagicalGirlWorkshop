"""MainWindow 主页布局构建器。

将 MainWindow 的纯 UI 构建方法（header / 内容区 / 左右面板卡片 / 状态栏 /
日志区 / footer / 子界面）迁移到独立模块，使主窗口的 init_ui 变成薄方法。

约束：
- 本模块**不导入** MainWindow，通过显式 window 参数访问宿主窗口，避免循环依赖。
- 只负责创建控件、布局与接线；不启动任何业务 worker，也不直接操作后台线程。
- 允许依赖 qfluentwidgets、ui.common、ui.interfaces、config 与已抽出的
  FileListManager / LogManager。

迁移方法一一对应原 MainWindow 的 _init_* 方法，仅把 self 换成 window。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    LineEdit,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SpinBox,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    TextEdit,
)

from i18n.translator import tr, translator
from ui.common import DroppableBodyLabel, DroppableListWidget
from ui.file_list_manager import FileListManager
from ui.interfaces import (
    CreditsInterface,
    MediaInfoInterface,
    ProfileInterface,
    SettingsInterface,
)
from ui.log_manager import LogManager
from utils import get_default_cache_dir


def build_home_ui(window):
    """构建主窗口首页布局与全部控件（作为 MainWindow.init_ui 的薄委托）。

    等价于原 MainWindow.init_ui：创建 main_layout 后依次构建头部、内容区、
    状态栏、日志区、footer 与子界面。所有控件以属性形式挂到 window 上。
    """
    window.main_layout = QVBoxLayout()
    window.main_layout.setContentsMargins(24, 24, 24, 24)
    window.main_layout.setSpacing(24)

    _init_header(window)
    _init_content_area(window)
    _init_status_bar(window)
    _init_log_area(window)
    _init_footer(window)
    _init_sub_interfaces(window)


def _init_header(window):
    """初始化窗口头部区域，包括标题和主题/语言切换。"""
    header_row = QHBoxLayout()
    header_row.setSpacing(16)

    title_block = QVBoxLayout()
    window.title = SubtitleLabel("炼成祭坛", window)
    window.subtitle = BodyLabel("AV1 硬件加速魔力驱动 · 绝对领域 Edition", window)
    window.subtitle.setTextColor(QColor("#999999"), QColor("#999999"))
    title_block.addWidget(window.title)
    title_block.addWidget(window.subtitle)
    title_block.setSpacing(2)
    header_row.addLayout(title_block, 1)

    window.combo_lang = ComboBox(window)
    window.combo_lang.setMinimumWidth(120)
    lang_map = translator.get_language_map()
    for lang_code, lang_name in lang_map.items():
        window.combo_lang.addItem(lang_name, userData=lang_code)

    current_lang = translator.current_lang
    for i in range(window.combo_lang.count()):
        if window.combo_lang.itemData(i) == current_lang:
            window.combo_lang.setCurrentIndex(i)
            break

    window.combo_lang.currentIndexChanged.connect(window.on_language_changed)
    header_row.addWidget(window.combo_lang, 0, Qt.AlignmentFlag.AlignCenter)

    window.combo_theme = ComboBox(window)
    window.combo_theme.addItem("世界线收束 (Auto)", FluentIcon.SYNC)
    window.combo_theme.addItem("光之加护 (Light)", FluentIcon.BRIGHTNESS)
    window.combo_theme.addItem("深渊凝视 (Dark)", FluentIcon.QUIET_HOURS)
    window.combo_theme.currentIndexChanged.connect(window.on_theme_changed)
    window.combo_theme.setMinimumWidth(140)
    header_row.addWidget(window.combo_theme, 0, Qt.AlignmentFlag.AlignCenter)

    window.main_layout.addLayout(header_row)


def _init_content_area(window):
    """初始化内容区域，分为左右两栏。"""
    content_row = QHBoxLayout()
    content_row.setSpacing(14)
    window.column_splitter = QSplitter(Qt.Orientation.Horizontal, window)
    window.column_splitter.setChildrenCollapsible(False)
    window.column_splitter.setHandleWidth(8)
    window.column_splitter.setStyleSheet(
        "QSplitter::handle { background: transparent; }"
    )

    window.left_panel = QWidget(window)
    window.left_panel.setMinimumWidth(0)
    window.left_column = QVBoxLayout(window.left_panel)
    window.left_column.setContentsMargins(0, 0, 0, 0)
    window.left_column.setSpacing(12)

    window.right_panel = QWidget(window)
    window.right_panel.setMinimumWidth(0)
    window.right_column = QVBoxLayout(window.right_panel)
    window.right_column.setContentsMargins(0, 0, 0, 0)
    window.right_column.setSpacing(12)

    _init_left_panel_content(window)
    _init_right_panel_content(window)

    window.column_splitter.addWidget(window.left_panel)
    window.column_splitter.addWidget(window.right_panel)
    window.column_splitter.setStretchFactor(0, 1)
    window.column_splitter.setStretchFactor(1, 1)
    window.column_splitter.setSizes([1, 1])

    content_row.addWidget(window.column_splitter, 1)
    window.main_layout.addLayout(content_row)


def _init_left_panel_content(window):
    """初始化左侧面板内容（缓存、设置、操作）。"""
    _init_cache_card(window)
    _init_settings_card(window)
    _init_action_card(window)


def _init_cache_card(window):
    """初始化缓存设置卡片。"""
    window.card_io = CardWidget(window)
    io_layout = QVBoxLayout(window.card_io)
    io_layout.setContentsMargins(18, 16, 18, 16)
    io_layout.setSpacing(12)

    h_cache_head = QHBoxLayout()
    window.cache_card_title = StrongBodyLabel("魔力回路缓冲 (Cache)", window.card_io)
    h_cache_head.addWidget(window.cache_card_title)
    h_cache_head.addStretch(1)
    window.btn_clear_cache = PushButton("🧹 净化残渣", window.card_io)
    window.btn_clear_cache.setCursor(Qt.CursorShape.PointingHandCursor)
    window.btn_clear_cache.clicked.connect(window.clear_cache_files)
    h_cache_head.addWidget(window.btn_clear_cache)
    io_layout.addLayout(h_cache_head)

    h2 = QHBoxLayout()
    window.line_cache = LineEdit(window.card_io)
    window.line_cache.setPlaceholderText("ab-av1 临时文件存放处...")
    window.line_cache.setFixedHeight(36)
    window.line_cache.setText(get_default_cache_dir())
    window.btn_cache = PushButton("浏览", window.card_io)
    window.btn_cache.setFixedHeight(36)
    window.btn_cache.setMinimumWidth(80)
    window.btn_cache.clicked.connect(lambda: window.browse_folder(window.line_cache))
    h2.addWidget(window.line_cache)
    h2.addWidget(window.btn_cache)

    io_layout.addLayout(h2)
    window.left_column.addWidget(window.card_io)


def _init_settings_card(window):
    """初始化编码设置卡片。"""
    window.card_settings = CardWidget(window)
    set_layout = QVBoxLayout(window.card_settings)
    set_layout.setContentsMargins(20, 20, 20, 20)
    set_layout.setSpacing(18)

    row1 = QHBoxLayout()
    row1.setSpacing(12)

    v1 = QVBoxLayout()
    window.settings_card_encoder_label = BodyLabel(
        "魔力核心 (Encoder)", window.card_settings
    )
    v1.addWidget(window.settings_card_encoder_label)
    window.combo_encoder = ComboBox(window.card_settings)
    window.combo_encoder.addItems(["Intel QSV", "NVIDIA NVENC", "AMD AMF"])
    window.combo_encoder.setMinimumWidth(140)
    window.combo_encoder.setMinimumHeight(36)
    v1.addWidget(window.combo_encoder)

    v2 = QVBoxLayout()
    window.settings_card_vmaf_label = BodyLabel(
        "视界还原度 (VMAF)", window.card_settings
    )
    v2.addWidget(window.settings_card_vmaf_label)
    window.line_vmaf = LineEdit(window.card_settings)
    window.line_vmaf.setMinimumHeight(36)
    window.line_vmaf.setMinimumWidth(60)
    v2.addWidget(window.line_vmaf)

    v3 = QVBoxLayout()
    window.settings_card_bitrate_label = BodyLabel(
        "共鸣频率 (Bitrate)", window.card_settings
    )
    v3.addWidget(window.settings_card_bitrate_label)
    window.line_audio = LineEdit(window.card_settings)
    window.line_audio.setMinimumHeight(36)
    window.line_audio.setMinimumWidth(60)
    v3.addWidget(window.line_audio)

    v4 = QVBoxLayout()
    window.settings_card_preset_label = BodyLabel(
        "咏唱速度 (Preset)", window.card_settings
    )
    v4.addWidget(window.settings_card_preset_label)
    window.combo_preset = ComboBox(window.card_settings)
    window.combo_preset.addItems(["1", "2", "3", "4", "5", "6", "7"])
    window.combo_preset.setMinimumHeight(36)
    window.combo_preset.setMinimumWidth(100)
    v4.addWidget(window.combo_preset)

    v8 = QVBoxLayout()
    window.lbl_offset = BodyLabel("灵力偏移 (Offset)", window.card_settings)
    v8.addWidget(window.lbl_offset)
    window.spin_offset = SpinBox(window.card_settings)
    window.spin_offset.setRange(-30, 0)
    window.spin_offset.setValue(-6)
    window.spin_offset.setMinimumHeight(36)
    v8.addWidget(window.spin_offset)

    row1.addLayout(v1, 3)
    row1.addLayout(v4, 2)
    set_layout.addLayout(row1)

    v9 = QVBoxLayout()
    window.lbl_color_mode = BodyLabel("色彩幻境 (Color Mode)", window.card_settings)
    v9.addWidget(window.lbl_color_mode)
    window.combo_color = ComboBox(window.card_settings)
    window.combo_color.addItem("自动保留 HDR (Auto)", userData="Auto")
    window.combo_color.addItem("色彩同调 SDR (Tone Map)", userData="ToneMap")
    window.combo_color.addItem("强制常规 SDR (Force SDR)", userData="SDR")
    window.combo_color.setMinimumHeight(36)
    v9.addWidget(window.combo_color)

    row1_b = QHBoxLayout()
    row1_b.setSpacing(12)
    row1_b.addLayout(v2, 1)
    row1_b.addLayout(v8, 1)
    row1_b.addLayout(v3, 1)
    row1_b.addLayout(v9, 1)
    set_layout.addLayout(row1_b)

    row2 = QHBoxLayout()
    row2.setSpacing(12)

    v6 = QVBoxLayout()
    h_loud = QHBoxLayout()
    window.settings_card_loudnorm_label = BodyLabel(
        "音量均一化术式 (Loudnorm)", window.card_settings
    )
    h_loud.addWidget(window.settings_card_loudnorm_label)
    h_loud.addStretch(1)
    window.combo_loudnorm = ComboBox(window.card_settings)
    window._populate_combo(window.combo_loudnorm, window.loudnorm_modes)
    window.combo_loudnorm.setMinimumWidth(200)
    h_loud.addWidget(window.combo_loudnorm)
    h_loud.addStretch(1)
    v6.addLayout(h_loud)

    window.line_loudnorm = LineEdit(window.card_settings)
    window.line_loudnorm.setMinimumHeight(36)
    v6.addWidget(window.line_loudnorm)

    v7 = QVBoxLayout()
    window.lbl_aq = BodyLabel("NVIDIA 感知增强", window.card_settings)
    v7.addWidget(window.lbl_aq)
    window.sw_nv_aq = SwitchButton("开启", window.card_settings)
    window.sw_nv_aq.setOnText("开启")
    window.sw_nv_aq.setOffText("关闭")
    window.sw_nv_aq.setChecked(True)
    v7.addWidget(window.sw_nv_aq)

    row2.addLayout(v6, 3)
    row2.addLayout(v7, 1)
    set_layout.addLayout(row2)

    # 魔导书快捷模版 (Quick Presets Row)
    h_presets = QHBoxLayout()
    h_presets.setSpacing(8)
    window.lbl_presets_title = BodyLabel(
        "魔导书快捷模版 (Templates):", window.card_settings
    )
    window.btn_preset_light = PushButton("轻量洗版术", window.card_settings)
    window.btn_preset_light.setCursor(Qt.CursorShape.PointingHandCursor)
    window.btn_preset_light.clicked.connect(window.apply_preset_light)
    window.btn_preset_balanced = PushButton("黄金均衡法则", window.card_settings)
    window.btn_preset_balanced.setCursor(Qt.CursorShape.PointingHandCursor)
    window.btn_preset_balanced.clicked.connect(window.apply_preset_balanced)
    window.btn_preset_heavenly = PushButton("圣殿至高典藏", window.card_settings)
    window.btn_preset_heavenly.setCursor(Qt.CursorShape.PointingHandCursor)
    window.btn_preset_heavenly.clicked.connect(window.apply_preset_heavenly)

    h_presets.addWidget(window.lbl_presets_title)
    h_presets.addWidget(window.btn_preset_light)
    h_presets.addWidget(window.btn_preset_balanced)
    h_presets.addWidget(window.btn_preset_heavenly)
    set_layout.addLayout(h_presets)

    h_btns = QHBoxLayout()
    h_btns.setSpacing(12)
    window.btn_save_conf = PushButton("💾 铭刻记忆 (Save)", window.card_settings)
    window.btn_save_conf.setMinimumHeight(36)
    window.btn_save_conf.clicked.connect(
        lambda: window.save_current_settings(show_tip=True)
    )

    window.btn_reset_conf = PushButton("↩️ 记忆回溯 (Reset)", window.card_settings)
    window.btn_reset_conf.setMinimumHeight(36)
    window.btn_reset_conf.clicked.connect(window.restore_defaults)

    h_btns.addWidget(window.btn_save_conf)
    h_btns.addWidget(window.btn_reset_conf)
    set_layout.addLayout(h_btns)

    window.left_column.addWidget(window.card_settings)


def _init_action_card(window):
    """初始化操作卡片（保存模式、开始/暂停/停止按钮）。"""
    window.card_action = CardWidget(window)
    act_layout = QVBoxLayout(window.card_action)
    act_layout.setContentsMargins(20, 20, 20, 20)
    act_layout.setSpacing(15)

    mode_layout = QVBoxLayout()
    mode_layout.setContentsMargins(0, 0, 0, 0)
    mode_layout.setSpacing(6)

    h_mode_combo = QHBoxLayout()
    h_mode_combo.setContentsMargins(0, 0, 0, 0)
    window.combo_save_mode = ComboBox(window.card_action)
    window._populate_combo(window.combo_save_mode, window.save_modes)
    window.combo_save_mode.setMinimumHeight(36)
    window.combo_save_mode.currentIndexChanged.connect(window.toggle_export_ui)
    h_mode_combo.addWidget(window.combo_save_mode)

    mode_layout.addLayout(h_mode_combo)

    window.export_container = QWidget(window.card_action)
    exp_layout = QHBoxLayout(window.export_container)
    exp_layout.setContentsMargins(0, 0, 0, 0)
    exp_layout.setSpacing(10)
    window.line_export = LineEdit(window.export_container)
    window.line_export.setPlaceholderText("新世界坐标...")
    window.line_export.setFixedHeight(36)
    window.btn_export = PushButton("选择", window.export_container)
    window.btn_export.setFixedHeight(36)
    window.btn_export.setMinimumWidth(80)
    window.btn_export.clicked.connect(lambda: window.browse_folder(window.line_export))
    exp_layout.addWidget(window.line_export)
    exp_layout.addWidget(window.btn_export)
    mode_layout.addWidget(window.export_container)
    act_layout.addLayout(mode_layout)

    concurrency_layout = QHBoxLayout()
    concurrency_layout.setSpacing(12)

    concurrency_mode_layout = QVBoxLayout()
    window.lbl_transcode_mode = BodyLabel(
        tr("home.action_card.concurrency.mode_label"),
        window.card_action,
    )
    concurrency_mode_layout.addWidget(window.lbl_transcode_mode)
    window.combo_transcode_mode = ComboBox(window.card_action)
    window._populate_combo(
        window.combo_transcode_mode,
        window.transcode_modes,
    )
    window.combo_transcode_mode.setMinimumHeight(36)
    window.combo_transcode_mode.currentIndexChanged.connect(
        window.toggle_transcode_concurrency_ui
    )
    concurrency_mode_layout.addWidget(window.combo_transcode_mode)

    concurrency_count_layout = QVBoxLayout()
    window.lbl_transcode_count = BodyLabel(
        tr("home.action_card.concurrency.count_label"),
        window.card_action,
    )
    concurrency_count_layout.addWidget(window.lbl_transcode_count)
    window.spin_transcode_concurrency = SpinBox(window.card_action)
    window.spin_transcode_concurrency.setRange(1, 4)
    window.spin_transcode_concurrency.setValue(2)
    window.spin_transcode_concurrency.setMinimumHeight(36)
    concurrency_count_layout.addWidget(window.spin_transcode_concurrency)

    concurrency_layout.addLayout(concurrency_mode_layout, 2)
    concurrency_layout.addLayout(concurrency_count_layout, 1)
    act_layout.addLayout(concurrency_layout)

    window.lbl_concurrency_status = BodyLabel(
        tr("home.action_card.concurrency.idle"),
        window.card_action,
    )
    window.lbl_concurrency_status.setWordWrap(True)
    act_layout.addWidget(window.lbl_concurrency_status)
    act_layout.addStretch(1)
    window.toggle_export_ui()
    window.toggle_transcode_concurrency_ui()

    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(10)
    window.btn_start = PrimaryPushButton("✨ 缔结契约 (Start)", window.card_action)
    window.btn_start.clicked.connect(window.start_task)
    window.btn_start.setMinimumHeight(36)
    window.btn_start.setMaximumHeight(36)

    window.btn_pause = PushButton("⏳ 时空冻结 (Pause)", window.card_action)
    window.btn_pause.clicked.connect(window.pause_task)
    window.btn_pause.setEnabled(False)
    window.btn_pause.setMinimumHeight(36)
    window.btn_pause.setMaximumHeight(36)
    window.btn_pause.setStyleSheet(
        "PushButton { border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 6px; }"
    )

    window.btn_stop = PushButton(" 契约破弃 (Stop)", window.card_action)
    window.btn_stop.clicked.connect(window.stop_task)
    window.btn_stop.setEnabled(False)
    window.btn_stop.setMinimumHeight(36)
    window.btn_stop.setMaximumHeight(36)
    window.btn_stop.setStyleSheet(
        "PushButton { color: #D93652; font-weight: bold; border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 6px; } PushButton:disabled { color: #CCCCCC; border: 1px solid rgba(128, 128, 128, 0.1); }"
    )

    btn_layout.addWidget(window.btn_start)
    btn_layout.addWidget(window.btn_pause)
    btn_layout.addWidget(window.btn_stop)
    act_layout.addLayout(btn_layout)

    window.left_column.addWidget(window.card_action)


def _init_right_panel_content(window):
    """初始化右侧面板内容（源文件、文件列表）。"""
    _init_source_card(window)
    _init_file_list_card(window)
    window.sync_source_cache_card_height()
    window.sync_settings_selected_card_height()
    window.right_column.addStretch(1)


def _init_source_card(window):
    """初始化源文件选择卡片。"""
    window.card_source = CardWidget(window)
    source_layout = QVBoxLayout(window.card_source)
    source_layout.setContentsMargins(18, 16, 18, 16)
    source_layout.setSpacing(10)
    window.source_card_title = StrongBodyLabel("素材次元 (Source)", window.card_source)
    source_layout.addWidget(window.source_card_title)

    source_btns = QHBoxLayout()
    source_btns.setSpacing(10)
    window.btn_src = PushButton("以文件夹之名", window.card_source)
    window.btn_src.setMinimumHeight(36)
    window.btn_src.clicked.connect(window.choose_source_folder)
    window.btn_files = PushButton("以文件之名", window.card_source)
    window.btn_files.setMinimumHeight(36)
    window.btn_files.clicked.connect(window.browse_files)
    source_btns.addWidget(window.btn_src)
    source_btns.addWidget(window.btn_files)
    source_layout.addLayout(source_btns)

    window.right_column.addWidget(window.card_source)


def _init_file_list_card(window):
    """初始化文件列表卡片。"""
    window.card_selected_files = CardWidget(window)
    selected_layout = QVBoxLayout(window.card_selected_files)
    selected_layout.setContentsMargins(18, 16, 18, 16)
    selected_layout.setSpacing(8)

    selected_header = QHBoxLayout()
    window.file_list_card_title = StrongBodyLabel(
        "次元空间 (List)", window.card_selected_files
    )
    selected_header.addWidget(window.file_list_card_title)
    selected_header.addStretch(1)

    window.btn_clear_list = PushButton(
        FluentIcon.DELETE, "归于虚无", window.card_selected_files
    )
    window.btn_clear_list.setMinimumWidth(120)
    window.btn_clear_list.setCursor(Qt.CursorShape.PointingHandCursor)
    window.btn_clear_list.clicked.connect(window.clear_all_selected_files)
    selected_header.addWidget(window.btn_clear_list)

    window.lbl_selected_count_right = BodyLabel("0", window.card_selected_files)
    window.lbl_selected_count_right.setStyleSheet("""
        color: white; 
        background-color: #FB7299; 
        border-radius: 10px; 
        padding: 2px 10px; 
        font-weight: bold; 
        margin-left: 8px; 
        font-size: 12px;
    """)
    selected_header.addWidget(window.lbl_selected_count_right)
    selected_layout.addLayout(selected_header)

    window.lbl_selected_placeholder = DroppableBodyLabel(
        "把元素拖拽到此处", window.card_selected_files
    )
    window.lbl_selected_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.lbl_selected_placeholder.setTextColor(QColor("#FB7299"), QColor("#FB7299"))
    window.lbl_selected_placeholder.setMinimumHeight(330)
    window.lbl_selected_placeholder.filesDropped.connect(window.handle_dropped_paths)
    window.lbl_selected_placeholder.dragActiveChanged.connect(
        window.on_selected_zone_drag_active_changed
    )
    selected_layout.addWidget(window.lbl_selected_placeholder)

    window.list_selected_files = DroppableListWidget(window.card_selected_files)
    window.list_selected_files.setMinimumHeight(330)
    window.list_selected_files.setSpacing(0)
    window.list_selected_files.setSelectionMode(
        QAbstractItemView.SelectionMode.NoSelection
    )
    window.list_selected_files.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    window.list_selected_files.setUniformItemSizes(True)
    window.list_selected_files.setVerticalScrollMode(
        QAbstractItemView.ScrollMode.ScrollPerPixel
    )
    window.list_selected_files.setContentsMargins(0, 0, 0, 0)
    window.list_selected_files.setViewportMargins(0, 0, 0, 0)
    if hasattr(window.list_selected_files, "setSelectionRectVisible"):
        window.list_selected_files.setSelectionRectVisible(False)
    if hasattr(window.list_selected_files, "setSelectRightClickedRow"):
        window.list_selected_files.setSelectRightClickedRow(False)
    window.list_selected_files.pressed.connect(
        lambda _: window.clear_selected_list_visual_state()
    )
    window.list_selected_files.clicked.connect(
        lambda _: window.clear_selected_list_visual_state()
    )
    window.list_selected_files.filesDropped.connect(window.handle_dropped_paths)
    window.list_selected_files.dragActiveChanged.connect(
        window.on_selected_zone_drag_active_changed
    )
    window.list_selected_files.itemDoubleClicked.connect(window.open_file_location)
    selected_layout.addWidget(window.list_selected_files)

    # 实例化 FileListManager：显式注入列表控件与回调。
    # thread_limit_getter 读取当前线程限制并转为 int，缺失/非法回退 4。
    # status_text_callback 恢复旧的 ab-av1/探测 分支：探测阶段改写 lbl_current，
    # 普通编码恢复翻译后的当前标签。
    # remove_callback 在文件被移除时通知宿主。
    window.file_list_manager = FileListManager(
        list_widget=window.list_selected_files,
        placeholder=window.lbl_selected_placeholder,
        count_label=window.lbl_selected_count_right,
        thread_limit_getter=window._get_thread_limit,
        status_text_callback=window._on_file_stats_text,
        remove_callback=window._on_file_removed,
    )
    window.file_list_manager.update_selected_count()

    window.right_column.addWidget(window.card_selected_files)


def _init_status_bar(window):
    """初始化状态栏（进度条）。"""
    status_layout = QHBoxLayout()
    status_layout.setContentsMargins(0, 0, 0, 0)

    window.lbl_current = BodyLabel("当前 (Current):", window)
    window.pbar_current = ProgressBar(window)
    window.lbl_total = BodyLabel("总体 (Total):", window)
    window.pbar_total = ProgressBar(window)

    status_layout.addWidget(window.lbl_current)
    status_layout.addWidget(window.pbar_current)
    status_layout.addSpacing(20)
    status_layout.addWidget(window.lbl_total)
    status_layout.addWidget(window.pbar_total)

    window.main_layout.addLayout(status_layout)


def _init_log_area(window):
    """初始化日志显示区域。"""
    window.text_log = TextEdit(window)
    window.text_log.setReadOnly(True)
    window.text_log.setFixedHeight(160)
    window.text_log.setStyleSheet("""
        TextEdit {
            background-color: rgba(0, 0, 0, 0.05); 
            border: 1px solid rgba(128, 128, 128, 0.1);
            font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace;
        }
    """)
    window.main_layout.addWidget(window.text_log)

    # LogManager：在 text_log 创建后 attach，flush 作为主线程定时器槽
    window.log_manager = LogManager(text_log=window.text_log)


def _init_footer(window):
    """初始化窗口底部区域（版权信息）。"""
    window.footer = BodyLabel(
        "Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | AI-assisted with Codex, GPT, Antigravity & Gemini",
        window,
    )
    window.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.footer.setTextColor(QColor("#AAAAAA"), QColor("#AAAAAA"))
    window.footer.setOpenExternalLinks(True)
    window.main_layout.addWidget(window.footer)


def _init_sub_interfaces(window):
    """初始化并添加所有子界面到导航面板。"""
    window.home_interface = QWidget()
    window.home_interface.setObjectName("homeInterface")
    window.home_interface.setLayout(window.main_layout)
    window.addSubInterface(window.home_interface, FluentIcon.VIDEO, tr("home.title"))

    window.info_interface = MediaInfoInterface(window)
    window.addSubInterface(window.info_interface, FluentIcon.INFO, tr("info.title"))

    window.profile_interface = ProfileInterface(window)
    window.addSubInterface(
        window.profile_interface, FluentIcon.PEOPLE, tr("profile.title")
    )

    window.credits_interface = CreditsInterface(window)
    window.addSubInterface(
        window.credits_interface, FluentIcon.HEART, tr("credits.title")
    )

    window.settings_interface = SettingsInterface(window)
    window.addSubInterface(
        window.settings_interface, FluentIcon.SETTING, tr("settings.title")
    )
