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
from i18n.translator import tr, translator
from ui.common import ClickableBodyLabel, DroppableBodyLabel, DroppableListWidget

# --- 初次运行欢迎向导 ---
class WelcomeWizard(MessageBoxBase):
    """ 初次运行时显示的欢迎和设置向导。 """
    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 Key 而非直接翻译，以便后续动态切换语言
        self.pages_config = [
            ("welcome.wizard.page1.title", "welcome.wizard.page1.content"),
            ("welcome.wizard.page2.title", "welcome.wizard.page2.content"),
            ("welcome.wizard.page3.title", "welcome.wizard.page3.content"),
            ("welcome.wizard.page4.title", "welcome.wizard.page4.content"),
            ("welcome.wizard.page5.title", "welcome.wizard.page5.content")
        ]
        
        self.titleLabel = SubtitleLabel("", self)

        # 创建语言切换下拉框，放在 viewLayout 中使其在所有页面可见
        self.lang_combo = ComboBox(self)
        self.lang_combo.setMinimumWidth(200)
        lang_map = translator.get_language_map()
        for lang_code, lang_name in lang_map.items():
            self.lang_combo.addItem(lang_name, userData=lang_code)
        
        # 设置当前语言
        curr = translator.current_lang
        idx = self.lang_combo.findData(curr)
        if idx >= 0: self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.on_wizard_language_changed)

        self.view = QStackedWidget(self)
        self.page_labels = [] # 存储 Label 引用用于重翻译
        
        self.init_pages()
        
        # 调整布局和尺寸
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.lang_combo)
        self.viewLayout.addWidget(self.view)
        self.widget.setFixedSize(480, 400) # 稍微调高一点给下拉框留空间
        
        self.current_idx = 0
        self.view.setCurrentIndex(0)
        self.retranslate_wizard()
        
        # 重新绑定信号 (接管默认的 accept/reject 行为)
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self.next_page)
        self.cancelButton.clicked.disconnect()
        self.cancelButton.clicked.connect(self.reject)

    def init_pages(self):
        """ 初始化所有向导页面。 """
        for i, (t_key, c_key) in enumerate(self.pages_config):
            page = QWidget()
            vbox = QVBoxLayout(page)
            vbox.setContentsMargins(0, 10, 0, 0)
            vbox.setSpacing(10)
            
            lbl_title = StrongBodyLabel("", page)
            lbl_content = BodyLabel("", page)
            lbl_content.setWordWrap(True)
            text_color = "#666666" if not isDarkTheme() else "#CCCCCC"
            lbl_content.setStyleSheet(f"color: {text_color}; font-size: 13px; line-height: 1.5;")
            
            vbox.addWidget(lbl_title)
            vbox.addWidget(lbl_content)
            
            vbox.addStretch(1)
            self.view.addWidget(page)
            self.page_labels.append((lbl_title, lbl_content))

    def on_wizard_language_changed(self, index):
        """ 当向导中的语言下拉框改变时。 """
        lang_code = self.lang_combo.itemData(index)
        if lang_code == translator.current_lang:
            return
            
        translator.set_language(lang_code)
        self.retranslate_wizard()
        
        # 同步更新主界面 (如果父窗口是 MainWindow)
        main_win = self.parent()
        if main_win and hasattr(main_win, 'retranslate_ui'):
            main_win.retranslate_ui()
            # 同步主界面的下拉框索引
            if hasattr(main_win, 'combo_lang'):
                main_win.combo_lang.blockSignals(True)
                main_win.combo_lang.setCurrentIndex(index)
                main_win.combo_lang.blockSignals(False)

    def retranslate_wizard(self):
        """ 刷新向导界面的所有文本。 """
        self.titleLabel.setText(tr("welcome.wizard.title"))
        
        # 既然是无限循环，确认按钮始终显示“翻阅魔导书”
        self.yesButton.setText(tr("welcome.wizard.next_button"))
        self.cancelButton.setText(tr("welcome.wizard.skip_button"))
        
        # 更新每一页的文本
        for i, (t_key, c_key) in enumerate(self.pages_config):
            lbl_title, lbl_content = self.page_labels[i]
            lbl_title.setText(tr(t_key))
            lbl_content.setText(tr(c_key))

    def next_page(self):
        """ 切换到下一个向导页面（无限循环）。 """
        self.current_idx = (self.current_idx + 1) % len(self.pages_config)
        self.view.setCurrentIndex(self.current_idx)

# --- 主窗口 (Win11 风格) ---
class MainWindow(FluentWindow):
    """ 应用程序的主窗口，集成了所有UI组件和核心逻辑。 """
    OLD_VALUE_MAP = {
        "开辟新世界 (Save As)": SAVE_MODE_SAVE_AS,
        "元素覆写 (Overwrite)": SAVE_MODE_OVERWRITE,
        "元素保留 (Remain)": SAVE_MODE_REMAIN,
        "全部启用 (Always)": LOUDNORM_MODE_ALWAYS,
        "全部禁用 (Disable)": LOUDNORM_MODE_DISABLE,
        "仅立体声/单声道 (Stereo/Mono Only)": LOUDNORM_MODE_AUTO,
    }

    def __init__(self):
        super().__init__()
        
        self._base_min_size = MIN_WINDOW_SIZE
        self._centered_once = False
        
        self.save_modes = [SAVE_MODE_SAVE_AS, SAVE_MODE_OVERWRITE, SAVE_MODE_REMAIN]
        self.loudnorm_modes = [LOUDNORM_MODE_AUTO, LOUDNORM_MODE_ALWAYS, LOUDNORM_MODE_DISABLE]

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
        self.worker = None # 编码工作线程
        self.selected_files = [] # 待处理的文件列表
        self._drag_over_source_zone = False # 拖拽状态标志
        self._auto_save_blocked = False # 自动保存状态标志
        self.dep_worker = None # 依赖检查工作线程
        self.active_dur_workers = {}   # 正在运行的时长线程
        self.pending_dur_tasks = []    # 等待中的时长任务
        self.active_thumb_workers = {} # 正在运行的缩略图线程
        self.pending_thumb_tasks = []  # 等待中的缩略图任务
        self.cached_durations = {} # 视频时长缓存
        self.cached_thumbnails = OrderedDict() # 视频缩略图LRU缓存
        self.MAX_THUMBNAIL_CACHE = MAX_THUMBNAIL_CACHE_SIZE
        self.path_to_item = {}     # 文件路径到列表项的映射
        self.file_metadata = {}    # 媒体元数据缓存
        
        # 日志缓冲队列，优化高频日志性能
        self.log_mutex = QMutex()
        self.log_queue = []
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.process_log_queue)
        self.log_timer.start(LOG_UPDATE_INTERVAL)
        
        # 编码器配置管理
        self.last_encoder_name = "Intel QSV"
        self.encoder_settings = copy.deepcopy(ENCODER_CONFIGS)
        
        # 初始化 UI
        self.init_ui()
        self.retranslate_ui()
        self.apply_min_window_size()
        self.load_settings_to_ui()
        self.combo_encoder.currentIndexChanged.connect(self.on_encoder_changed)
        self.bind_auto_save_signals()

        # 连接所有页面的主题切换信号
        for interface in [self.info_interface, self.profile_interface, self.credits_interface]:
            interface.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
            
        # 连接所有页面的语言切换信号，并同步初始状态
        for interface in [self.info_interface, self.profile_interface, self.credits_interface]:
            interface.combo_lang.currentIndexChanged.connect(self.on_language_changed)
            interface.combo_lang.blockSignals(True)
            interface.combo_lang.setCurrentIndex(self.combo_lang.currentIndex())
            interface.combo_lang.blockSignals(False)
        
        # 欢迎语
        kaomojis = ["(｡•̀ᴗ-)✧", "(*/ω＼*)", "ヽ(✿ﾟ▽ﾟ)ノ", "(๑•̀ㅂ•́)و✧"]
        self.log(tr("log.system_ready", kaomoji=random.choice(kaomojis)), "info")
        
        # 启动后延迟检查依赖
        QTimer.singleShot(DEPENDENCY_CHECK_DELAY, self.check_dependencies)

    def _populate_combo(self, combo: ComboBox, items: list):
        """ 使用可翻译的文本填充组合框，并将原始键存储在userData中。 """
        current_data = combo.currentData()
        is_blocked = combo.signalsBlocked()
        combo.blockSignals(True)
        combo.clear()

        key_map = {
            SAVE_MODE_SAVE_AS: "home.action_card.save_mode.save_as",
            SAVE_MODE_OVERWRITE: "home.action_card.save_mode.overwrite",
            SAVE_MODE_REMAIN: "home.action_card.save_mode.remain",
            LOUDNORM_MODE_AUTO: "home.settings_card.loudnorm_mode.auto",
            LOUDNORM_MODE_ALWAYS: "home.settings_card.loudnorm_mode.always",
            LOUDNORM_MODE_DISABLE: "home.settings_card.loudnorm_mode.disable",
        }

        for key in items:
            tr_key = key_map.get(key, key)
            combo.addItem(tr(tr_key), userData=key)

        index = combo.findData(current_data)
        if index == -1:
            index = 0
        combo.setCurrentIndex(index)
        combo.blockSignals(is_blocked)

    def retranslate_ui(self):
        """ 根据当前语言重新翻译整个界面的文本。 """
        self.setWindowTitle(tr("app.title"))

        # 头部
        self.title.setText(tr("home.header.title"))
        self.subtitle.setText(tr("home.header.subtitle"))
        self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
        self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
        self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))

        # 缓存卡片
        self.cache_card_title.setText(tr("home.cache_card.title"))
        self.btn_clear_cache.setText(tr("home.cache_card.clear_button"))
        self.line_cache.setPlaceholderText(tr("home.cache_card.path_placeholder"))
        self.btn_cache.setText(tr("home.cache_card.browse_button"))

        # 设置卡片
        self.settings_card_encoder_label.setText(tr("home.settings_card.encoder.label"))
        self.settings_card_vmaf_label.setText(tr("home.settings_card.vmaf.label"))
        self.settings_card_bitrate_label.setText(tr("home.settings_card.bitrate.label"))
        self.settings_card_preset_label.setText(tr("home.settings_card.preset.label"))
        self.lbl_offset.setText(tr("home.settings_card.offset.label"))
        self.settings_card_loudnorm_label.setText(tr("home.settings_card.loudnorm.label"))
        self.sw_nv_aq.setOnText(tr("home.settings_card.nv_aq.on"))
        self.sw_nv_aq.setOffText(tr("home.settings_card.nv_aq.off"))

        current_enc = self.combo_encoder.currentText()
        if ENC_NVENC in current_enc:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.nvidia"))
        elif ENC_AMF in current_enc:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.amd"))
        else:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.intel"))

        self.btn_save_conf.setText(tr("home.settings_card.save_button"))
        self.btn_reset_conf.setText(tr("home.settings_card.reset_button"))
        self._populate_combo(self.combo_loudnorm, self.loudnorm_modes)

        # 操作卡片
        self._populate_combo(self.combo_save_mode, self.save_modes)
        self.line_export.setPlaceholderText(tr("home.action_card.export_path_placeholder"))
        self.btn_export.setText(tr("home.action_card.choose_button"))
        self.btn_start.setText(tr("home.action_card.start_button"))
        self.btn_pause.setText(tr("home.action_card.pause_button"))
        self.btn_stop.setText(tr("home.action_card.stop_button"))

        # 源文件卡片
        self.source_card_title.setText(tr("home.source_card.title"))
        self.btn_src.setText(tr("home.source_card.folder_button"))
        self.btn_files.setText(tr("home.source_card.file_button"))

        # 文件列表卡片
        self.file_list_card_title.setText(tr("home.file_list_card.title"))
        self.btn_clear_list.setText(tr("home.file_list_card.clear_button"))
        self.lbl_selected_placeholder.setText(tr("home.file_list_card.placeholder"))

        # 状态栏
        self.lbl_current.setText(tr("home.status_bar.current_label"))
        self.lbl_total.setText(tr("home.status_bar.total_label"))

        # 子界面
        self.navigationInterface.widget("homeInterface").setText(tr("home.title"))
        self.navigationInterface.widget("mediaInfoInterface").setText(tr("info.title"))
        self.navigationInterface.widget("profileInterface").setText(tr("profile.title"))
        self.navigationInterface.widget("creditsInterface").setText(tr("credits.title"))
        
        self.info_interface.retranslate_ui()
        self.profile_interface.retranslate_ui()
        self.credits_interface.retranslate_ui()

        self.footer.setText(tr("app.designed_by"))
        self.update()


    def on_language_changed(self, index):
        """ 当用户在设置中更改语言时调用。 """
        # 同步所有界面的语言下拉框状态，防止递归触发
        combos = [self.combo_lang]
        if hasattr(self, 'info_interface'): combos.append(self.info_interface.combo_lang)
        if hasattr(self, 'profile_interface'): combos.append(self.profile_interface.combo_lang)
        if hasattr(self, 'credits_interface'): combos.append(self.credits_interface.combo_lang)
        
        for c in combos:
            if c.currentIndex() != index:
                c.blockSignals(True)
                c.setCurrentIndex(index)
                c.blockSignals(False)

        lang_code = self.combo_lang.itemData(index)
        translator.set_language(lang_code)

        dialog = MessageDialog(tr("dialog.language_change.title"), tr("dialog.language_change.content"), self)
        dialog.yesButton.setText(tr("dialog.language_change.yes_button"))
        dialog.cancelButton.hide()
        dialog.exec()
        self.retranslate_ui()

    def apply_min_window_size(self):
        """根据当前布局自动计算最小可用尺寸，避免控件挤压错位。"""
        hint = self.minimumSizeHint()
        min_w = max(self._base_min_size.width(), hint.width())
        min_h = max(self._base_min_size.height(), hint.height())
        self.setMinimumSize(min_w, min_h)
        if self.width() < min_w or self.height() < min_h:
            self.resize(max(self.width(), min_w), max(self.height(), min_h))

    def init_ui(self):
        """ 初始化主窗口的所有UI组件。 """
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
        """ 初始化窗口头部区域，包括标题和主题/语言切换。 """
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_block = QVBoxLayout()
        self.title = SubtitleLabel("炼成祭坛", self)
        self.subtitle = BodyLabel("AV1 硬件加速魔力驱动 · 绝对领域 Edition", self)
        self.subtitle.setTextColor(QColor("#999999"), QColor("#999999"))
        title_block.addWidget(self.title)
        title_block.addWidget(self.subtitle)
        title_block.setSpacing(2)
        header_row.addLayout(title_block, 1)

        self.combo_lang = ComboBox(self)
        self.combo_lang.setMinimumWidth(120)
        lang_map = translator.get_language_map()
        for lang_code, lang_name in lang_map.items():
            self.combo_lang.addItem(lang_name, userData=lang_code)
        
        current_lang = translator.current_lang
        for i in range(self.combo_lang.count()):
            if self.combo_lang.itemData(i) == current_lang:
                self.combo_lang.setCurrentIndex(i)
                break
        
        self.combo_lang.currentIndexChanged.connect(self.on_language_changed)
        header_row.addWidget(self.combo_lang, 0, Qt.AlignmentFlag.AlignCenter)

        self.combo_theme = ComboBox(self)
        self.combo_theme.addItem("世界线收束 (Auto)", FluentIcon.SYNC)
        self.combo_theme.addItem("光之加护 (Light)", FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem("深渊凝视 (Dark)", FluentIcon.QUIET_HOURS)
        self.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
        self.combo_theme.setMinimumWidth(140)
        header_row.addWidget(self.combo_theme, 0, Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addLayout(header_row)

    def _init_content_area(self):
        """ 初始化内容区域，分为左右两栏。 """
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
        """ 初始化左侧面板内容（缓存、设置、操作）。 """
        self._init_cache_card()
        self._init_settings_card()
        self._init_action_card()

    def _init_cache_card(self):
        """ 初始化缓存设置卡片。 """
        self.card_io = CardWidget(self)
        io_layout = QVBoxLayout(self.card_io)
        io_layout.setContentsMargins(18, 16, 18, 16)
        io_layout.setSpacing(12)

        h_cache_head = QHBoxLayout()
        self.cache_card_title = StrongBodyLabel("魔力回路缓冲 (Cache)", self.card_io)
        h_cache_head.addWidget(self.cache_card_title)
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
        self.btn_cache.setMinimumWidth(80)
        self.btn_cache.clicked.connect(lambda: self.browse_folder(self.line_cache))
        h2.addWidget(self.line_cache)
        h2.addWidget(self.btn_cache)
        
        io_layout.addLayout(h2)
        self.left_column.addWidget(self.card_io)

    def _init_settings_card(self):
        """ 初始化编码设置卡片。 """
        self.card_settings = CardWidget(self)
        set_layout = QVBoxLayout(self.card_settings)
        set_layout.setContentsMargins(20, 20, 20, 20)
        set_layout.setSpacing(18)
        
        row1 = QHBoxLayout()
        row1.setSpacing(12)
        
        v1 = QVBoxLayout()
        self.settings_card_encoder_label = StrongBodyLabel("魔力核心 (Encoder)", self.card_settings)
        v1.addWidget(self.settings_card_encoder_label)
        self.combo_encoder = ComboBox(self.card_settings)
        self.combo_encoder.addItems(["Intel QSV", "NVIDIA NVENC", "AMD AMF"])
        self.combo_encoder.setMinimumWidth(140)
        self.combo_encoder.setMinimumHeight(36)
        v1.addWidget(self.combo_encoder)

        v2 = QVBoxLayout()
        self.settings_card_vmaf_label = StrongBodyLabel("视界还原度 (VMAF)", self.card_settings)
        v2.addWidget(self.settings_card_vmaf_label)
        self.line_vmaf = LineEdit(self.card_settings)
        self.line_vmaf.setMinimumHeight(36)
        self.line_vmaf.setMinimumWidth(60)
        v2.addWidget(self.line_vmaf)
        
        v3 = QVBoxLayout()
        self.settings_card_bitrate_label = StrongBodyLabel("共鸣频率 (Bitrate)", self.card_settings)
        v3.addWidget(self.settings_card_bitrate_label)
        self.line_audio = LineEdit(self.card_settings)
        self.line_audio.setMinimumHeight(36)
        self.line_audio.setMinimumWidth(60)
        v3.addWidget(self.line_audio)

        v4 = QVBoxLayout()
        self.settings_card_preset_label = StrongBodyLabel("咏唱速度 (Preset)", self.card_settings)
        v4.addWidget(self.settings_card_preset_label)
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

        row1.addLayout(v1, 3) 
        row1.addLayout(v4, 2)
        set_layout.addLayout(row1)

        row1_b = QHBoxLayout()
        row1_b.setSpacing(12)
        row1_b.addLayout(v2, 1)
        row1_b.addLayout(v8, 1)
        row1_b.addLayout(v3, 1)
        set_layout.addLayout(row1_b)

        row2 = QHBoxLayout()
        row2.setSpacing(12)

        v6 = QVBoxLayout()
        h_loud = QHBoxLayout()
        self.settings_card_loudnorm_label = StrongBodyLabel("音量均一化术式 (Loudnorm)", self.card_settings)
        h_loud.addWidget(self.settings_card_loudnorm_label)
        h_loud.addStretch(1)
        self.combo_loudnorm = ComboBox(self.card_settings)
        self._populate_combo(self.combo_loudnorm, self.loudnorm_modes)
        self.combo_loudnorm.setMinimumWidth(200)
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
        """ 初始化操作卡片（保存模式、开始/暂停/停止按钮）。 """
        self.card_action = CardWidget(self)
        act_layout = QVBoxLayout(self.card_action)
        act_layout.setContentsMargins(20, 20, 20, 20)
        act_layout.setSpacing(15)

        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(6)
        
        h_mode_combo = QHBoxLayout()
        h_mode_combo.setContentsMargins(0, 0, 0, 0)
        self.combo_save_mode = ComboBox(self.card_action)
        self._populate_combo(self.combo_save_mode, self.save_modes)
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
        self.btn_export.setMinimumWidth(80)
        self.btn_export.clicked.connect(lambda: self.browse_folder(self.line_export))
        exp_layout.addWidget(self.line_export)
        exp_layout.addWidget(self.btn_export)
        mode_layout.addWidget(self.export_container)
        act_layout.addLayout(mode_layout)
        act_layout.addStretch(1)
        self.toggle_export_ui()

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
        self.btn_stop.setStyleSheet("PushButton { color: #D93652; font-weight: bold; border: 1px solid rgba(128, 128, 128, 0.25); border-radius: 6px; } PushButton:disabled { color: #CCCCCC; border: 1px solid rgba(128, 128, 128, 0.1); }")

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        act_layout.addLayout(btn_layout)

        self.left_column.addWidget(self.card_action)

    def _init_right_panel_content(self):
        """ 初始化右侧面板内容（源文件、文件列表）。 """
        self._init_source_card()
        self._init_file_list_card()
        self.sync_source_cache_card_height()
        self.sync_settings_selected_card_height()
        self.right_column.addStretch(1)

    def _init_source_card(self):
        """ 初始化源文件选择卡片。 """
        self.card_source = CardWidget(self)
        source_layout = QVBoxLayout(self.card_source)
        source_layout.setContentsMargins(18, 16, 18, 16)
        source_layout.setSpacing(10)
        self.source_card_title = StrongBodyLabel("素材次元 (Source)", self.card_source)
        source_layout.addWidget(self.source_card_title)

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
        """ 初始化文件列表卡片。 """
        self.card_selected_files = CardWidget(self)
        selected_layout = QVBoxLayout(self.card_selected_files)
        selected_layout.setContentsMargins(18, 16, 18, 16)
        selected_layout.setSpacing(8)

        selected_header = QHBoxLayout()
        self.file_list_card_title = StrongBodyLabel("次元空间 (List)", self.card_selected_files)
        selected_header.addWidget(self.file_list_card_title)
        selected_header.addStretch(1)
        
        self.btn_clear_list = PushButton(FluentIcon.DELETE, "归于虚无", self.card_selected_files)
        self.btn_clear_list.setMinimumWidth(120)
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
        """ 初始化状态栏（进度条）。 """
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
        """ 初始化日志显示区域。 """
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
        """ 初始化窗口底部区域（版权信息）。 """
        self.footer = BodyLabel("Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", self)
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer.setTextColor(QColor("#AAAAAA"), QColor("#AAAAAA"))
        self.footer.setOpenExternalLinks(True)
        self.main_layout.addWidget(self.footer)

    def _init_sub_interfaces(self):
        """ 初始化并添加所有子界面到导航面板。 """
        self.home_interface = QWidget()
        self.home_interface.setObjectName("homeInterface")
        self.home_interface.setLayout(self.main_layout)
        self.addSubInterface(self.home_interface, FluentIcon.VIDEO, tr("home.title"))
        
        self.info_interface = MediaInfoInterface(self)
        self.addSubInterface(self.info_interface, FluentIcon.INFO, tr("info.title"))
        
        self.profile_interface = ProfileInterface(self)
        self.addSubInterface(self.profile_interface, FluentIcon.PEOPLE, tr("profile.title"))

        self.credits_interface = CreditsInterface(self)
        self.addSubInterface(self.credits_interface, FluentIcon.HEART, tr("credits.title"))

    def showEvent(self, event):
        """ 窗口显示事件。 """
        super().showEvent(event)
        if not self._centered_once:
            self._centered_once = True
            QTimer.singleShot(0, self.center_on_screen)
            if getattr(self, 'is_first_run', False):
                QTimer.singleShot(600, self.show_welcome_wizard)
                self.is_first_run = False

        QTimer.singleShot(0, self.equalize_columns)
        QTimer.singleShot(0, self.sync_source_cache_card_height)
        QTimer.singleShot(0, self.sync_settings_selected_card_height)
        QTimer.singleShot(0, self.update_selected_zone_border)

    def resizeEvent(self, event):
        """ 窗口大小调整事件。 """
        super().resizeEvent(event)
        self.equalize_columns()
        self.sync_source_cache_card_height()
        self.sync_settings_selected_card_height()
        
    def equalize_columns(self):
        """ 使左右两栏等宽。 """
        if hasattr(self, "column_splitter") and self.column_splitter:
            total = max(self.column_splitter.width(), 2)
            half = total // 2
            self.column_splitter.setSizes([half, total - half])

    def sync_source_cache_card_height(self):
        """ 同步源文件卡片和缓存卡片的高度。 """
        if hasattr(self, "card_io") and hasattr(self, "card_source"):
            target = max(self.card_io.minimumSizeHint().height(), self.card_source.minimumSizeHint().height())
            self.card_io.setFixedHeight(target)
            self.card_source.setFixedHeight(target)

    def sync_settings_selected_card_height(self):
        """ 同步设置卡片和文件列表卡片的高度。 """
        if not (hasattr(self, "card_settings") and hasattr(self, "card_action") and hasattr(self, "card_selected_files")):
            return

        settings_min = self.card_settings.minimumSizeHint().height()
        action_min = self.card_action.minimumSizeHint().height()
        if settings_min <= 0 or action_min <= 0:
            return

        settings_pref = max(settings_min, self.card_settings.sizeHint().height())
        action_pref = max(action_min, self.card_action.sizeHint().height())
        
        current_save_mode_key = self.combo_save_mode.currentData()
        if current_save_mode_key != SAVE_MODE_SAVE_AS:
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

        if settings_h < settings_min or action_h < action_min:
            settings_h = settings_min
            action_h = action_min

        self.card_settings.setFixedHeight(settings_h)
        self.card_action.setFixedHeight(action_h)

    def center_on_screen(self):
        """ 将窗口居中显示。 """
        screen = self.windowHandle().screen() if self.windowHandle() else QGuiApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.availableGeometry()
        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(screen_geo.center())
        self.move(frame_geo.topLeft())

    def show_welcome_wizard(self):
        """ 显示欢迎向导。 """
        w = WelcomeWizard(self)
        w.exec()

    def load_settings_to_ui(self):
        """ 从配置文件加载设置到UI。 """
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
                    raw_save_mode = sect.get("save_mode", DEFAULT_SETTINGS["save_mode"])
                    data["save_mode"] = self.OLD_VALUE_MAP.get(raw_save_mode, raw_save_mode)
                    data["export_dir"] = sect.get("export_dir", DEFAULT_SETTINGS["export_dir"])
                
                for enc_name in self.encoder_settings:
                    if enc_name in config:
                        sect = config[enc_name]
                        defaults = ENCODER_CONFIGS[enc_name]
                        raw_loudnorm_mode = sect.get("loudnorm_mode", defaults["loudnorm_mode"])
                        self.encoder_settings[enc_name] = {
                            "vmaf": sect.get("vmaf", defaults["vmaf"]),
                            "audio_bitrate": sect.get("audio_bitrate", defaults["audio_bitrate"]),
                            "preset": sect.get("preset", defaults["preset"]),
                            "loudnorm": sect.get("loudnorm", defaults["loudnorm"]),
                            "loudnorm_mode": self.OLD_VALUE_MAP.get(raw_loudnorm_mode, raw_loudnorm_mode),
                            "nv_aq": sect.get("nv_aq", defaults["nv_aq"]),
                            "amf_offset": sect.get("amf_offset", defaults.get("amf_offset", "0"))
                        }
            except Exception:
                pass
        else:
            self.is_first_run = True
            self.save_settings_file(DEFAULT_SETTINGS, self.encoder_settings)
        
        enc_idx = 0
        if ENC_NVENC in data["encoder"]:
            enc_idx = 1
        elif ENC_AMF in data["encoder"]:
            enc_idx = 2
        
        self.last_encoder_name = self.combo_encoder.itemText(enc_idx)
        self.combo_encoder.setCurrentIndex(enc_idx)
        self.load_encoder_settings_to_ui(self.last_encoder_name)
        
        try:
            self.combo_theme.setCurrentIndex(THEMES.index(data["theme"]))
        except ValueError:
            self.combo_theme.setCurrentIndex(0)
        self.on_theme_changed(self.combo_theme.currentIndex())

        save_mode_index = self.combo_save_mode.findData(data["save_mode"])
        if save_mode_index > -1:
            self.combo_save_mode.setCurrentIndex(save_mode_index)
        self.line_export.setText(data.get("export_dir", ""))
        self.toggle_export_ui()

    def load_encoder_settings_to_ui(self, enc_name):
        """ 加载指定编码器的设置到UI。 """
        settings = self.encoder_settings.get(enc_name, ENCODER_CONFIGS.get(enc_name))
        if not settings: return

        self.block_signals_for_settings(True)
        
        self.line_vmaf.setText(settings["vmaf"])
        self.line_audio.setText(settings["audio_bitrate"])
        self.line_loudnorm.setText(settings["loudnorm"])
        
        loudnorm_mode_index = self.combo_loudnorm.findData(settings["loudnorm_mode"])
        if loudnorm_mode_index > -1:
            self.combo_loudnorm.setCurrentIndex(loudnorm_mode_index)

        self.sw_nv_aq.setChecked(settings["nv_aq"] == "True")
        self.spin_offset.setValue(int(settings.get("amf_offset", 0)))
        
        idx = self.combo_preset.findText(settings["preset"])
        if idx >= 0: self.combo_preset.setCurrentIndex(idx)
        else: self.combo_preset.setCurrentIndex(3)
        
        self.block_signals_for_settings(False)
        
        if ENC_NVENC in enc_name:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.nvidia"))
        elif ENC_AMF in enc_name:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.amd"))
        else:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.intel"))
        self.sw_nv_aq.setEnabled(True)

        is_hw = (ENC_AMF in enc_name) or (ENC_NVENC in enc_name) or (ENC_QSV in enc_name)
        self.lbl_offset.setEnabled(is_hw)
        self.spin_offset.setEnabled(is_hw)

    def block_signals_for_settings(self, block):
        """ 阻止或取消阻止设置控件的信号，以避免在加载设置时触发不必要的操作。 """
        widgets = [self.line_vmaf, self.line_audio, self.line_loudnorm, 
                   self.combo_loudnorm, self.sw_nv_aq, self.combo_preset, self.spin_offset]
        for w in widgets:
            w.blockSignals(block)

    def on_encoder_changed(self, index):
        """ 当用户更改编码器时调用，保存旧编码器的设置并加载新编码器的设置。 """
        new_encoder = self.combo_encoder.currentText()
        if new_encoder == self.last_encoder_name:
            return

        prev_settings = {
            "vmaf": self.line_vmaf.text(),
            "audio_bitrate": self.line_audio.text(),
            "preset": self.combo_preset.text(),
            "loudnorm": self.line_loudnorm.text(),
            "loudnorm_mode": self.combo_loudnorm.currentData(),
            "nv_aq": str(self.sw_nv_aq.isChecked()),
            "amf_offset": str(self.spin_offset.value())
        }
        self.encoder_settings[self.last_encoder_name].update(prev_settings)
        
        self.last_encoder_name = new_encoder
        self.load_encoder_settings_to_ui(new_encoder)
        
        self.auto_save_settings()

    def bind_auto_save_signals(self):
        """ 绑定所有设置控件的信号到自动保存槽函数。 """
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
        """ 自动保存当前设置。 """
        if self._auto_save_blocked:
            return
        self.save_current_settings(show_tip=False)

    def save_settings_file(self, settings_dict, encoder_settings=None):
        """ 将设置字典写入配置文件。 """
        config = configparser.ConfigParser()
        
        if os.path.exists(get_config_path()):
            config.read(get_config_path(), encoding='utf-8')

        if "Settings" not in config:
            config["Settings"] = {}

        for key, value in settings_dict.items():
            config["Settings"][key] = str(value)
        
        if encoder_settings:
            for enc_name, enc_conf in encoder_settings.items():
                if enc_name not in config:
                    config[enc_name] = {}
                for key, value in enc_conf.items():
                    config[enc_name][key] = str(value)
                
        with open(get_config_path(), 'w', encoding='utf-8') as f:
            config.write(f)

    def save_current_settings(self, show_tip=False):
        """ 保存当前UI上的所有设置到文件。 """
        curr_enc = self.combo_encoder.currentText()
        if curr_enc in self.encoder_settings:
            self.encoder_settings[curr_enc].update({
                "vmaf": self.line_vmaf.text(),
                "audio_bitrate": self.line_audio.text(),
                "preset": self.combo_preset.text(),
                "loudnorm": self.line_loudnorm.text(),
                "loudnorm_mode": self.combo_loudnorm.currentData(),
                "nv_aq": str(self.sw_nv_aq.isChecked()),
                "amf_offset": str(self.spin_offset.value())
            })

        settings = {
            "encoder": curr_enc,
            "theme": THEMES[self.combo_theme.currentIndex()],
            "save_mode": self.combo_save_mode.currentData(),
            "export_dir": self.line_export.text().strip(),
            "language": translator.current_lang
        }
        self.save_settings_file(settings, self.encoder_settings)
        if show_tip:
            orig_text = self.btn_save_conf.text()
            self.btn_save_conf.setText(tr("button.save.saved"))
            self.btn_save_conf.setStyleSheet("color: #FB7299; font-weight: bold;")
            
            QTimer.singleShot(1000, lambda: [self.btn_save_conf.setText(orig_text), self.btn_save_conf.setStyleSheet("")])
            
            InfoBar.success(tr("infobar.success.settings_saved.title"), tr("infobar.success.settings_saved.content"), parent=self, position=InfoBarPosition.TOP)

    def restore_defaults(self):
        """ 恢复所有设置为默认值。 """
        self._auto_save_blocked = True
        self.setUpdatesEnabled(False)
        
        widgets_to_block = [
            self.combo_encoder, self.combo_preset, self.combo_theme,
            self.combo_save_mode, self.combo_loudnorm, self.sw_nv_aq,
            self.line_vmaf, self.line_audio, self.line_loudnorm, self.line_export, self.spin_offset
        ]
        for w in widgets_to_block:
            w.blockSignals(True)
        
        self.encoder_settings = copy.deepcopy(ENCODER_CONFIGS)
        
        current_enc = self.combo_encoder.currentText()
        self.load_encoder_settings_to_ui(current_enc)
        
        self.combo_theme.setCurrentIndex(0)
        self.on_theme_changed(0)
        
        self.combo_save_mode.setCurrentIndex(self.combo_save_mode.findData(SAVE_MODE_OVERWRITE))
        self.line_export.clear()
        
        for w in widgets_to_block:
            w.blockSignals(False)

        self.toggle_export_ui()
        self.setUpdatesEnabled(True)
        self._auto_save_blocked = False

        self.save_current_settings(show_tip=False)
        
        orig_text = self.btn_reset_conf.text()
        self.btn_reset_conf.setText(tr("button.reset.restored"))
        self.btn_reset_conf.setStyleSheet("color: #FB7299; font-weight: bold;")
        QTimer.singleShot(1000, lambda: [self.btn_reset_conf.setText(orig_text), self.btn_reset_conf.setStyleSheet("")])
        
        InfoBar.info(tr("infobar.info.settings_reset.title"), tr("infobar.info.settings_reset.content"), parent=self, position=InfoBarPosition.TOP)
        
        QApplication.processEvents()

        if self.worker and self.worker.isRunning():
            InfoBar.warning(tr("infobar.warning.dependency_check_skipped.title"), tr("infobar.warning.dependency_check_skipped.content"), parent=self, position=InfoBarPosition.TOP)
        else:
            self.log(tr("log.recalibrating"), "info")
            QTimer.singleShot(200, self.check_dependencies)


    def on_theme_changed(self, index):
        """ 当用户在设置中更改主题时调用。 """
        if index == 0:
            setTheme(Theme.AUTO)
        elif index == 1:
            setTheme(Theme.LIGHT)
        elif index == 2:
            setTheme(Theme.DARK)
        setThemeColor('#FB7299')

        combos = [self.combo_theme]
        if hasattr(self, 'info_interface'): combos.append(self.info_interface.combo_theme)
        if hasattr(self, 'profile_interface'): combos.append(self.profile_interface.combo_theme)
        if hasattr(self, 'credits_interface'): combos.append(self.credits_interface.combo_theme)
        for c in combos:
            if c.currentIndex() != index:
                c.blockSignals(True)
                c.setCurrentIndex(index)
                c.blockSignals(False)
        
        QTimer.singleShot(50, self._update_card_style)
        
        QTimer.singleShot(0, self.update_selected_zone_border)
        QTimer.singleShot(120, self.update_selected_zone_border)

    def _update_card_style(self):
        """ 根据主题调整卡片样式 (解决浅色模式太白的问题)。 """
        cards = self.findChildren(CardWidget)
        
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
        """ 弹出文件夹选择对话框，并将选择的文件夹路径设置到指定的LineEdit。 """
        folder = QFileDialog.getExistingDirectory(self, tr("home.action_card.choose_button"))
        if folder:
            line_edit.setText(folder)

    def add_source_paths(self, paths):
        """ 将给定的路径（文件或文件夹）添加到待处理文件列表中。 """
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
        """ 处理拖放的文件路径。 """
        added = self.add_source_paths(paths)
        if added == 0:
            InfoBar.warning(tr("infobar.warning.no_new_files_dropped.title"), tr("infobar.warning.no_new_files_dropped.content"), parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.success(tr("infobar.success.files_added.title"), tr("infobar.success.drag_drop_added.content", count=added), parent=self, position=InfoBarPosition.TOP)

    def clear_selected_list_visual_state(self):
        """ 清除文件列表的视觉选择状态。 """
        if hasattr(self, "list_selected_files"):
            self.list_selected_files.clearSelection()
            self.list_selected_files.setCurrentRow(-1)

    def on_selected_zone_drag_active_changed(self, active):
        """ 当拖拽进入或离开文件列表区域时调用。 """
        self._drag_over_source_zone = bool(active)
        self.update_selected_zone_border()

    def update_selected_zone_border(self):
        """ 更新文件列表区域的边框样式，以响应拖拽状态。 """
        if not hasattr(self, "lbl_selected_placeholder") or not hasattr(self, "list_selected_files"):
            return

        show_hint_border = self._drag_over_source_zone or (len(self.selected_files) == 0)
        border_css = "2px dashed rgba(251, 114, 153, 0.90)" if show_hint_border else "1px solid transparent"
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
        """ 弹出文件夹选择对话框以选择源文件夹。 """
        folder = QFileDialog.getExistingDirectory(self, tr("home.source_card.folder_button"))
        if not folder:
            return
        added = self.add_source_paths([folder])
        if added == 0:
            InfoBar.warning(tr("infobar.warning.no_files_found.title"), tr("infobar.warning.no_files_found.content"), parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.success(tr("infobar.success.files_added.title"), tr("infobar.success.files_added.content", count=added), parent=self, position=InfoBarPosition.TOP)

    def browse_files(self):
        """ 弹出文件选择对话框以选择源文件。 """
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("home.source_card.file_button"),
            "",
            "Video Files (*.mkv *.mp4 *.avi *.mov *.wmv *.flv *.webm *.m4v *.ts);;All Files (*.*)"
        )
        if files:
            self.add_source_paths(files)

    def open_file_location(self, item):
        """ 在文件浏览器中打开所选文件的位置。 """
        if not item: return
        row = self.list_selected_files.row(item)
        if 0 <= row < len(self.selected_files):
            path = self.selected_files[row]
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            except Exception:
                pass

    def process_duration_queue(self):
        """ 处理等待中的视频时长分析任务。 """
        MAX_CONCURRENT = MAX_DURATION_WORKERS
        while len(self.active_dur_workers) < MAX_CONCURRENT and self.pending_dur_tasks:
            path = self.pending_dur_tasks.pop(0)
            self.start_duration_worker(path)

    def start_duration_worker(self, path):
        """ 启动一个新的线程来分析视频时长。 """
        worker = DurationWorker(path)
        worker.result.connect(self.update_file_duration_label)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self.on_duration_worker_finished(path))
        self.active_dur_workers[path] = worker
        worker.start()
        self.set_duration_text_in_list(path, "...")

    def on_duration_worker_finished(self, path):
        """ 视频时长分析线程完成时的清理工作。 """
        self.active_dur_workers.pop(path, None)
        self.process_duration_queue()

    def get_file_duration(self, path):
        """ 请求获取指定文件的视频时长。 """
        if path in self.pending_dur_tasks: return
        
        self.pending_dur_tasks.append(path)
        self.process_duration_queue()

    def update_file_duration_label(self, path, duration_str, duration_sec, meta=None):
        """ 更新文件列表中的视频时长标签。 """
        self.cached_durations[path] = (duration_str, duration_sec)
        if meta:
            self.file_metadata[path] = {**meta, "duration": duration_sec}

        self.set_duration_text_in_list(path, duration_str)
        
        if path not in self.cached_thumbnails:
            self.get_file_thumbnail(path, duration_sec)

    def process_thumbnail_queue(self):
        """ 处理等待中的视频缩略图生成任务。 """
        MAX_CONCURRENT = MAX_THUMBNAIL_WORKERS
        while len(self.active_thumb_workers) < MAX_CONCURRENT and self.pending_thumb_tasks:
            path, duration = self.pending_thumb_tasks.pop(0)
            self.start_thumbnail_worker(path, duration)

    def start_thumbnail_worker(self, path, duration_sec):
        """ 启动一个新的线程来生成视频缩略图。 """
        worker = ThumbnailWorker(path, duration_sec)
        worker.result.connect(self.update_file_thumbnail)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self.on_thumbnail_worker_finished(path))
        self.active_thumb_workers[path] = worker
        worker.start()

    def on_thumbnail_worker_finished(self, path):
        """ 视频缩略图生成线程完成时的清理工作。 """
        self.active_thumb_workers.pop(path, None)
        self.process_thumbnail_queue()

    def get_file_thumbnail(self, path, duration_sec):
        """ 请求获取指定文件的视频缩略图。 """
        if path in self.active_thumb_workers: return
        for p, _ in self.pending_thumb_tasks:
            if p == path: return
            
        self.pending_thumb_tasks.append((path, duration_sec))
        self.process_thumbnail_queue()

    def update_file_thumbnail(self, path, image):
        """ 更新文件列表中的视频缩略图。 """
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            
            rounded = QPixmap(pixmap.size())
            rounded.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter_path = QPainterPath()
            painter_path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 6, 6)
            painter.setClipPath(painter_path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            if path in self.cached_thumbnails:
                self.cached_thumbnails.move_to_end(path)
            self.cached_thumbnails[path] = QIcon(rounded)
            
            if len(self.cached_thumbnails) > self.MAX_THUMBNAIL_CACHE:
                self.cached_thumbnails.popitem(last=False)

            item = self.path_to_item.get(path)
            if item:
                widget = self.list_selected_files.itemWidget(item)
                if widget:
                    icon_w = widget.findChild(IconWidget, "video_icon")
                    if icon_w:
                        icon_w.setIcon(self.cached_thumbnails[path])

    def clear_all_selected_files(self):
        """ 清空所有已选择的文件。 """
        if not self.selected_files:
            return
        
        if self.worker and self.worker.isRunning():
            InfoBar.warning(tr("infobar.warning.task_running.title"), tr("infobar.warning.task_running.content"), parent=self, position=InfoBarPosition.TOP)
            return

        title = tr("dialog.clear_list.title")
        content = tr("dialog.clear_list.content")
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText(tr("dialog.clear_list.yes_button"))
        dialog.cancelButton.setText(tr("dialog.clear_list.cancel_button"))
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
        self.log(tr("log.list_cleared"), "info")

    def set_duration_text_in_list(self, path, text):
        """ 在文件列表中设置指定文件的时长文本。 """
        for i in range(self.list_selected_files.count()):
            if i < len(self.selected_files) and self.selected_files[i] == path:
                item = self.list_selected_files.item(i)
                widget = self.list_selected_files.itemWidget(item)
                if widget:
                    btn = widget.findChild(ClickableBodyLabel, "btn_duration")
                    if btn:
                        btn.setText(text)
                        if text not in ["...", tr("list.item.duration_button")]:
                            btn.setEnabled(False)
                            btn.setCursor(Qt.CursorShape.ArrowCursor)

    def remove_selected_file(self, file_path):
        """ 从文件列表中移除指定的文件。 """
        self.selected_files = [p for p in self.selected_files if p != file_path]
        
        if file_path in self.path_to_item:
            item = self.path_to_item.pop(file_path)
            row = self.list_selected_files.row(item)
            taken_item = self.list_selected_files.takeItem(row)
            del taken_item

        self.cached_durations.pop(file_path, None)
        self.cached_thumbnails.pop(file_path, None)
        self.file_metadata.pop(file_path, None)
        
        if file_path in self.pending_dur_tasks:
            self.pending_dur_tasks.remove(file_path)
        self.pending_thumb_tasks = [t for t in self.pending_thumb_tasks if t[0] != file_path]
        
        self.update_selected_count()

    def format_file_size(self, size_bytes):
        """ 格式化文件大小为可读字符串。 """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def update_selected_count(self):
        """ 更新文件列表中的文件数量显示，并切换占位符和列表的可见性。 """
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

        for p in self.selected_files:
            if p in self.path_to_item: continue

            item = QListWidgetItem(self.list_selected_files)
            item.setSizeHint(QSize(0, 60))
            self.path_to_item[p] = item

            item_widget = QWidget(self.list_selected_files)
            item_widget.setObjectName("item_tile")
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

            btn_remove = ClickableBodyLabel(tr("list.item.remove_button"), row)
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setStyleSheet("font-weight: 700; background: transparent;")
            btn_remove.setTextColor(QColor("#D93652"), QColor("#FF8FA1"))
            btn_remove.clicked.connect(lambda path=p: self.remove_selected_file(path))

            dur_text = tr("list.item.duration_button")
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
        """ 更新指定文件的进度条。 """
        item = self.path_to_item.get(filepath)
        if not item: return
        widget = self.list_selected_files.itemWidget(item)
        if widget:
            pbar = widget.findChild(ProgressBar, "pbar")
            if pbar:
                if pbar.isHidden(): pbar.show()
                pbar.setValue(percent)

    def update_file_stats(self, filepath, speed, eta):
        """ 更新指定文件的统计信息（速度和剩余时间）。 """
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
        """ 更新指定文件的状态图标。 """
        item = self.path_to_item.get(filepath)
        if not item: return
        widget = self.list_selected_files.itemWidget(item)
        if widget:
            icon_w = widget.findChild(IconWidget, "status_icon")
            pbar = widget.findChild(ProgressBar, "pbar")
            lbl_stats = widget.findChild(BodyLabel, "lbl_stats")
            if icon_w:
                if status == "processing":
                    icon_w.setIcon(FluentIcon.SYNC)
                    if lbl_stats: lbl_stats.setStyleSheet("font-size: 11px; font-weight: bold; color: #FB7299;")
                elif status == "success":
                    icon_w.setIcon(FluentIcon.ACCEPT)
                    if pbar: pbar.hide()
                    if lbl_stats: 
                        lbl_stats.setStyleSheet("font-size: 11px; font-weight: bold; color: #55E555;")
                        lbl_stats.show()
                elif status == "error":
                    icon_w.setIcon(FluentIcon.CANCEL)
                    if pbar: pbar.hide()
                    if lbl_stats: lbl_stats.hide()

    def toggle_export_ui(self):
        """ 根据保存模式显示或隐藏导出路径UI。 """
        current_save_mode_key = self.combo_save_mode.currentData()
        is_save_as = (current_save_mode_key == SAVE_MODE_SAVE_AS)
        self.export_container.setVisible(is_save_as)
        self.export_container.updateGeometry()
        if self.card_action.layout():
            self.card_action.layout().activate()
        self.card_action.updateGeometry()
        self.sync_settings_selected_card_height()
        QTimer.singleShot(0, self.sync_settings_selected_card_height)

    def log(self, msg, level="info"):
        """ 将日志消息添加到队列中以便稍后处理。 """
        # 使用 tryLock(timeout) 防止在 log 本身发生死锁
        # 如果 50ms 内拿不到锁，直接放弃这条日志，防止卡死主线程
        if not self.log_mutex.tryLock(50):
            print(f"Warning: Log mutex locked, dropping message: {msg}")
            return
            
        try:
            self.log_queue.append((time.time(), msg, level))
        finally:
            self.log_mutex.unlock()

    def process_log_queue(self):
        """ 定期处理日志队列并将消息显示在日志区域。 """
        # 使用 tryLock 防止死锁
        if not self.log_mutex.tryLock():
            return

        batch = []
        try:
            if self.log_queue:
                if len(self.log_queue) > LOG_MAX_BLOCKS // 2:
                    self.log_queue = self.log_queue[-(LOG_MAX_BLOCKS // 2):]
                batch = self.log_queue[:]
                self.log_queue.clear()
        except Exception as e:
            print(f"Log queue error: {e}")
        finally:
            self.log_mutex.unlock()

        if not batch:
            return

        try:
            # 将 UI 更新逻辑放在 try 块中，防止报错导致循环
            is_dark = isDarkTheme()
            colors = {
                "dark": { "ts": "#707070", "info": "#DCDCDC", "success": "#A6E22E", "warning": "#E6DB74", "error": "#FF5277" },
                "light": { "ts": "#888888", "info": "#333333", "success": "#228B22", "warning": "#B8860B", "error": "#D93652" }
            }
            
            theme = "dark" if is_dark else "light"
            c = colors[theme]
            ts_color = c["ts"]
            
            icons = { "info": "💡", "success": "✨", "warning": "⚠️", "error": "💢" }

            html_buffer = []
            for t, msg, level in batch:
                timestamp = time.strftime('%H:%M:%S', time.localtime(t))
                msg_color = c.get(level, c["info"])
                icon = icons.get(level, "•")
                msg = str(msg).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")
                html = (
                    f'<span style="color:{ts_color}; font-family: \'Cascadia Code\', \'Consolas\', monospace; font-size: 11px;">[{timestamp}]</span>&nbsp;'
                    f'<span style="color:{msg_color}; font-weight: {"600" if level in ["error", "warning", "success"] else "normal"};">'
                    f'{icon} {msg}</span><br>'
                )
                html_buffer.append(html)
            
            self.text_log.setUpdatesEnabled(False)
            cursor = self.text_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertHtml("".join(html_buffer))
            self.text_log.setTextCursor(cursor)
            self.text_log.ensureCursorVisible()
            
            if self.text_log.document().blockCount() > LOG_MAX_BLOCKS:
                self.text_log.clear()
                self.text_log.append(f'<div style="color:{c["info"]}; font-family: \'Cascadia Code\'; font-size: 11px;">>>> 历史因果已抹除，日志重新开始记录。</div>')

            self.text_log.setUpdatesEnabled(True)
        except Exception as e:
            print(f"Log UI update error: {e}")

    def clear_cache_files(self):
        """ 清除ab-av1生成的临时缓存文件。 """
        cache_path = self.line_cache.text().strip() or get_default_cache_dir()
        if not os.path.exists(cache_path):
            InfoBar.warning(tr("infobar.warning.invalid_cache_path.title"), tr("infobar.warning.invalid_cache_path.content"), parent=self, position=InfoBarPosition.TOP)
            return
        
        title = tr("dialog.clear_cache.title")
        content = tr("dialog.clear_cache.content", path=cache_path)
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText(tr("dialog.clear_cache.yes_button"))
        dialog.cancelButton.setText(tr("dialog.clear_cache.cancel_button"))
        
        if not dialog.exec():
            return

        try:
            count = 0
            for f in os.listdir(cache_path):
                if f.endswith(".temp.mkv"):
                    os.remove(os.path.join(cache_path, f))
                    count += 1
            InfoBar.success(tr("infobar.success.cache_cleared.title"), tr("infobar.success.cache_cleared.content", count=count), parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error(tr("infobar.error.cache_clear_failed.title"), str(e), parent=self, position=InfoBarPosition.TOP)

    def start_task(self):
        """ 开始编码任务。 """
        if not self.selected_files:
            InfoBar.warning(title=tr("infobar.warning.no_files_selected.title"), content=tr("infobar.warning.no_files_selected.content"), orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, parent=self)
            return

        save_mode = self.combo_save_mode.currentData()
        export_dir = self.line_export.text().strip()
        if save_mode == SAVE_MODE_SAVE_AS and not export_dir:
            InfoBar.warning(tr("infobar.warning.no_export_dir.title"), tr("infobar.warning.no_export_dir.content"), parent=self, position=InfoBarPosition.TOP)
            return

        try:
            vmaf_val = float(self.line_vmaf.text())
        except ValueError:
            InfoBar.error(tr("infobar.error.vmaf_not_number.title"), tr("infobar.error.vmaf_not_number.content"), parent=self, position=InfoBarPosition.TOP)
            return

        config = {
            'selected_files': self.selected_files[:],
            'encoder': self.combo_encoder.currentText(),
            'export_dir': export_dir,
            'save_mode': self.combo_save_mode.currentData(),
            'cache_dir': self.line_cache.text().strip() or get_default_cache_dir(),
            'preset': self.combo_preset.text(),
            'vmaf': vmaf_val,
            'metadata': self.file_metadata.copy(),
            'audio_bitrate': self.line_audio.text(),
            'loudnorm': self.line_loudnorm.text(),
            'nv_aq': self.sw_nv_aq.isChecked(),
            'amf_offset': self.spin_offset.value(),
            'loudnorm_mode': self.combo_loudnorm.currentData()
        }
        os.makedirs(config['cache_dir'], exist_ok=True)

        self.worker = EncoderWorker(config)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_total_signal.connect(self.pbar_total.setValue)
        self.worker.progress_current_signal.connect(self.pbar_current.setValue)
        self.worker.file_progress_signal.connect(self.update_file_progress)
        self.worker.file_stats_signal.connect(self.update_file_stats)
        self.worker.file_status_signal.connect(self.update_file_status)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.ask_error_decision.connect(self.on_worker_error)
        self.worker.finished.connect(self.worker.deleteLater)
        
        self.worker.start()
        
        self.btn_start.setEnabled(False)
        self.btn_clear_list.setEnabled(False)
        self.btn_start.setText(tr("button.start.in_progress"))
        self.btn_pause.setEnabled(True)
        self.combo_encoder.setEnabled(False)
        self.combo_save_mode.setEnabled(False)
        self.btn_pause.setText(tr("home.action_card.pause_button"))
        self.btn_stop.setEnabled(True)
        self.pbar_total.setValue(0)
        self.pbar_current.setValue(0)

    def on_worker_error(self, title, content):
        """ 当工作线程遇到错误时，弹出一个对话框让用户决定是跳过还是停止。 """
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText(tr("dialog.error.skip_button"))
        dialog.cancelButton.setText(tr("dialog.error.stop_button"))
        
        self.error_countdown = 30
        
        def update_timer():
            self.error_countdown -= 1
            dialog.titleLabel.setText(f"{title} ({self.error_countdown}s 后自动跳过)")
            if self.error_countdown <= 0:
                timer.stop()
                dialog.accept()
        
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
        """ 停止当前正在运行的编码任务。 """
        if self.worker:
            self.log(tr("log.task_stop_request"), "error")
            self.worker.stop()
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)

    def pause_task(self):
        """ 暂停或恢复当前正在运行的编码任务。 """
        if self.worker:
            if self.worker.is_paused:
                self.worker.set_paused(False)
                self.btn_pause.setText(tr("home.action_card.pause_button"))
                self.log(tr("log.task_resume"), "info")
            else:
                self.worker.set_paused(True)
                self.btn_pause.setText(tr("home.action_card.pause_button"))
                self.log(tr("log.task_pause"), "info")

    def on_finished(self):
        """ 当编码任务完成时调用，恢复UI状态。 """
        self.btn_start.setEnabled(True)
        self.btn_clear_list.setEnabled(True)
        self.btn_start.setText(tr("home.action_card.start_button"))
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.combo_encoder.setEnabled(True)
        self.combo_save_mode.setEnabled(True)
        self.worker = None

    def apply_encoder_availability(self, has_qsv, has_nvenc, has_amf):
        """ 根据可用的编码器更新编码器选择下拉框。 """
        mapping = [(ENC_QSV, 0, has_qsv), (ENC_NVENC, 1, has_nvenc), (ENC_AMF, 2, has_amf)]

        for _, idx, enabled in mapping:
            self.combo_encoder.setItemEnabled(idx, enabled)

        available = [(name, idx) for name, idx, enabled in mapping if enabled]
        if not available:
            self.combo_encoder.setEnabled(False)
            return None

        if not (self.worker and self.worker.isRunning()):
            self.combo_encoder.setEnabled(True)

        current = self.combo_encoder.currentText()
        valid_names = {name for name, _ in available}
        if current not in valid_names:
            self.combo_encoder.setCurrentIndex(available[0][1])
            return available[0][0]

        return None

    def check_dependencies(self):
        """ 检查所需的外部依赖（如ffmpeg）是否存在。 """
        if self.dep_worker:
            try:
                if self.dep_worker.isRunning():
                    self.log(tr("infobar.warning.duplicate_dependency_check.content"), "warning")
                    return
            except RuntimeError:
                self.dep_worker = None

        self.log(tr("log.dependency_check_start"), "info")
        self.dep_worker = DependencyWorker()
        self.dep_worker.log_signal.connect(self.log)
        self.dep_worker.missing_signal.connect(self.on_dependency_missing)
        self.dep_worker.finished.connect(self.dep_worker.deleteLater)
        self.dep_worker.finished.connect(self.on_dependency_worker_finished)
        self.dep_worker.result_signal.connect(self.on_dependency_check_finished)
        self.dep_worker.start()

    def on_dependency_worker_finished(self):
        """ 依赖检查线程完成时的清理工作。 """
        self.dep_worker = None

    def on_dependency_missing(self, missing):
        """ 当检测到有依赖缺失时调用，弹出一个对话框提示用户。 """
        title = tr("dialog.dependency_missing.title")
        content = tr("dialog.dependency_missing.content", missing_files=chr(10).join(missing))
        
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText(tr("dialog.dependency_missing.yes_button"))
        dialog.cancelButton.setText(tr("dialog.dependency_missing.cancel_button"))
        
        if dialog.exec():
            QDesktopServices.openUrl(QUrl("https://github.com/LingMoe404/MagicalGirlWorkshop/blob/main/docs/FAQ.md"))
        
        self.btn_start.setEnabled(False)
        self.btn_start.setText(tr("button.start.missing_components"))
        self.apply_encoder_availability(False, False, False)
        self.log(tr("log.fatal_error_component_missing"), "error")

    def on_dependency_check_finished(self, has_qsv, has_nvenc, has_amf):
        """ 当依赖检查完成时调用，更新编码器可用性并记录日志。 """
        switched_to = self.apply_encoder_availability(has_qsv, has_nvenc, has_amf)

        if not has_qsv and not has_nvenc and not has_amf:
            self.log(tr("log.dependency_check_finished.fail"), "error")
            InfoBar.warning(tr("infobar.warning.hardware_unsupported.title"), tr("infobar.warning.hardware_unsupported.content"), parent=self, position=InfoBarPosition.TOP)
        else:
            msg = tr("log.dependency_check_finished.success")
            if has_qsv: msg += f" [{ENC_QSV}]"
            if has_nvenc: msg += f" [{ENC_NVENC}]"
            if has_amf: msg += f" [{ENC_AMF}]"
            self.log(msg + " (Ready)", "success")
            if switched_to:
                self.log(tr("log.autoselect_encoder", encoder=switched_to), "info")

    def add_source_paths_from_info(self, path):
        """ 从“真理之眼”界面添加文件到主列表。 """
        added = self.add_source_paths([path])
        if added > 0:
            self.switchTo(self.home_interface)
            InfoBar.success(tr("infobar.success.synced.title"), tr("infobar.success.synced.content"), parent=self, position=InfoBarPosition.TOP)

    def closeEvent(self, event):
        """ 窗口关闭事件，确保所有后台线程都已停止。 """
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(500)
        
        self.pending_dur_tasks.clear()
        self.pending_thumb_tasks.clear()
        
        for worker in self.active_dur_workers.values():
            try: worker.stop()
            except RuntimeError: pass
            
        for worker in self.active_thumb_workers.values():
            try: worker.stop()
            except RuntimeError: pass

        self.info_interface.stop_worker()
        super().closeEvent(event)
