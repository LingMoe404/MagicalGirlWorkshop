import os
import time
import random
import subprocess
import configparser
import copy
from collections import OrderedDict

from PySide6.QtCore import Qt, QTimer, QMutex, QSize
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QFileDialog, QListWidgetItem, QAbstractItemView, QSplitter, 
                               QGraphicsDropShadowEffect, QStackedWidget)
from PySide6.QtGui import (QIcon, QColor, QGuiApplication, QPixmap, QPainter, QPainterPath)

# 引入 Fluent Widgets (Win11 风格组件)
from qfluentwidgets import (FluentWindow, SubtitleLabel, StrongBodyLabel, BodyLabel, 
                            LineEdit, PrimaryPushButton, PushButton, ProgressBar, 
                            TextEdit, SwitchButton, ComboBox, CardWidget, InfoBar, 
                            InfoBarPosition, setTheme, Theme, FluentIcon, setThemeColor, isDarkTheme, MessageDialog, SpinBox,
                            IconWidget, MessageBoxBase)

from config import (
    APP_TITLE, ENC_QSV, ENC_NVENC, ENC_AMF,
    MAX_DURATION_WORKERS, MAX_THUMBNAIL_WORKERS, MAX_THUMBNAIL_CACHE_SIZE,
    LOG_UPDATE_INTERVAL, LOG_MAX_BLOCKS, DEPENDENCY_CHECK_DELAY,
    MIN_WINDOW_SIZE, NAV_EXPAND_WIDTH, THEMES,
    VIDEO_EXTS, SAVE_MODE_SAVE_AS, SAVE_MODE_OVERWRITE, SAVE_MODE_REMAIN,
    LOUDNORM_MODE_ALWAYS, LOUDNORM_MODE_DISABLE, LOUDNORM_MODE_AUTO,
    DEFAULT_SETTINGS, ENCODER_CONFIGS
)
from utils import (
    resource_path, get_default_cache_dir, get_config_path
)
from workers import DurationWorker, ThumbnailWorker, DependencyWorker, EncoderWorker
from ui.interfaces import MediaInfoInterface, ProfileInterface, CreditsInterface
from ui.common import ClickableBodyLabel, DroppableBodyLabel, DroppableListWidget

# --- 初次运行欢迎向导 ---
class WelcomeWizard(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("欢迎来到魔法少女工坊 ✨", self)
        self.view = QStackedWidget(self)
        
        # 定义向导页面数据
        self.pages = [
            {
                "title": "初次见面，适格者！",
                "content": "这是一个专为 NAS 仓鼠党打造的 AV1 硬件转码工具。\n\n它能利用 Intel/NVIDIA/AMD 显卡的算力，将视频体积缩小 30%-50%，同时保持肉眼无损的画质。\n\n接下来，让我为您简单介绍几个关键设置..."
            },
            {
                "title": "1. 魔力核心 (Encoder)",
                "content": "这是转码引擎的选择。\n\n• Intel QSV: 适合 Arc 独显 / Ultra 核显。\n• NVIDIA NVENC: 适合 RTX 40 系。\n• AMD AMF: 适合 RX 7000 系 / RDNA 3 架构核显。\n\n程序启动时会自动检测您的硬件，通常无需手动更改。"
            },
            {
                "title": "2. 视界还原度 (VMAF)",
                "content": "这是决定画质的核心指标 (0-100)。\n\n• 95+: 极高画质，适合收藏。\n• 93 (默认): 黄金平衡点，肉眼无损，体积缩减显著。\n• 90: 高压缩比，适合移动端观看。\n\n建议保持默认 93.0。"
            },
            {
                "title": "3. 咏唱速度 (Preset)",
                "content": "平衡编码速度与压缩效率 (1-7)。\n\n• 数字越小 (1-3): 速度慢，体积更小，画质更好。\n• 数字越大 (5-7): 速度快，体积稍大。\n• 默认 4: 均衡之选。\n\n挂机洗版建议设为 3 或 4。"
            },
            {
                "title": "4. 灵力偏移 (Offset)",
                "content": "针对硬件编码器的微调参数。\n\n由于硬件编码器效率不同，我们需要对 CPU 探测出的参数进行修正。\n• AMD 默认 -6\n• NVIDIA 默认 -4\n• Intel 默认 -2\n\n这能确保最终画质接近您的 VMAF 预期。"
            }
        ]
        
        self.init_pages()
        
        # 调整布局和尺寸
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.view)
        self.widget.setFixedSize(480, 360)
        
        # 配置按钮
        self.yesButton.setText("下一步")
        self.cancelButton.setText("跳过")
        
        # 重新绑定信号 (接管默认的 accept/reject 行为)
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self.next_page)
        self.cancelButton.clicked.disconnect()
        self.cancelButton.clicked.connect(self.reject)
        
        self.current_idx = 0
        self.view.setCurrentIndex(0)

    def init_pages(self):
        for page_data in self.pages:
            page = QWidget()
            vbox = QVBoxLayout(page)
            vbox.setContentsMargins(0, 10, 0, 0)
            vbox.setSpacing(10)
            
            lbl_title = StrongBodyLabel(page_data["title"], page)
            lbl_content = BodyLabel(page_data["content"], page)
            lbl_content.setWordWrap(True)
            text_color = "#666666" if not isDarkTheme() else "#CCCCCC"
            lbl_content.setStyleSheet(f"color: {text_color}; font-size: 13px; line-height: 1.5;")
            
            vbox.addWidget(lbl_title)
            vbox.addWidget(lbl_content)
            vbox.addStretch(1)
            self.view.addWidget(page)

    def next_page(self):
        if self.current_idx < len(self.pages) - 1:
            self.current_idx += 1
            self.view.setCurrentIndex(self.current_idx)
            if self.current_idx == len(self.pages) - 1:
                self.yesButton.setText("开始炼成")
        else:
            self.accept()

# --- 主窗口 (Win11 风格) ---
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(MIN_WINDOW_SIZE)
        self._base_min_size = MIN_WINDOW_SIZE
        self._centered_once = False
        
        # [Fix] 缩减侧边栏展开宽度，避免留白过多，视觉更紧凑
        self.navigationInterface.setExpandWidth(NAV_EXPAND_WIDTH)
        
        # 启用 Mica 效果 (Win11 特有半透明背景)
        self.windowEffect.setMicaEffect(self.winId())
        setThemeColor('#FB7299') # Bilibili Pink / 魔法少女粉

        # 设置窗口图标 (任务栏和左上角)
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            icon = QIcon()
            # 使用 addFile 加载多分辨率图标，配合 AppUserModelID 解决模糊问题
            icon.addFile(icon_path)
            self.setWindowIcon(icon)

        # 核心变量
        self.worker = None
        self.selected_files = []
        self._drag_over_source_zone = False
        self._auto_save_blocked = False
        self.dep_worker = None
        self.active_dur_workers = {}   # 正在运行的时长线程
        self.pending_dur_tasks = []    # 等待中的时长任务
        self.active_thumb_workers = {} # 正在运行的缩略图线程
        self.pending_thumb_tasks = []  # 等待中的缩略图任务
        self.cached_durations = {} # path -> (str, float)
        self.cached_thumbnails = OrderedDict() # [Opt] 使用 OrderedDict 实现 LRU 缓存
        self.MAX_THUMBNAIL_CACHE = MAX_THUMBNAIL_CACHE_SIZE
        self.path_to_item = {}     # [Add] 路径到列表项的映射，实现增量更新
        self.file_metadata = {}    # [Add] 存储媒体元数据
        
        # [Add] 日志缓冲队列，用于优化高频日志性能
        self.log_mutex = QMutex()
        self.log_queue = []
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.process_log_queue)
        self.log_timer.start(LOG_UPDATE_INTERVAL) # 提高刷新频率至 50ms，让反馈更灵敏
        
        # [Add] 编码器配置管理
        self.last_encoder_name = "Intel QSV"
        self.encoder_settings = copy.deepcopy(ENCODER_CONFIGS)
        
        # 初始化 UI
        self.init_ui()
        self.apply_min_window_size()
        self.load_settings_to_ui()
        self.combo_encoder.currentIndexChanged.connect(self.on_encoder_changed)
        self.bind_auto_save_signals()

        # 连接所有页面的主题切换信号
        for interface in [self.info_interface, self.profile_interface, self.credits_interface]:
            interface.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
        
        # 欢迎语
        kaomojis = ["(｡•̀ᴗ-)✧", "(*/ω＼*)", "ヽ(✿ﾟ▽ﾟ)ノ", "(๑•̀ㅂ•́)و✧"]
        self.log(f"系统就绪... {random.choice(kaomojis)}", "info")
        
        # 启动 0.5 秒后检查结界完整性 (依赖检查)
        QTimer.singleShot(DEPENDENCY_CHECK_DELAY, self.check_dependencies)

    def apply_min_window_size(self):
        """根据当前布局自动计算最小可用尺寸，避免控件挤压错位。"""
        hint = self.minimumSizeHint()
        min_w = max(self._base_min_size.width(), hint.width())
        min_h = max(self._base_min_size.height(), hint.height())
        self.setMinimumSize(min_w, min_h)
        if self.width() < min_w or self.height() < min_h:
            self.resize(max(self.width(), min_w), max(self.height(), min_h))

    def init_ui(self):
        # 主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(24)

        self._init_header()
        self._init_content_area()
        self._init_status_bar()
        self._init_log_area()
        self._init_footer()
        self._init_sub_interfaces()

    def _init_header(self):
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_block = QVBoxLayout()
        title = SubtitleLabel("炼成祭坛", self)
        subtitle = BodyLabel("AV1 硬件加速魔力驱动 · 绝对领域 Edition", self)
        subtitle.setTextColor(QColor("#999999"), QColor("#999999")) # 灰色副标题
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.setSpacing(2)
        header_row.addLayout(title_block, 1)

        # 主题切换
        self.combo_theme = ComboBox(self)
        self.combo_theme.addItem("世界线收束 (Auto)", FluentIcon.SYNC)
        self.combo_theme.addItem("光之加护 (Light)", FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem("深渊凝视 (Dark)", FluentIcon.QUIET_HOURS)
        self.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
        self.combo_theme.setFixedWidth(160)
        header_row.addWidget(self.combo_theme, 0, Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addLayout(header_row)

    def _init_content_area(self):
        content_row = QHBoxLayout()
        content_row.setSpacing(14)
        self.column_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.column_splitter.setChildrenCollapsible(False)
        self.column_splitter.setHandleWidth(8)
        self.column_splitter.setStyleSheet("QSplitter::handle { background: transparent; }")

        self.left_panel = QWidget(self)
        self.left_panel.setMinimumWidth(0)
        self.left_column = QVBoxLayout(self.left_panel)
        self.left_column.setContentsMargins(0, 0, 0, 0)
        self.left_column.setSpacing(12)

        self.right_panel = QWidget(self)
        self.right_panel.setMinimumWidth(0)
        self.right_column = QVBoxLayout(self.right_panel)
        self.right_column.setContentsMargins(0, 0, 0, 0)
        self.right_column.setSpacing(12)

        self._init_left_panel_content()
        self._init_right_panel_content()

        self.column_splitter.addWidget(self.left_panel)
        self.column_splitter.addWidget(self.right_panel)
        self.column_splitter.setStretchFactor(0, 1)
        self.column_splitter.setStretchFactor(1, 1)
        self.column_splitter.setSizes([1, 1])

        content_row.addWidget(self.column_splitter, 1)
        self.main_layout.addLayout(content_row)

    def _init_left_panel_content(self):
        self._init_cache_card()
        self._init_settings_card()
        self._init_action_card()

    def _init_cache_card(self):
        self.card_io = CardWidget(self)
        io_layout = QVBoxLayout(self.card_io)
        io_layout.setContentsMargins(18, 16, 18, 16)
        io_layout.setSpacing(12)

        # 缓存卡片内容
        h_cache_head = QHBoxLayout()
        h_cache_head.addWidget(StrongBodyLabel("魔力回路缓冲 (Cache)", self.card_io))
        h_cache_head.addStretch(1)
        self.btn_clear_cache = PushButton("🧹 净化残渣", self.card_io)
        self.btn_clear_cache.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_cache.clicked.connect(self.clear_cache_files)
        h_cache_head.addWidget(self.btn_clear_cache)
        io_layout.addLayout(h_cache_head)

        h2 = QHBoxLayout()
        self.line_cache = LineEdit(self.card_io)
        self.line_cache.setPlaceholderText("ab-av1 临时文件存放处...")
        self.line_cache.setFixedHeight(36)
        self.line_cache.setText(get_default_cache_dir())
        self.btn_cache = PushButton("浏览", self.card_io)
        self.btn_cache.setFixedHeight(36)
        self.btn_cache.setFixedWidth(84)
        self.btn_cache.clicked.connect(lambda: self.browse_folder(self.line_cache))
        h2.addWidget(self.line_cache)
        h2.addWidget(self.btn_cache)
        
        io_layout.addLayout(h2)
        self.left_column.addWidget(self.card_io)

    def _init_settings_card(self):
        self.card_settings = CardWidget(self)
        set_layout = QVBoxLayout(self.card_settings)
        set_layout.setContentsMargins(20, 20, 20, 20)
        set_layout.setSpacing(18)
        
        # 第一行参数
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        v1 = QVBoxLayout()
        v1.addWidget(StrongBodyLabel("魔力核心 (Encoder)", self.card_settings))
        self.combo_encoder = ComboBox(self.card_settings)
        self.combo_encoder.addItems(["Intel QSV", "NVIDIA NVENC", "AMD AMF"])
        self.combo_encoder.setMinimumWidth(140)
        self.combo_encoder.setMinimumHeight(36)
        v1.addWidget(self.combo_encoder)

        v2 = QVBoxLayout()
        v2.addWidget(StrongBodyLabel("视界还原度 (VMAF)", self.card_settings))
        self.line_vmaf = LineEdit(self.card_settings)
        self.line_vmaf.setMinimumHeight(36)
        self.line_vmaf.setMinimumWidth(60)
        v2.addWidget(self.line_vmaf)
        
        v3 = QVBoxLayout()
        v3.addWidget(StrongBodyLabel("共鸣频率 (Bitrate)", self.card_settings))
        self.line_audio = LineEdit(self.card_settings)
        self.line_audio.setMinimumHeight(36)
        self.line_audio.setMinimumWidth(60)
        v3.addWidget(self.line_audio)

        v4 = QVBoxLayout()
        v4.addWidget(StrongBodyLabel("咏唱速度 (Preset)", self.card_settings))
        self.combo_preset = ComboBox(self.card_settings)
        self.combo_preset.addItems(["1", "2", "3", "4", "5", "6", "7"])
        self.combo_preset.setMinimumHeight(36)
        self.combo_preset.setMinimumWidth(100)
        v4.addWidget(self.combo_preset)

        v8 = QVBoxLayout()
        self.lbl_offset = StrongBodyLabel("灵力偏移 (Offset)", self.card_settings)
        v8.addWidget(self.lbl_offset)
        self.spin_offset = SpinBox(self.card_settings)
        self.spin_offset.setRange(-30, 30)
        self.spin_offset.setRange(-30, 0)
        self.spin_offset.setValue(-6)
        self.spin_offset.setMinimumHeight(36)
        v8.addWidget(self.spin_offset)

        # 第一行参数 (Encoder, Preset) - 核心配置
        row1.addLayout(v1, 3) 
        row1.addLayout(v4, 2)
        set_layout.addLayout(row1)

        # 第二行参数 (VMAF, Offset, Bitrate) - 质量控制
        row1_b = QHBoxLayout()
        row1_b.setSpacing(12)
        row1_b.addLayout(v2, 1)
        row1_b.addLayout(v8, 1)
        row1_b.addLayout(v3, 1)
        set_layout.addLayout(row1_b)

        # 第三行参数 (Loudnorm, AQ)
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        v6 = QVBoxLayout()
        h_loud = QHBoxLayout()
        h_loud.addWidget(StrongBodyLabel("音量均一化术式 (Loudnorm)", self.card_settings))
        h_loud.addStretch(1)
        self.combo_loudnorm = ComboBox(self.card_settings)
        self.combo_loudnorm.addItems([LOUDNORM_MODE_AUTO, LOUDNORM_MODE_ALWAYS, LOUDNORM_MODE_DISABLE])
        self.combo_loudnorm.setFixedWidth(240)
        h_loud.addWidget(self.combo_loudnorm)
        h_loud.addStretch(1)
        v6.addLayout(h_loud)
        
        self.line_loudnorm = LineEdit(self.card_settings)
        self.line_loudnorm.setMinimumHeight(36)
        v6.addWidget(self.line_loudnorm)
        
        v7 = QVBoxLayout()
        self.lbl_aq = StrongBodyLabel("NVIDIA 感知增强", self.card_settings)
        v7.addWidget(self.lbl_aq)
        self.sw_nv_aq = SwitchButton("开启", self.card_settings)
        self.sw_nv_aq.setOnText("开启")
        self.sw_nv_aq.setOffText("关闭")
        self.sw_nv_aq.setChecked(True)
        v7.addWidget(self.sw_nv_aq)

        row2.addLayout(v6, 3)
        row2.addLayout(v7, 1)
        set_layout.addLayout(row2)

        # 保存/恢复按钮
        h_btns = QHBoxLayout()
        h_btns.setSpacing(12)
        self.btn_save_conf = PushButton("💾 铭刻记忆 (Save)", self.card_settings)
        self.btn_save_conf.setMinimumHeight(36)
        self.btn_save_conf.clicked.connect(lambda: self.save_current_settings(show_tip=True))
        
        self.btn_reset_conf = PushButton("↩️ 记忆回溯 (Reset)", self.card_settings)
        self.btn_reset_conf.setMinimumHeight(36)
        self.btn_reset_conf.clicked.connect(self.restore_defaults)
        
        h_btns.addWidget(self.btn_save_conf)
        h_btns.addWidget(self.btn_reset_conf)
        set_layout.addLayout(h_btns)

        self.left_column.addWidget(self.card_settings)

    def _init_action_card(self):
        self.card_action = CardWidget(self)
        act_layout = QVBoxLayout(self.card_action)
        act_layout.setContentsMargins(20, 20, 20, 20)
        act_layout.setSpacing(15)

        # 保存模式 + 导出路径（与操作按钮同卡片）
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)
        
        h_mode_combo = QHBoxLayout()
        h_mode_combo.setContentsMargins(0, 0, 0, 0)
        self.combo_save_mode = ComboBox(self.card_action)
        self.combo_save_mode.addItems([SAVE_MODE_SAVE_AS, SAVE_MODE_OVERWRITE, SAVE_MODE_REMAIN])
        self.combo_save_mode.setMinimumHeight(36)
        self.combo_save_mode.currentIndexChanged.connect(self.toggle_export_ui)
        h_mode_combo.addWidget(self.combo_save_mode)
        
        mode_layout.addLayout(h_mode_combo)

        self.export_container = QWidget(self.card_action)
        exp_layout = QHBoxLayout(self.export_container)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(10)
        self.line_export = LineEdit(self.export_container)
        self.line_export.setPlaceholderText("新世界坐标...")
        self.line_export.setFixedHeight(36)
        self.btn_export = PushButton("选择", self.export_container)
        self.btn_export.setFixedHeight(36)
        self.btn_export.setFixedWidth(84)
        self.btn_export.clicked.connect(lambda: self.browse_folder(self.line_export))
        exp_layout.addWidget(self.line_export)
        exp_layout.addWidget(self.btn_export)
        mode_layout.addWidget(self.export_container)
        act_layout.addLayout(mode_layout)
        act_layout.addStretch(1)
        self.toggle_export_ui() # 初始化状态

        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_start = PrimaryPushButton("✨ 缔结契约 (Start)", self.card_action)
        self.btn_start.clicked.connect(self.start_task)
        self.btn_start.setMinimumHeight(36)
        self.btn_start.setMaximumHeight(36)
        
        self.btn_pause = PushButton("⏳ 时空冻结 (Pause)", self.card_action)
        self.btn_pause.clicked.connect(self.pause_task)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setMinimumHeight(36)
        self.btn_pause.setMaximumHeight(36)
        self.btn_pause.setStyleSheet("PushButton { border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 6px; }")
        
        self.btn_stop = PushButton(" 契约破弃 (Stop)", self.card_action)
        self.btn_stop.clicked.connect(self.stop_task)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(36)
        self.btn_stop.setMaximumHeight(36)
        # 设置停止按钮为红色样式 (自定义QSS)
        self.btn_stop.setStyleSheet("PushButton { color: #D93652; font-weight: bold; border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 6px; } PushButton:disabled { color: #CCCCCC; border: 1px solid rgba(128, 128, 128, 0.1); }")

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        act_layout.addLayout(btn_layout)

        self.left_column.addWidget(self.card_action)

    def _init_right_panel_content(self):
        self._init_source_card()
        self._init_file_list_card()
        self.sync_source_cache_card_height()
        self.sync_settings_selected_card_height()
        self.right_column.addStretch(1)

    def _init_source_card(self):
        self.card_source = CardWidget(self)
        source_layout = QVBoxLayout(self.card_source)
        source_layout.setContentsMargins(18, 16, 18, 16)
        source_layout.setSpacing(10)
        source_layout.addWidget(StrongBodyLabel("素材次元 (Source)", self.card_source))

        source_btns = QHBoxLayout()
        source_btns.setSpacing(10)
        self.btn_src = PushButton("以文件夹之名", self.card_source)
        self.btn_src.setMinimumHeight(36)
        self.btn_src.clicked.connect(self.choose_source_folder)
        self.btn_files = PushButton("以文件之名", self.card_source)
        self.btn_files.setMinimumHeight(36)
        self.btn_files.clicked.connect(self.browse_files)
        source_btns.addWidget(self.btn_src)
        source_btns.addWidget(self.btn_files)
        source_layout.addLayout(source_btns)

        self.right_column.addWidget(self.card_source)

    def _init_file_list_card(self):
        self.card_selected_files = CardWidget(self)
        selected_layout = QVBoxLayout(self.card_selected_files)
        selected_layout.setContentsMargins(18, 16, 18, 16)
        selected_layout.setSpacing(8)

        selected_header = QHBoxLayout()
        selected_header.addWidget(StrongBodyLabel("次元空间 (List)", self.card_selected_files))
        selected_header.addStretch(1)
        
        self.btn_clear_list = PushButton(FluentIcon.DELETE, "归于虚无", self.card_selected_files)
        self.btn_clear_list.setFixedWidth(120)
        self.btn_clear_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_list.clicked.connect(self.clear_all_selected_files)
        selected_header.addWidget(self.btn_clear_list)

        self.lbl_selected_count_right = BodyLabel("0", self.card_selected_files)
        self.lbl_selected_count_right.setStyleSheet("""
            color: white; 
            background-color: #FB7299; 
            border-radius: 10px; 
            padding: 2px 10px; 
            font-weight: bold; 
            margin-left: 8px; 
            font-size: 12px;
        """)
        selected_header.addWidget(self.lbl_selected_count_right)
        selected_layout.addLayout(selected_header)

        self.lbl_selected_placeholder = DroppableBodyLabel("把元素拖拽到此处", self.card_selected_files)
        self.lbl_selected_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_selected_placeholder.setTextColor(QColor("#FB7299"), QColor("#FB7299"))
        self.lbl_selected_placeholder.setMinimumHeight(330)
        self.lbl_selected_placeholder.filesDropped.connect(self.handle_dropped_paths)
        self.lbl_selected_placeholder.dragActiveChanged.connect(self.on_selected_zone_drag_active_changed)
        selected_layout.addWidget(self.lbl_selected_placeholder)

        self.list_selected_files = DroppableListWidget(self.card_selected_files)
        self.list_selected_files.setMinimumHeight(330)
        self.list_selected_files.setSpacing(0)
        self.list_selected_files.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_selected_files.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_selected_files.setUniformItemSizes(True)
        self.list_selected_files.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_selected_files.setContentsMargins(0, 0, 0, 0)
        self.list_selected_files.setViewportMargins(0, 0, 0, 0)
        if hasattr(self.list_selected_files, "setSelectionRectVisible"):
            self.list_selected_files.setSelectionRectVisible(False)
        if hasattr(self.list_selected_files, "setSelectRightClickedRow"):
            self.list_selected_files.setSelectRightClickedRow(False)
        self.list_selected_files.pressed.connect(lambda _: self.clear_selected_list_visual_state())
        self.list_selected_files.clicked.connect(lambda _: self.clear_selected_list_visual_state())
        self.list_selected_files.filesDropped.connect(self.handle_dropped_paths)
        self.list_selected_files.dragActiveChanged.connect(self.on_selected_zone_drag_active_changed)
        self.list_selected_files.itemDoubleClicked.connect(self.open_file_location)
        selected_layout.addWidget(self.list_selected_files)
        self.update_selected_count()

        self.right_column.addWidget(self.card_selected_files)

    def _init_status_bar(self):
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_current = BodyLabel("当前 (Current):", self)
        self.pbar_current = ProgressBar(self)
        self.lbl_total = BodyLabel("总体 (Total):", self)
        self.pbar_total = ProgressBar(self)
        
        status_layout.addWidget(self.lbl_current)
        status_layout.addWidget(self.pbar_current)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.lbl_total)
        status_layout.addWidget(self.pbar_total)
        
        self.main_layout.addLayout(status_layout)

    def _init_log_area(self):
        self.text_log = TextEdit(self)
        self.text_log.setReadOnly(True)
        self.text_log.setFixedHeight(160)
        self.text_log.setStyleSheet("""
            TextEdit {
                background-color: rgba(0, 0, 0, 0.05); 
                border: 1px solid rgba(128, 128, 128, 0.1);
                font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace;
            }
        """)
        self.main_layout.addWidget(self.text_log)

    def _init_footer(self):
        footer = BodyLabel("Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", self)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setTextColor(QColor("#AAAAAA"), QColor("#AAAAAA"))
        footer.setOpenExternalLinks(True)
        self.main_layout.addWidget(footer)

    def _init_sub_interfaces(self):
        self.home_interface = QWidget()
        self.home_interface.setObjectName("homeInterface")
        self.home_interface.setLayout(self.main_layout)
        self.addSubInterface(self.home_interface, FluentIcon.VIDEO, "炼成祭坛")
        
        # 添加详细信息页
        self.info_interface = MediaInfoInterface(self)
        self.info_interface.addFileRequested.connect(self.add_source_paths_from_info)
        self.addSubInterface(self.info_interface, FluentIcon.INFO, "真理之眼")
        
        # 添加个人资料页
        self.profile_interface = ProfileInterface(self)
        self.addSubInterface(self.profile_interface, FluentIcon.PEOPLE, "观测者档案")

        # 添加鸣谢页
        self.credits_interface = CreditsInterface(self)
        self.addSubInterface(self.credits_interface, FluentIcon.HEART, "羁绊之证")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._centered_once:
            self._centered_once = True
            QTimer.singleShot(0, self.center_on_screen)
            # [Add] 如果是初次运行，显示欢迎向导
            if getattr(self, 'is_first_run', False):
                QTimer.singleShot(600, self.show_welcome_wizard)
                self.is_first_run = False

        QTimer.singleShot(0, self.equalize_columns)
        QTimer.singleShot(0, self.sync_source_cache_card_height)
        QTimer.singleShot(0, self.sync_settings_selected_card_height)
        QTimer.singleShot(0, self.update_selected_zone_border)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.equalize_columns()
        self.sync_source_cache_card_height()
        self.sync_settings_selected_card_height()
        
    def equalize_columns(self):
        if hasattr(self, "column_splitter") and self.column_splitter:
            total = max(self.column_splitter.width(), 2)
            half = total // 2
            self.column_splitter.setSizes([half, total - half])

    def sync_source_cache_card_height(self):
        if hasattr(self, "card_io") and hasattr(self, "card_source"):
            target = max(self.card_io.minimumSizeHint().height(), self.card_source.minimumSizeHint().height())
            self.card_io.setFixedHeight(target)
            self.card_source.setFixedHeight(target)

    def sync_settings_selected_card_height(self):
        if not (hasattr(self, "card_settings") and hasattr(self, "card_action") and hasattr(self, "card_selected_files")):
            return

        settings_min = self.card_settings.minimumSizeHint().height()
        action_min = self.card_action.minimumSizeHint().height()
        if settings_min <= 0 or action_min <= 0:
            return

        # 使用当前可见内容的建议高度进行比例分配（保存模式切换后会变化）
        settings_pref = max(settings_min, self.card_settings.sizeHint().height())
        action_pref = max(action_min, self.card_action.sizeHint().height())
        mode_text = self.combo_save_mode.currentText() if hasattr(self, "combo_save_mode") else SAVE_MODE_SAVE_AS
        # 元素覆写/元素保留模式下，操作卡片更紧凑一点
        if mode_text != SAVE_MODE_SAVE_AS:
            action_pref = max(action_min, int(action_pref * 0.48))

        left_layout = self.left_panel.layout() if hasattr(self, "left_panel") else None
        gap = left_layout.spacing() if left_layout is not None else 12
        if gap < 0:
            gap = 12

        right_h = max(self.card_selected_files.height(), self.card_selected_files.minimumSizeHint().height())
        available = max(0, right_h - gap)

        pref_sum = max(1, settings_pref + action_pref)
        action_h = int(round(available * (action_pref / pref_sum)))
        settings_h = available - action_h

        if settings_h < settings_min:
            settings_h = settings_min
            action_h = available - settings_h
        if action_h < action_min:
            action_h = action_min
            settings_h = available - action_h

        # 极端情况下（总可用高度小于两卡片最小总和）尽量回退到可显示状态
        if settings_h < settings_min or action_h < action_min:
            settings_h = settings_min
            action_h = action_min

        self.card_settings.setFixedHeight(settings_h)
        self.card_action.setFixedHeight(action_h)

    def center_on_screen(self):
        screen = self.windowHandle().screen() if self.windowHandle() else QGuiApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.availableGeometry()
        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(screen_geo.center())
        self.move(frame_geo.topLeft())

    def show_welcome_wizard(self):
        w = WelcomeWizard(self)
        w.exec()

    def load_settings_to_ui(self):
        cfg_path = get_config_path()
        config = configparser.ConfigParser()
        
        data = DEFAULT_SETTINGS.copy()
        
        if os.path.exists(cfg_path):
            self.is_first_run = False
            try:
                config.read(cfg_path, encoding='utf-8')
                if "Settings" in config:
                    sect = config["Settings"]
                    data["encoder"] = sect.get("encoder", DEFAULT_SETTINGS["encoder"])
                    data["theme"] = sect.get("theme", DEFAULT_SETTINGS["theme"])
                    data["save_mode"] = sect.get("save_mode", DEFAULT_SETTINGS["save_mode"])
                    data["export_dir"] = sect.get("export_dir", DEFAULT_SETTINGS["export_dir"])
                
                # [Add] 加载各编码器独立配置
                for enc_name in self.encoder_settings:
                    if enc_name in config:
                        sect = config[enc_name]
                        defaults = ENCODER_CONFIGS[enc_name]
                        self.encoder_settings[enc_name] = {
                            "vmaf": sect.get("vmaf", defaults["vmaf"]),
                            "audio_bitrate": sect.get("audio_bitrate", defaults["audio_bitrate"]),
                            "preset": sect.get("preset", defaults["preset"]),
                            "loudnorm": sect.get("loudnorm", defaults["loudnorm"]),
                            "loudnorm_mode": sect.get("loudnorm_mode", defaults["loudnorm_mode"]),
                            "nv_aq": sect.get("nv_aq", defaults["nv_aq"]),
                            "amf_offset": sect.get("amf_offset", defaults.get("amf_offset", "0"))
                        }
            except Exception:
                pass
        else:
            self.is_first_run = True
            self.save_settings_file(DEFAULT_SETTINGS, self.encoder_settings)
        
        # 设置 Encoder
        enc_idx = 0
        if ENC_NVENC in data["encoder"]:
            enc_idx = 1
        elif ENC_AMF in data["encoder"]:
            enc_idx = 2
        
        # [Fix] 先设置索引，on_encoder_changed 会负责加载该编码器的具体参数
        self.last_encoder_name = self.combo_encoder.itemText(enc_idx)
        self.combo_encoder.setCurrentIndex(enc_idx)
        # 手动触发一次加载逻辑，确保 UI 与内存数据同步
        self.load_encoder_settings_to_ui(self.last_encoder_name)
        
        # 设置主题
        try:
            self.combo_theme.setCurrentIndex(THEMES.index(data["theme"]))
        except ValueError:
            self.combo_theme.setCurrentIndex(0)
        self.on_theme_changed(self.combo_theme.currentIndex()) # 确保应用

        # 设置保存模式 + 导出目录
        mode_map = {
            SAVE_MODE_SAVE_AS: 0,
            SAVE_MODE_OVERWRITE: 1,
            SAVE_MODE_REMAIN: 2
        }
        default_mode_idx = mode_map.get(DEFAULT_SETTINGS["save_mode"], 1)
        self.combo_save_mode.setCurrentIndex(mode_map.get(data["save_mode"], default_mode_idx))
        self.line_export.setText(data.get("export_dir", ""))
        self.toggle_export_ui()

    def load_encoder_settings_to_ui(self, enc_name):
        """ 将指定编码器的配置加载到 UI """
        settings = self.encoder_settings.get(enc_name, ENCODER_CONFIGS.get(enc_name))
        if not settings: return

        # 临时屏蔽信号，防止触发自动保存
        self.block_signals_for_settings(True)
        
        self.line_vmaf.setText(settings["vmaf"])
        self.line_audio.setText(settings["audio_bitrate"])
        self.line_loudnorm.setText(settings["loudnorm"])
        self.combo_loudnorm.setCurrentText(settings["loudnorm_mode"])
        self.sw_nv_aq.setChecked(settings["nv_aq"] == "True")
        self.spin_offset.setValue(int(settings.get("amf_offset", 0)))
        
        idx = self.combo_preset.findText(settings["preset"])
        if idx >= 0: self.combo_preset.setCurrentIndex(idx)
        else: self.combo_preset.setCurrentIndex(3)
        
        self.block_signals_for_settings(False)
        
        # 更新标签文本
        if ENC_NVENC in enc_name:
            self.lbl_aq.setText("NVIDIA 感知增强")
        elif ENC_AMF in enc_name:
            self.lbl_aq.setText("AMD 预分析 (PreAnalysis)")
        else:
            self.lbl_aq.setText("Intel 深度分析 (Lookahead)")
        self.sw_nv_aq.setEnabled(True)

        # 仅在硬件编码模式下启用偏移量设置 (AMD/NVIDIA/QSV 均通过 CPU 探测)
        is_hw = (ENC_AMF in enc_name) or (ENC_NVENC in enc_name) or (ENC_QSV in enc_name)
        self.lbl_offset.setEnabled(is_hw)
        self.spin_offset.setEnabled(is_hw)

    def block_signals_for_settings(self, block):
        widgets = [self.line_vmaf, self.line_audio, self.line_loudnorm, 
                   self.combo_loudnorm, self.sw_nv_aq, self.combo_preset, self.spin_offset]
        for w in widgets:
            w.blockSignals(block)

    def on_encoder_changed(self, index):
        new_encoder = self.combo_encoder.currentText()
        if new_encoder == self.last_encoder_name:
            return

        # 1. 保存上一个编码器的当前 UI 设置到内存
        prev_settings = {
            "vmaf": self.line_vmaf.text(),
            "audio_bitrate": self.line_audio.text(),
            "preset": self.combo_preset.text(),
            "loudnorm": self.line_loudnorm.text(),
            "loudnorm_mode": self.combo_loudnorm.currentText(),
            "nv_aq": str(self.sw_nv_aq.isChecked()),
            "amf_offset": str(self.spin_offset.value())
        }
        self.encoder_settings[self.last_encoder_name].update(prev_settings)
        
        # 2. 切换到新编码器
        self.last_encoder_name = new_encoder
        self.load_encoder_settings_to_ui(new_encoder)
        
        # 3. 触发一次自动保存，确保持久化
        self.auto_save_settings()

    def bind_auto_save_signals(self):
        self.combo_preset.currentIndexChanged.connect(lambda _: self.auto_save_settings())
        self.combo_theme.currentIndexChanged.connect(lambda _: self.auto_save_settings())
        self.combo_save_mode.currentIndexChanged.connect(lambda _: self.auto_save_settings())
        self.sw_nv_aq.checkedChanged.connect(lambda _: self.auto_save_settings())
        self.combo_loudnorm.currentIndexChanged.connect(lambda _: self.auto_save_settings())
        self.line_vmaf.textChanged.connect(lambda _: self.auto_save_settings())
        self.line_audio.textChanged.connect(lambda _: self.auto_save_settings())
        self.line_loudnorm.textChanged.connect(lambda _: self.auto_save_settings())
        self.line_export.textChanged.connect(lambda _: self.auto_save_settings())
        self.spin_offset.valueChanged.connect(lambda _: self.auto_save_settings())
        self.spin_offset.valueChanged.connect(lambda _: self.auto_save_settings())

    def auto_save_settings(self):
        if self._auto_save_blocked:
            return
        self.save_current_settings(show_tip=False)

    def save_settings_file(self, settings_dict, encoder_settings=None):
        """ 将配置写入文件 """
        config = configparser.ConfigParser()
        config["Settings"] = settings_dict
        
        # 如果提供了编码器配置，则写入独立 Section
        if encoder_settings:
            for enc_name, enc_conf in encoder_settings.items():
                config[enc_name] = enc_conf
                
        with open(get_config_path(), 'w', encoding='utf-8') as f:
            config.write(f)

    def save_current_settings(self, show_tip=False):
        # 1. 同步当前 UI 到内存中的编码器配置
        curr_enc = self.combo_encoder.currentText()
        if curr_enc in self.encoder_settings:
            self.encoder_settings[curr_enc].update({
                "vmaf": self.line_vmaf.text(),
                "audio_bitrate": self.line_audio.text(),
                "preset": self.combo_preset.text(),
                "loudnorm": self.line_loudnorm.text(),
                "loudnorm_mode": self.combo_loudnorm.currentText(),
                "nv_aq": str(self.sw_nv_aq.isChecked()),
                "amf_offset": str(self.spin_offset.value())
            })

        settings = {
            "encoder": curr_enc,
            "theme": THEMES[self.combo_theme.currentIndex()],
            "save_mode": self.combo_save_mode.currentText(),
            "export_dir": self.line_export.text().strip()
        }
        self.save_settings_file(settings, self.encoder_settings)
        if show_tip:
            # [Add] 按钮反馈动画
            orig_text = self.btn_save_conf.text()
            self.btn_save_conf.setText("✅ 已铭刻")
            self.btn_save_conf.setStyleSheet("color: #FB7299; font-weight: bold;")
            
            QTimer.singleShot(1000, lambda: [self.btn_save_conf.setText(orig_text), self.btn_save_conf.setStyleSheet("")])
            
            InfoBar.success("记忆已铭刻", "当前术式参数已写入 config.ini", parent=self, position=InfoBarPosition.TOP)

    def restore_defaults(self):
        self._auto_save_blocked = True
        self.setUpdatesEnabled(False) # [Add] 停止界面重绘，防止重置过程中的布局闪烁
        
        # [Fix] 屏蔽所有相关控件的信号，防止连锁触发布局计算
        widgets_to_block = [
            self.combo_encoder, self.combo_preset, self.combo_theme,
            self.combo_save_mode, self.combo_loudnorm, self.sw_nv_aq,
            self.line_vmaf, self.line_audio, self.line_loudnorm, self.line_export, self.spin_offset
        ]
        for w in widgets_to_block:
            w.blockSignals(True)
        
        # 重置内存中的配置为默认值
        self.encoder_settings = copy.deepcopy(ENCODER_CONFIGS)
        
        # 恢复当前编码器的 UI
        current_enc = self.combo_encoder.currentText()
        self.load_encoder_settings_to_ui(current_enc)
        
        self.combo_theme.setCurrentIndex(0) # Auto
        self.on_theme_changed(0) # 手动调用一次
        
        self.combo_save_mode.setCurrentIndex(1) # Overwrite
        self.line_export.clear()
        
        for w in widgets_to_block:
            w.blockSignals(False)

        self.toggle_export_ui()
        self.setUpdatesEnabled(True) # [Add] 恢复界面重绘
        self._auto_save_blocked = False

        self.save_current_settings(show_tip=False)
        
        # [Add] 按钮反馈动画
        orig_text = self.btn_reset_conf.text()
        self.btn_reset_conf.setText("✅ 已回溯")
        self.btn_reset_conf.setStyleSheet("color: #FB7299; font-weight: bold;")
        QTimer.singleShot(1000, lambda: [self.btn_reset_conf.setText(orig_text), self.btn_reset_conf.setStyleSheet("")])
        
        InfoBar.info("记忆回溯成功", "参数已重置为初始形态", parent=self, position=InfoBarPosition.TOP)
        
        # 强制处理一次事件循环，确保“正在重新校准”日志和 UI 重置状态立即显示
        QApplication.processEvents()

        if self.worker and self.worker.isRunning():
            InfoBar.warning("魔力核心重检已跳过", "当前正在进行炼成，停止任务后再执行记忆回溯可触发自检。", parent=self, position=InfoBarPosition.TOP)
        else:
            self.log(">>> 正在重新校准魔力核心可用性 (Re-calibrating)...", "info")
            # 给予 200ms 的“仪式感”延迟，确保肉眼能看到 UI 切换和日志跳动
            QTimer.singleShot(200, self.check_dependencies)

    def on_theme_changed(self, index):
        if index == 0:
            setTheme(Theme.AUTO)
        elif index == 1:
            setTheme(Theme.LIGHT)
        elif index == 2:
            setTheme(Theme.DARK)
        setThemeColor('#FB7299') # 重新应用主题色

        # [Add] 同步所有页面的主题下拉框
        combos = [self.combo_theme]
        if hasattr(self, 'info_interface'): combos.append(self.info_interface.combo_theme)
        if hasattr(self, 'profile_interface'): combos.append(self.profile_interface.combo_theme)
        if hasattr(self, 'credits_interface'): combos.append(self.credits_interface.combo_theme)
        for c in combos:
            if c.currentIndex() != index:
                c.blockSignals(True)
                c.setCurrentIndex(index)
                c.blockSignals(False)
        
        # [Fix] 浅色模式下增加卡片边框，增强层次感
        QTimer.singleShot(50, self._update_card_style)
        
        # 主题切换会刷新控件样式，延迟重绘一次拖拽提示边框，防止虚线被覆盖
        QTimer.singleShot(0, self.update_selected_zone_border)
        QTimer.singleShot(120, self.update_selected_zone_border)

    def _update_card_style(self):
        """ 根据主题调整卡片样式 (解决浅色模式太白的问题) """
        cards = self.findChildren(CardWidget)
        
        # 基础样式 (按钮悬停)
        base_qss = """
            PushButton:hover {
                border: 2px solid #FB7299;
                background-color: rgba(251, 114, 153, 0.1);
                border-radius: 6px;
            }
            PrimaryPushButton:hover {
                border: 2px solid #FFD1DC;
                border-radius: 6px;
            }
            /* 让主窗口背景完全透明以显现 Mica 效果 */
            MainWindow { background: transparent; }
        """

        if not isDarkTheme():
            self.setStyleSheet(base_qss + "MainWindow { background-color: #F3F3F3; }")
            
            for card in cards:
                card.setStyleSheet("""
                    CardWidget {
                        border: 1px solid rgba(0, 0, 0, 0.08);
                        border-radius: 10px;
                        background-color: rgba(255, 255, 255, 0.65);
                    }
                    CardWidget:hover {
                        border: 1px solid rgba(0, 0, 0, 0.1);
                        background-color: rgba(255, 255, 255, 0.75);
                        border: 1px solid rgba(251, 114, 153, 0.3);
                    }
                """)
                
                # [Add] 添加轻微阴影 (Box Shadow)
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(15)
                shadow.setColor(QColor(0, 0, 0, 20))
                shadow.setOffset(0, 2)
                card.setGraphicsEffect(shadow)
        else:
            self.setStyleSheet(base_qss + "MainWindow { background: transparent; }")
            
            for card in cards:
                card.setStyleSheet("""
                    CardWidget {
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 10px;
                        background-color: rgba(32, 32, 32, 0.65);
                    }
                    CardWidget:hover {
                        background-color: rgba(40, 40, 40, 0.75);
                        border: 1px solid rgba(251, 114, 153, 0.3);
                    }
                """)
                card.setGraphicsEffect(None)

    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            line_edit.setText(folder)

    def add_source_paths(self, paths):
        existing = set(self.selected_files)
        added = 0

        for raw in paths:
            if not raw:
                continue
            p = os.path.normpath(raw)

            if os.path.isdir(p):
                for dp, _, filenames in os.walk(p):
                    for f in filenames:
                        fp = os.path.join(dp, f)
                        if fp.lower().endswith(VIDEO_EXTS) and fp not in existing:
                            self.selected_files.append(fp)
                            existing.add(fp)
                            added += 1
            elif os.path.isfile(p):
                if p.lower().endswith(VIDEO_EXTS) and p not in existing:
                    self.selected_files.append(p)
                    existing.add(p)
                    added += 1

        if added > 0:
            self.update_selected_count()
        return added

    def handle_dropped_paths(self, paths):
        added = self.add_source_paths(paths)
        if added == 0:
            InfoBar.warning("未添加素材", "拖拽内容中没有可处理的视频文件，或已全部存在。", parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.success("素材已加入", f"拖拽添加 {added} 个文件。", parent=self, position=InfoBarPosition.TOP)

    def clear_selected_list_visual_state(self):
        if hasattr(self, "list_selected_files"):
            self.list_selected_files.clearSelection()
            self.list_selected_files.setCurrentRow(-1)

    def on_selected_zone_drag_active_changed(self, active):
        self._drag_over_source_zone = bool(active)
        self.update_selected_zone_border()

    def update_selected_zone_border(self):
        if not hasattr(self, "lbl_selected_placeholder") or not hasattr(self, "list_selected_files"):
            return

        show_hint_border = self._drag_over_source_zone or (len(self.selected_files) == 0)
        border_css = "2px dashed rgba(251, 114, 153, 0.90)" if show_hint_border else "1px solid transparent"
        bg_css = "rgba(251, 114, 153, 0.06)" if show_hint_border else "transparent"
        bg_css = "rgba(251, 114, 153, 0.1)" if show_hint_border else "rgba(128, 128, 128, 0.05)"

        self.lbl_selected_placeholder.setStyleSheet(
            f"border: {border_css}; border-radius: 10px; background: {bg_css}; padding: 8px; color: #FB7299; font-size: 18px; font-weight: 700;"
        )

        self.list_selected_files.setStyleSheet(f"""
            ListWidget {{
                background: {bg_css};
                border: {border_css};
                border-radius: 10px;
                outline: none;
            }}
            ListWidget::item {{
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            ListWidget::item:hover {{
                background: transparent;
            }}
            ListWidget::item:selected {{
                background: transparent;
            }}
            QListWidget {{
                background: {bg_css};
                border: {border_css};
                border-radius: 10px;
                outline: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            QListWidget::item:hover {{
                background: transparent;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """)

    def choose_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择素材文件夹")
        if not folder:
            return
        added = self.add_source_paths([folder])
        if added == 0:
            InfoBar.warning("未发现可用文件", "该文件夹下没有可处理的视频文件。", parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.success("素材已加入", f"已添加 {added} 个文件。", parent=self, position=InfoBarPosition.TOP)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "Video Files (*.mkv *.mp4 *.avi *.mov *.wmv *.flv *.webm *.m4v *.ts);;All Files (*.*)"
        )
        if files:
            self.add_source_paths(files)

    def open_file_location(self, item):
        """ 双击列表项打开文件所在位置 """
        if not item: return
        row = self.list_selected_files.row(item)
        if 0 <= row < len(self.selected_files):
            path = self.selected_files[row]
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            except Exception:
                pass

    # --- 任务队列管理系统 (防止线程爆炸) ---
    def process_duration_queue(self):
        """ 调度时长获取任务，限制最大并发数为 3 """
        MAX_CONCURRENT = MAX_DURATION_WORKERS
        while len(self.active_dur_workers) < MAX_CONCURRENT and self.pending_dur_tasks:
            path = self.pending_dur_tasks.pop(0)
            self.start_duration_worker(path)

    def start_duration_worker(self, path):
        worker = DurationWorker(path)
        worker.result.connect(self.update_file_duration_label)
        worker.finished.connect(worker.deleteLater) # 频繁创建的线程必须显式释放
        worker.finished.connect(lambda: self.on_duration_worker_finished(path))
        self.active_dur_workers[path] = worker
        worker.start()
        # 更新UI状态为加载中
        self.set_duration_text_in_list(path, "...")

    def on_duration_worker_finished(self, path):
        self.active_dur_workers.pop(path, None)
        self.process_duration_queue() # 继续处理下一个

    def get_file_duration(self, path):
        """ 将时长获取请求加入队列 """
        if path in self.pending_dur_tasks: return
        
        self.pending_dur_tasks.append(path)
        self.process_duration_queue()

    def update_file_duration_label(self, path, duration_str, duration_sec, meta=None):
        """ 更新列表中的时长显示，并触发缩略图获取 """
        self.cached_durations[path] = (duration_str, duration_sec)
        if meta:
            # 整合元数据供转码引擎使用
            self.file_metadata[path] = {**meta, "duration": duration_sec}

        self.set_duration_text_in_list(path, duration_str)
        
        # 获取到时长后，自动开始获取缩略图
        if path not in self.cached_thumbnails:
            self.get_file_thumbnail(path, duration_sec)

    def process_thumbnail_queue(self):
        """ 调度缩略图获取任务，限制最大并发数为 2 (避免磁盘IO过高) """
        MAX_CONCURRENT = MAX_THUMBNAIL_WORKERS
        while len(self.active_thumb_workers) < MAX_CONCURRENT and self.pending_thumb_tasks:
            path, duration = self.pending_thumb_tasks.pop(0)
            self.start_thumbnail_worker(path, duration)

    def start_thumbnail_worker(self, path, duration_sec):
        worker = ThumbnailWorker(path, duration_sec)
        worker.result.connect(self.update_file_thumbnail)
        worker.finished.connect(worker.deleteLater) # 频繁创建的线程必须显式释放
        worker.finished.connect(lambda: self.on_thumbnail_worker_finished(path))
        self.active_thumb_workers[path] = worker
        worker.start()

    def on_thumbnail_worker_finished(self, path):
        self.active_thumb_workers.pop(path, None)
        self.process_thumbnail_queue()

    def get_file_thumbnail(self, path, duration_sec):
        """ 将缩略图获取请求加入队列 """
        if path in self.active_thumb_workers: return
        # 检查是否已在等待队列
        for p, _ in self.pending_thumb_tasks:
            if p == path: return
            
        self.pending_thumb_tasks.append((path, duration_sec))
        self.process_thumbnail_queue()

    def update_file_thumbnail(self, path, image):
        if not image.isNull():
            # [Fix] 在主线程进行 QPixmap 转换和绘图操作
            pixmap = QPixmap.fromImage(image)
            
            rounded = QPixmap(pixmap.size())
            rounded.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter_path = QPainterPath()
            painter_path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 6, 6) # 6px 圆角
            painter.setClipPath(painter_path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            # [Opt] LRU 缓存逻辑
            if path in self.cached_thumbnails:
                self.cached_thumbnails.move_to_end(path)
            self.cached_thumbnails[path] = QIcon(rounded)
            
            if len(self.cached_thumbnails) > self.MAX_THUMBNAIL_CACHE:
                self.cached_thumbnails.popitem(last=False) # 弹出最旧的缓存

            # [Fix] 使用 path_to_item 快速定位 Widget，不再遍历列表
            item = self.path_to_item.get(path)
            if item:
                widget = self.list_selected_files.itemWidget(item)
                if widget:
                    icon_w = widget.findChild(IconWidget, "video_icon")
                    if icon_w:
                        icon_w.setIcon(self.cached_thumbnails[path])

    def clear_all_selected_files(self):
        """ [Add] 一键清空所有素材，重置因果律 """
        if not self.selected_files:
            return
        
        # 如果正在转码，禁止清空
        if self.worker and self.worker.isRunning():
            InfoBar.warning("术式进行中", "炼成仪式尚未结束，无法强行重置次元空间！", parent=self, position=InfoBarPosition.TOP)
            return

        # [Add] 增加确认弹窗，防止手滑
        title = "确认要归于虚无吗？"
        content = "此操作将从祭坛中移除所有待净化的异变体，因果律将被重置。确定要继续吗？"
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText("确定 (Void)")
        dialog.cancelButton.setText("取消 (Stay)")
        if not dialog.exec():
            return

        self.selected_files.clear()
        self.path_to_item.clear()
        self.list_selected_files.clear()
        self.pending_dur_tasks.clear()
        self.pending_thumb_tasks.clear()
        self.cached_durations.clear()
        self.cached_thumbnails.clear()
        self.file_metadata.clear()
        self.update_selected_count()
        self.log(">>> 祭坛已清空，所有因果律已重置。 (Voided)", "info")

    def set_duration_text_in_list(self, path, text):
        for i in range(self.list_selected_files.count()):
            if i < len(self.selected_files) and self.selected_files[i] == path:
                item = self.list_selected_files.item(i)
                widget = self.list_selected_files.itemWidget(item)
                if widget:
                    btn = widget.findChild(ClickableBodyLabel, "btn_duration")
                    if btn:
                        btn.setText(text)
                        if text not in ["...", "获取时长"]:
                            btn.setEnabled(False)
                            btn.setCursor(Qt.CursorShape.ArrowCursor)

    def remove_selected_file(self, file_path):
        self.selected_files = [p for p in self.selected_files if p != file_path]
        
        # [Fix] 增量移除 UI 元素，而不是 clear()
        if file_path in self.path_to_item:
            item = self.path_to_item.pop(file_path)
            row = self.list_selected_files.row(item)
            taken_item = self.list_selected_files.takeItem(row)
            del taken_item # 显式销毁项及其关联的 Widget

        # [Fix] 移除文件时清理缓存，防止内存泄漏
        self.cached_durations.pop(file_path, None)
        self.cached_thumbnails.pop(file_path, None)
        self.file_metadata.pop(file_path, None)
        
        # 尝试从等待队列中移除（如果还在排队）
        if file_path in self.pending_dur_tasks:
            self.pending_dur_tasks.remove(file_path)
        self.pending_thumb_tasks = [t for t in self.pending_thumb_tasks if t[0] != file_path]
        
        self.update_selected_count()

    def format_file_size(self, size_bytes):
        """ 格式化文件大小 """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def update_selected_count(self):
        count = len(self.selected_files)
        if hasattr(self, 'lbl_selected_count_right'):
            self.lbl_selected_count_right.setText(str(count))

        is_empty = (count == 0)
        self.lbl_selected_placeholder.setVisible(is_empty)
        self.list_selected_files.setVisible(not is_empty)
        self.update_selected_zone_border()

        if is_empty:
            self.list_selected_files.clear()
            self.path_to_item.clear()
            return

        # [优化] 增量添加逻辑
        for p in self.selected_files:
            if p in self.path_to_item: continue

            item = QListWidgetItem(self.list_selected_files)
            item.setSizeHint(QSize(0, 60)) # [Mod] 增加高度以容纳状态栏
            self.path_to_item[p] = item

            item_widget = QWidget(self.list_selected_files)
            item_widget.setObjectName("item_tile")
            # 为每个列表项增加“瓷砖”感
            item_widget.setStyleSheet("""
                QWidget#item_tile {
                    background-color: rgba(251, 114, 153, 0.05);
                    border: 1px solid rgba(251, 114, 153, 0.1);
                    border-radius: 8px;
                    margin: 2px 4px;
                }
                QWidget#item_tile:hover {
                    background-color: rgba(251, 114, 153, 0.12);
                    border: 1px solid rgba(251, 114, 153, 0.3);
                }
            """)
            container = QVBoxLayout(item_widget)
            container.setContentsMargins(4, 2, 4, 2)
            container.setSpacing(0)

            row = QWidget(item_widget)
            row.setFixedHeight(44)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(0)

            status_icon = IconWidget(FluentIcon.HISTORY, row)
            status_icon.setFixedSize(16, 16)
            status_icon.setObjectName("status_icon")
            
            display_icon = self.cached_thumbnails.get(p, FluentIcon.VIDEO)
            icon_widget = IconWidget(display_icon, row) 
            icon_widget.setFixedSize(24, 24)
            icon_widget.setObjectName("video_icon")
            
            row_layout.addWidget(status_icon)
            row_layout.addSpacing(4)
            row_layout.addWidget(icon_widget)
            row_layout.addSpacing(8)

            try:
                f_size = os.path.getsize(p)
                size_str = self.format_file_size(f_size)
            except Exception:
                size_str = "Unknown"
            
            name_label = BodyLabel(os.path.basename(p) or p, row)
            name_label.setToolTip(p)

            btn_remove = ClickableBodyLabel("移除", row)
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setStyleSheet("font-weight: 700; background: transparent;")
            btn_remove.setTextColor(QColor("#D93652"), QColor("#FF8FA1"))
            btn_remove.clicked.connect(lambda path=p: self.remove_selected_file(path))

            dur_text = "获取时长"
            if p in self.cached_durations:
                dur_text = self.cached_durations[p][0]
            
            btn_duration = ClickableBodyLabel(dur_text, row)
            btn_duration.setObjectName("btn_duration")
            btn_duration.setFixedWidth(60)
            btn_duration.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            size_label = BodyLabel(size_str, row)
            size_label.setTextColor(QColor("#999999"), QColor("#999999"))
            size_label.setFixedWidth(80)
            size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            row_layout.addWidget(name_label, 1)
            row_layout.addSpacing(12)
            row_layout.addWidget(btn_duration)
            row_layout.addSpacing(0)
            row_layout.addWidget(size_label)
            row_layout.addSpacing(12)
            row_layout.addWidget(btn_remove)
            
            container.addWidget(row)

            # [Add] 底部状态栏容器 (进度条 + 速度/ETA)
            stats_layout = QHBoxLayout()
            stats_layout.setContentsMargins(6, 0, 12, 4)
            stats_layout.setSpacing(10)

            pbar = ProgressBar(item_widget)
            pbar.setFixedHeight(4)
            pbar.setValue(0)
            pbar.hide()
            pbar.setObjectName("pbar")
            
            lbl_stats = BodyLabel("", item_widget)
            lbl_stats.setObjectName("lbl_stats")
            lbl_stats.setStyleSheet("font-size: 11px; font-weight: bold; color: #FB7299;")
            lbl_stats.hide()
            
            stats_layout.addWidget(pbar, 1)
            stats_layout.addWidget(lbl_stats)
            
            container.addLayout(stats_layout)

            self.list_selected_files.setItemWidget(item, item_widget)
            if p not in self.cached_durations:
                self.get_file_duration(p)

        self.clear_selected_list_visual_state()

    def update_file_progress(self, filepath, percent):
        """ [Fix] 通过路径查找 Widget，解决 index 偏移问题 """
        item = self.path_to_item.get(filepath)
        if not item: return
        widget = self.list_selected_files.itemWidget(item)
        if widget:
            pbar = widget.findChild(ProgressBar, "pbar")
            if pbar:
                if pbar.isHidden(): pbar.show()
                pbar.setValue(percent)

    def update_file_stats(self, filepath, speed, eta):
        """ [Add] 更新单个文件的速度和 ETA """
        item = self.path_to_item.get(filepath)
        if not item: return
        widget = self.list_selected_files.itemWidget(item)
        if widget:
            lbl = widget.findChild(BodyLabel, "lbl_stats")
            pbar = widget.findChild(ProgressBar, "pbar")
            if lbl:
                if lbl.isHidden(): lbl.show()
                lbl.setText(f"{speed} | {eta}")
            if pbar and pbar.isHidden(): pbar.show()

    def update_file_status(self, filepath, status):
        """ [Fix] 通过路径查找 Widget """
        item = self.path_to_item.get(filepath)
        if not item: return
        widget = self.list_selected_files.itemWidget(item)
        if widget:
            icon_w = widget.findChild(IconWidget, "status_icon")
            pbar = widget.findChild(ProgressBar, "pbar")
            lbl_stats = widget.findChild(BodyLabel, "lbl_stats") # [Add]
            if icon_w:
                if status == "processing":
                    icon_w.setIcon(FluentIcon.SYNC)
                    if lbl_stats: lbl_stats.setStyleSheet("font-size: 11px; font-weight: bold; color: #FB7299;")
                elif status == "success":
                    icon_w.setIcon(FluentIcon.ACCEPT)
                    if pbar: pbar.hide() # 完成后隐藏进度条
                    if lbl_stats: 
                        # [Mod] 完成后不隐藏，改为绿色显示
                        lbl_stats.setStyleSheet("font-size: 11px; font-weight: bold; color: #55E555;")
                        lbl_stats.show()
                elif status == "error":
                    icon_w.setIcon(FluentIcon.CANCEL)
                    if pbar: pbar.hide()
                    if lbl_stats: lbl_stats.hide() # [Add]

    def toggle_export_ui(self):
        mode_text = self.combo_save_mode.currentText()
        is_save_as = (mode_text == SAVE_MODE_SAVE_AS)
        self.export_container.setVisible(is_save_as)
        # 仅刷新布局，避免强制 resize 在无边框窗口下触发异常
        self.export_container.updateGeometry()
        if self.card_action.layout():
            self.card_action.layout().activate()
        self.card_action.updateGeometry()
        self.sync_settings_selected_card_height()
        QTimer.singleShot(0, self.sync_settings_selected_card_height)

    def log(self, msg, level="info"):
        # [Fix] 使用互斥锁确保多线程下日志队列的线程安全，防止日志丢失
        self.log_mutex.lock()
        self.log_queue.append((time.time(), msg, level))
        self.log_mutex.unlock()

    def process_log_queue(self):
        self.log_mutex.lock()
        if not self.log_queue:
            self.log_mutex.unlock()
            return

        if len(self.log_queue) > LOG_MAX_BLOCKS // 2:
            self.log_queue = self.log_queue[-(LOG_MAX_BLOCKS // 2):]

        batch = self.log_queue[:]
        self.log_queue.clear()
        self.log_mutex.unlock()

        is_dark = isDarkTheme()
        # [Opt] 魔法少女风格的彩色日志方案
        colors = {
            "dark": {
                "ts": "#707070",
                "info": "#DCDCDC",
                "success": "#A6E22E", # 亮绿 (Monokai 风格)
                "warning": "#E6DB74", # 亮黄
                "error": "#FF5277",   # 魔法红/粉
            },
            "light": {
                "ts": "#888888",
                "info": "#333333",
                "success": "#228B22", # 森林绿
                "warning": "#B8860B", # 暗金
                "error": "#D93652",   # 判定红
            }
        }
        
        theme = "dark" if is_dark else "light"
        c = colors[theme]
        ts_color = c["ts"]
        
        # 为不同级别添加图标前缀，增加视觉识别度
        icons = {
            "info": "💡",
            "success": "✨",
            "warning": "⚠️",
            "error": "💢"
        }

        html_buffer = []
        for t, msg, level in batch:
            timestamp = time.strftime('%H:%M:%S', time.localtime(t))
            msg_color = c.get(level, c["info"])
            icon = icons.get(level, "•")

            # [Fix] 采用最兼容的 HTML 转义方案：<br> 换行 + &nbsp; 空格，确保排版整齐
            msg = str(msg).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")

            html = (
                f'<span style="color:{ts_color}; font-family: \'Cascadia Code\', \'Consolas\', monospace; font-size: 11px;">[{timestamp}]</span>&nbsp;'
                f'<span style="color:{msg_color}; font-weight: {"600" if level in ["error", "warning", "success"] else "normal"};">'
                f'{icon} {msg}</span><br>'
            )
            html_buffer.append(html)
        
        # 批量更新 UI
        self.text_log.setUpdatesEnabled(False)
        cursor = self.text_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml("".join(html_buffer))
        self.text_log.setTextCursor(cursor)
        self.text_log.ensureCursorVisible()
        
        # [Add] 日志自动清理 (超过2000行清空)
        if self.text_log.document().blockCount() > LOG_MAX_BLOCKS:
            self.text_log.clear()
            # 直接插入清理提示，不走队列
            self.text_log.append(f'<div style="color:{c["info"]}; font-family: \'Cascadia Code\'; font-size: 11px;">>>> 历史因果已抹除，日志重新开始记录。</div>')

        self.text_log.setUpdatesEnabled(True)

    def clear_cache_files(self):
        cache_path = self.line_cache.text().strip() or get_default_cache_dir()
        if not os.path.exists(cache_path):
            InfoBar.warning("目标丢失", "请先指定有效的魔力缓冲区域...", parent=self, position=InfoBarPosition.TOP)
            return
        
        # [Add] 净化确认弹窗
        title = "确认要肃清魔力残渣吗？"
        content = f"这些是炼成仪式中产生的混沌碎片 (*.temp.mkv)，继续留存可能会干扰世界线的稳定。\n\n目标区域：{cache_path}\n\n一旦执行肃清，这些碎片将彻底归于虚无，无法找回。确定要发动净化术式吗？"
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText("发动净化 (Purify)")
        dialog.cancelButton.setText("维持现状 (Stay)")
        
        if not dialog.exec():
            return

        try:
            count = 0
            for f in os.listdir(cache_path):
                # 仅删除看起来像临时文件的文件，避免误删
                if f.endswith(".temp.mkv"):
                    os.remove(os.path.join(cache_path, f))
                    count += 1
            InfoBar.success("净化完成", f"已清除 {count} 个魔力残渣！", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("净化失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def start_task(self):
        if not self.selected_files:
            InfoBar.warning(title="提示", content="请先选择视频源文件夹或视频文件！", orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, parent=self)
            return

        save_mode = self.combo_save_mode.currentText()
        export_dir = self.line_export.text().strip()
        if save_mode == SAVE_MODE_SAVE_AS and not export_dir:
            InfoBar.warning("缺少导出目录", "当前是“开辟新世界 (Save As)”模式，请先选择导出文件夹。", parent=self, position=InfoBarPosition.TOP)
            return

        # 参数校验
        try:
            vmaf_val = float(self.line_vmaf.text())
        except ValueError:
            InfoBar.error("参数错误", "VMAF 必须是数字 (例如 93.0)", parent=self, position=InfoBarPosition.TOP)
            return

        config = {
            'selected_files': self.selected_files[:],
            'encoder': self.combo_encoder.currentText(),
            'export_dir': export_dir,
            'save_mode': save_mode,
            'cache_dir': self.line_cache.text().strip() or get_default_cache_dir(),
            'preset': self.combo_preset.text(),
            'vmaf': vmaf_val,
            'metadata': self.file_metadata.copy(),
            'audio_bitrate': self.line_audio.text(),
            'loudnorm': self.line_loudnorm.text(),
            'nv_aq': self.sw_nv_aq.isChecked(),
            'amf_offset': self.spin_offset.value(),
            'loudnorm_mode': self.combo_loudnorm.currentText()
        }
        os.makedirs(config['cache_dir'], exist_ok=True)

        self.worker = EncoderWorker(config)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_total_signal.connect(self.pbar_total.setValue)
        self.worker.progress_current_signal.connect(self.pbar_current.setValue)
        self.worker.file_progress_signal.connect(self.update_file_progress)
        self.worker.file_stats_signal.connect(self.update_file_stats) # [Add]
        self.worker.file_status_signal.connect(self.update_file_status)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.ask_error_decision.connect(self.on_worker_error)
        self.worker.finished.connect(self.worker.deleteLater) # 释放转码线程
        
        self.worker.start()
        
        self.btn_start.setEnabled(False)
        self.btn_clear_list.setEnabled(False) # 运行中禁止清空
        self.btn_start.setText("✨ 奇迹发生中...")
        self.btn_pause.setEnabled(True)
        self.combo_encoder.setEnabled(False) # 运行中禁止切换后端
        self.combo_save_mode.setEnabled(False) # 运行中禁止切换保存模式
        self.btn_pause.setText("⏳ 时空冻结 (Pause)")
        self.btn_stop.setEnabled(True)
        self.pbar_total.setValue(0)
        self.pbar_current.setValue(0)

    def on_worker_error(self, title, content):
        """ 处理转码失败时的弹窗询问 """
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText("跳过并继续 (Skip)")
        dialog.cancelButton.setText("停止任务 (Stop)")
        
        self.error_countdown = 30
        
        def update_timer():
            self.error_countdown -= 1
            dialog.titleLabel.setText(f"{title} ({self.error_countdown}s 后自动跳过)")
            if self.error_countdown <= 0:
                timer.stop()
                dialog.accept() # 默认接受（继续）
        
        timer = QTimer(self)
        timer.timeout.connect(update_timer)
        timer.start(1000)
        
        dialog.titleLabel.setText(f"{title} ({self.error_countdown}s 后自动跳过)")
        res = dialog.exec()
        timer.stop()
        
        decision = 'continue' if res else 'stop'
        if self.worker:
            self.worker.receive_decision(decision)

    def stop_task(self):
        if self.worker:
            self.log(">>> 正在请求中止...", "error")
            self.worker.stop()
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)

    def pause_task(self):
        if self.worker:
            if self.worker.is_paused:
                self.worker.set_paused(False)
                self.btn_pause.setText("⏳ 时空冻结 (Pause)")
                self.log(">>> 时空流动已恢复...", "info")
            else:
                self.worker.set_paused(True)
                self.btn_pause.setText("▶️ 时空流动 (Resume)")
                self.log(">>> 固有结界已冻结 (Paused)...", "info")

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_clear_list.setEnabled(True)
        self.btn_start.setText("✨ 缔结契约 (Start)")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.combo_encoder.setEnabled(True)
        self.combo_save_mode.setEnabled(True)
        self.worker = None

    def apply_encoder_availability(self, has_qsv, has_nvenc, has_amf):
        """根据自检结果启用/禁用魔力核心选项，返回自动切换到的后端名(若发生切换)。"""
        mapping = [(ENC_QSV, 0, has_qsv), (ENC_NVENC, 1, has_nvenc), (ENC_AMF, 2, has_amf)]

        for _, idx, enabled in mapping:
            self.combo_encoder.setItemEnabled(idx, enabled)

        available = [(name, idx) for name, idx, enabled in mapping if enabled]
        if not available:
            self.combo_encoder.setEnabled(False)
            return None

        # 仅当当前不在任务中时允许切换/启用
        if not (self.worker and self.worker.isRunning()):
            self.combo_encoder.setEnabled(True)

        current = self.combo_encoder.currentText()
        valid_names = {name for name, _ in available}
        if current not in valid_names:
            self.combo_encoder.setCurrentIndex(available[0][1])
            return available[0][0]

        return None

    def check_dependencies(self):
        """ 启动时检查依赖组件 (多线程版) """
        # [Fix] 防止重复启动
        if self.dep_worker:
            try:
                if self.dep_worker.isRunning():
                    self.log(">>> 自检术式已在运行中，请勿重复咏唱。", "warning")
                    return
            except RuntimeError:
                # C++ 对象已被删除，重置引用
                self.dep_worker = None

        self.log(">>> 正在启动环境自检术式 (Initializing environment check)...", "info")
        self.dep_worker = DependencyWorker()
        self.dep_worker.log_signal.connect(self.log)
        self.dep_worker.missing_signal.connect(self.on_dependency_missing)
        self.dep_worker.finished.connect(self.dep_worker.deleteLater) # 释放自检线程
        self.dep_worker.finished.connect(self.on_dependency_worker_finished) # [Add] 清理引用
        self.dep_worker.result_signal.connect(self.on_dependency_check_finished)
        self.dep_worker.start()

    def on_dependency_worker_finished(self):
        """ 自检线程结束后的清理工作 """
        self.dep_worker = None

    def on_dependency_missing(self, missing):
        title = "⚠️ 结界破损警告 (Critical Error)"
        content = (
            "呜哇！大事不好了！(>_<)\n"
            "工坊的魔力回路检测到了严重的断裂！\n\n"
            "以下核心圣遗物似乎离家出走了：\n"
            f"{chr(10).join(missing)}\n\n"
            "没有它们，炼成仪式将无法进行！\n"
            "请尽快将它们召回至工坊目录！"
        )
        
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText("GitHub (Search)")
        dialog.cancelButton.setText("我这就去修 (OK)")
        
        if dialog.exec():
            QDesktopServices.openUrl(QUrl("https://github.com/"))
        
        # 禁用开始按钮防止报错
        self.btn_start.setEnabled(False)
        self.btn_start.setText("🚫 缺少组件")
        self.apply_encoder_availability(False, False, False)
        self.log(">>> 致命错误：关键组件缺失，系统已停摆。", "error")

    def on_dependency_check_finished(self, has_qsv, has_nvenc, has_amf):
        switched_to = self.apply_encoder_availability(has_qsv, has_nvenc, has_amf)

        if not has_qsv and not has_nvenc and not has_amf:
            self.log(">>> 警告：未侦测到有效的 AV1 硬件编码器 (QSV/NVENC/AMF)。", "error")
            InfoBar.warning("硬件不支持", "您的显卡似乎不支持 AV1 硬件编码，或者驱动未正确安装。", parent=self, position=InfoBarPosition.TOP)
        else:
            msg = ">>> 适格者认证通过："
            if has_qsv:
                msg += f" [{ENC_QSV}]"
            if has_nvenc:
                msg += f" [{ENC_NVENC}]"
            if has_amf:
                msg += f" [{ENC_AMF}]"
            self.log(msg + " (Ready)", "success")
            if switched_to:
                self.log(f">>> 已自动切换至 {switched_to} 术式。", "info")

    def add_source_paths_from_info(self, path):
        added = self.add_source_paths([path])
        if added > 0:
            self.switchTo(self.home_interface)
            InfoBar.success("同步成功", "该物质已成功纳入祭坛！", parent=self, position=InfoBarPosition.TOP)

    def closeEvent(self, event):
        """ [Fix] 窗口关闭时强制终止所有子进程 """
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)
        
        # [Fix] 停止所有活跃的时长/缩略图线程，防止僵尸进程
        self.pending_dur_tasks.clear()
        self.pending_thumb_tasks.clear()
        
        for worker in self.active_dur_workers.values():
            try: worker.stop()
            except RuntimeError: pass
            
        for worker in self.active_thumb_workers.values():
            try: worker.stop()
            except RuntimeError: pass

        # 清理真理之眼的分析线程
        self.info_interface.stop_worker()
        super().closeEvent(event)