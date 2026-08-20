import copy
import os
import random
import subprocess

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# 引入 Fluent Widgets (Win11 风格组件)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    MessageBoxBase,
    MessageDialog,
    StrongBodyLabel,
    SubtitleLabel,
    Theme,
    isDarkTheme,
    setTheme,
    setThemeColor,
)

from config import (
    DEFAULT_SETTINGS,
    DEPENDENCY_CHECK_DELAY,
    ENC_AMF,
    ENC_NVENC,
    ENC_QSV,
    ENCODER_CONFIGS,
    LOG_MAX_BLOCKS,
    LOG_UPDATE_INTERVAL,
    LOUDNORM_MODE_ALWAYS,
    LOUDNORM_MODE_AUTO,
    LOUDNORM_MODE_DISABLE,
    MIN_WINDOW_SIZE,
    NAV_EXPAND_WIDTH,
    SAVE_MODE_OVERWRITE,
    SAVE_MODE_REMAIN,
    SAVE_MODE_SAVE_AS,
    THEMES,
)
from i18n.translator import tr, translator
from ui.config_manager import ConfigManager
from utils import get_default_cache_dir, resource_path
from workers import (
    DependencyWorker,
    TranscodeController,
)
from workers.transcode_paths import cleanup_stale_sessions


# --- 初次运行欢迎向导 ---
class WelcomeWizard(MessageBoxBase):
    """初次运行时显示的欢迎和设置向导。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 Key 而非直接翻译，以便后续动态切换语言
        self.pages_config = [
            ("welcome.wizard.page1.title", "welcome.wizard.page1.content"),
            ("welcome.wizard.page2.title", "welcome.wizard.page2.content"),
            ("welcome.wizard.page3.title", "welcome.wizard.page3.content"),
            ("welcome.wizard.page4.title", "welcome.wizard.page4.content"),
            ("welcome.wizard.page5.title", "welcome.wizard.page5.content"),
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
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.on_wizard_language_changed)

        self.view = QStackedWidget(self)
        self.page_labels = []  # 存储 Label 引用用于重翻译

        self.init_pages()

        # 调整布局和尺寸
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.lang_combo)
        self.viewLayout.addWidget(self.view)
        self.widget.setFixedSize(480, 400)  # 稍微调高一点给下拉框留空间

        self.current_idx = 0
        self.view.setCurrentIndex(0)
        self.retranslate_wizard()

        # 重新绑定信号 (接管默认的 accept/reject 行为)
        self.yesButton.clicked.disconnect()
        self.yesButton.clicked.connect(self.next_page)
        self.cancelButton.clicked.disconnect()
        self.cancelButton.clicked.connect(self.reject)

    def init_pages(self):
        """初始化所有向导页面。"""
        for i, (t_key, c_key) in enumerate(self.pages_config):
            page = QWidget()
            vbox = QVBoxLayout(page)
            vbox.setContentsMargins(0, 10, 0, 0)
            vbox.setSpacing(10)

            lbl_title = StrongBodyLabel("", page)
            lbl_content = BodyLabel("", page)
            lbl_content.setWordWrap(True)
            text_color = "#666666" if not isDarkTheme() else "#CCCCCC"
            lbl_content.setStyleSheet(
                f"color: {text_color}; font-size: 13px; line-height: 1.5;"
            )

            vbox.addWidget(lbl_title)
            vbox.addWidget(lbl_content)

            vbox.addStretch(1)
            self.view.addWidget(page)
            self.page_labels.append((lbl_title, lbl_content))

    def on_wizard_language_changed(self, index):
        """当向导中的语言下拉框改变时。"""
        lang_code = self.lang_combo.itemData(index)
        if lang_code == translator.current_lang:
            return

        translator.set_language(lang_code)
        self.retranslate_wizard()

        # 同步更新主界面 (如果父窗口是 MainWindow)
        main_win = self.parent()
        if main_win and hasattr(main_win, "retranslate_ui"):
            main_win.retranslate_ui()
            # 同步主界面的下拉框索引
            if hasattr(main_win, "combo_lang"):
                main_win.combo_lang.blockSignals(True)
                main_win.combo_lang.setCurrentIndex(index)
                main_win.combo_lang.blockSignals(False)

    def retranslate_wizard(self):
        """刷新向导界面的所有文本。"""
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
        """切换到下一个向导页面（无限循环）。"""
        self.current_idx = (self.current_idx + 1) % len(self.pages_config)
        self.view.setCurrentIndex(self.current_idx)


# --- 主窗口 (Win11 风格) ---
class MainWindow(FluentWindow):
    """应用程序的主窗口，集成了所有UI组件和核心逻辑。"""

    OLD_VALUE_MAP = {  # noqa: RUF012
        "开辟新世界 (Save As)": SAVE_MODE_SAVE_AS,
        "元素覆写 (Overwrite)": SAVE_MODE_OVERWRITE,
        "元素保留 (Remain)": SAVE_MODE_REMAIN,
        "全部启用 (Always)": LOUDNORM_MODE_ALWAYS,
        "全部禁用 (Disable)": LOUDNORM_MODE_DISABLE,
        "仅立体声/单声道 (Stereo/Mono Only)": LOUDNORM_MODE_AUTO,
    }

    def __init__(self, config_manager=None, transcode_controller=None):
        super().__init__()

        self._base_min_size = MIN_WINDOW_SIZE
        self._centered_once = False

        self.save_modes = [SAVE_MODE_SAVE_AS, SAVE_MODE_OVERWRITE, SAVE_MODE_REMAIN]
        self.loudnorm_modes = [
            LOUDNORM_MODE_AUTO,
            LOUDNORM_MODE_ALWAYS,
            LOUDNORM_MODE_DISABLE,
        ]
        self.transcode_modes = ["auto", "manual"]

        # [Fix] 缩减侧边栏展开宽度，避免留白过多，视觉更紧凑
        self.navigationInterface.setExpandWidth(NAV_EXPAND_WIDTH)

        # 启用 Mica 效果 (Win11 特有半透明背景)
        self.windowEffect.setMicaEffect(self.winId())
        setThemeColor("#FB7299")  # Bilibili Pink / 魔法少女粉

        # 设置窗口图标 (任务栏和左上角)
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            icon = QIcon()
            # 使用 addFile 加载多分辨率图标，配合 AppUserModelID 解决模糊问题
            icon.addFile(icon_path)
            self.setWindowIcon(icon)

        # 核心变量
        # 转码生命周期由 TranscodeController 门面管理：内部创建/清理
        # EncodingCoordinator，start_task 只做 UI 校验 + config 构建 + controller.start。
        # 不直接持有 self.worker，避免两套转码生命周期并存。
        self._auto_save_blocked = False  # 自动保存状态标志
        self.dep_worker = None  # 依赖检查工作线程
        # 转码控制器：信号接线在 init_ui 之后（依赖 pbar/文件列表等控件）
        self.transcode_controller = transcode_controller or TranscodeController()

        # 日志刷新定时器：由 MainWindow 持有，调用 process_log_queue 转发到 LogManager.flush
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.process_log_queue)
        self.log_timer.start(LOG_UPDATE_INTERVAL)

        # 编码器配置管理
        self.last_encoder_name = "Intel QSV"
        self.encoder_settings = copy.deepcopy(ENCODER_CONFIGS)
        self.config_manager = config_manager or ConfigManager()

        # 初始化 UI
        self.init_ui()
        self.retranslate_ui()
        self.apply_min_window_size()
        self.load_settings_to_ui()
        self.auto_clean_cache_startup()
        self.combo_encoder.currentIndexChanged.connect(self.on_encoder_changed)
        self.bind_auto_save_signals()

        # 连接转码控制器的全部信号（依赖 init_ui 创建的控件）
        self._connect_transcode_signals()

        # 连接所有页面的主题切换信号
        for interface in [
            self.info_interface,
            self.profile_interface,
            self.credits_interface,
            self.settings_interface,
        ]:
            interface.combo_theme.currentIndexChanged.connect(self.on_theme_changed)

        # 连接所有页面的语言切换信号，并同步初始状态
        for interface in [
            self.info_interface,
            self.profile_interface,
            self.credits_interface,
            self.settings_interface,
        ]:
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
        """使用可翻译的文本填充组合框，并将原始键存储在userData中。"""
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
            "auto": "home.action_card.concurrency.auto",
            "manual": "home.action_card.concurrency.manual",
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
        """根据当前语言重新翻译整个界面的文本。"""
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
        self.settings_card_loudnorm_label.setText(
            tr("home.settings_card.loudnorm.label")
        )
        self.sw_nv_aq.setOnText(tr("home.settings_card.nv_aq.on"))
        self.sw_nv_aq.setOffText(tr("home.settings_card.nv_aq.off"))
        self.lbl_color_mode.setText(
            tr("home.settings_card.color_mode.label") or "色彩幻境 (Color Mode)"
        )

        # 刷新色彩幻境下拉菜单的翻译
        self.combo_color.blockSignals(True)
        curr_color = self.combo_color.currentData() or "Auto"
        self.combo_color.clear()
        self.combo_color.addItem(
            tr("home.settings_card.color_mode.auto") or "自动保留 HDR (Auto)",
            userData="Auto",
        )
        self.combo_color.addItem(
            tr("home.settings_card.color_mode.tonemap") or "色彩同调 SDR (Tone Map)",
            userData="ToneMap",
        )
        self.combo_color.addItem(
            tr("home.settings_card.color_mode.sdr") or "强制常规 SDR (Force SDR)",
            userData="SDR",
        )
        idx_c = self.combo_color.findData(curr_color)
        if idx_c >= 0:
            self.combo_color.setCurrentIndex(idx_c)
        self.combo_color.blockSignals(False)

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

        # 模版快捷键翻译
        self.lbl_presets_title.setText(tr("home.settings_card.presets_title"))
        self.btn_preset_light.setText(tr("home.settings_card.preset_light"))
        self.btn_preset_balanced.setText(tr("home.settings_card.preset_balanced"))
        self.btn_preset_heavenly.setText(tr("home.settings_card.preset_heavenly"))

        # 操作卡片
        self._populate_combo(self.combo_save_mode, self.save_modes)
        self.lbl_transcode_mode.setText(tr("home.action_card.concurrency.mode_label"))
        self.lbl_transcode_count.setText(tr("home.action_card.concurrency.count_label"))
        self._populate_combo(
            self.combo_transcode_mode,
            self.transcode_modes,
        )
        if not self.transcode_controller.is_running():
            self.lbl_concurrency_status.setText(tr("home.action_card.concurrency.idle"))
        self.line_export.setPlaceholderText(
            tr("home.action_card.export_path_placeholder")
        )
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
        self.navigationInterface.widget("settingsInterface").setText(
            tr("settings.title")
        )

        self.info_interface.retranslate_ui()
        self.profile_interface.retranslate_ui()
        self.credits_interface.retranslate_ui()
        self.settings_interface.retranslate_ui()

        self.footer.setText(tr("app.designed_by"))
        self.update()

    def on_language_changed(self, index):
        """当用户在设置中更改语言时调用。"""
        # 同步所有界面的语言下拉框状态，防止递归触发
        combos = [self.combo_lang]
        if hasattr(self, "info_interface"):
            combos.append(self.info_interface.combo_lang)
        if hasattr(self, "profile_interface"):
            combos.append(self.profile_interface.combo_lang)
        if hasattr(self, "credits_interface"):
            combos.append(self.credits_interface.combo_lang)
        if hasattr(self, "settings_interface"):
            combos.append(self.settings_interface.combo_lang)

        for c in combos:
            if c.currentIndex() != index:
                c.blockSignals(True)
                c.setCurrentIndex(index)
                c.blockSignals(False)

        lang_code = self.combo_lang.itemData(index)
        translator.set_language(lang_code)

        dialog = MessageDialog(
            tr("dialog.language_change.title"),
            tr("dialog.language_change.content"),
            self,
        )
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
        """初始化主窗口的所有UI组件（薄方法，委托给主页布局构建器）。"""
        from ui.home_ui_builder import build_home_ui

        build_home_ui(self)

    def _get_thread_limit(self):
        """读取当前线程限制；global_settings['thread_limit'] 缺失或非法时回退 4。"""
        try:
            return int(self.global_settings.get("thread_limit", "4"))
        except (TypeError, ValueError):
            return 4

    def _on_file_stats_text(self, speed, eta):
        """状态文本回调：恢复旧的 ab-av1/探测 分支的状态栏行为。"""
        if "ab-av1" in speed or "探测" in speed:
            self.lbl_current.setText(f"✨ 寻觅最优魔法参数 ({speed} · {eta}):")
        else:
            self.lbl_current.setText(tr("home.status_bar.current_label"))

    def _on_file_removed(self, file_path):
        """文件从列表中移除时的回调（当前为宿主预留，暂无额外行为）。"""

    def showEvent(self, event):
        """窗口显示事件。"""
        super().showEvent(event)
        if not self._centered_once:
            self._centered_once = True
            QTimer.singleShot(0, self.center_on_screen)
            if getattr(self, "is_first_run", False):
                QTimer.singleShot(600, self.show_welcome_wizard)
                self.is_first_run = False

        QTimer.singleShot(0, self.equalize_columns)
        QTimer.singleShot(0, self.sync_source_cache_card_height)
        QTimer.singleShot(0, self.sync_settings_selected_card_height)
        QTimer.singleShot(0, self.update_selected_zone_border)

    def resizeEvent(self, event):
        """窗口大小调整事件。"""
        super().resizeEvent(event)
        self.equalize_columns()
        self.sync_source_cache_card_height()
        self.sync_settings_selected_card_height()

    def equalize_columns(self):
        """使左右两栏等宽。"""
        if hasattr(self, "column_splitter") and self.column_splitter:
            total = max(self.column_splitter.width(), 2)
            half = total // 2
            self.column_splitter.setSizes([half, total - half])

    def sync_source_cache_card_height(self):
        """同步源文件卡片和缓存卡片的高度。"""
        if hasattr(self, "card_io") and hasattr(self, "card_source"):
            target = max(
                self.card_io.minimumSizeHint().height(),
                self.card_source.minimumSizeHint().height(),
            )
            self.card_io.setFixedHeight(target)
            self.card_source.setFixedHeight(target)

    def sync_settings_selected_card_height(self):
        """同步设置卡片和文件列表卡片的高度。"""
        if not (
            hasattr(self, "card_settings")
            and hasattr(self, "card_action")
            and hasattr(self, "card_selected_files")
        ):
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

        right_h = max(
            self.card_selected_files.height(),
            self.card_selected_files.minimumSizeHint().height(),
        )
        available = max(0, right_h - gap)

        pref_sum = max(1, settings_pref + action_pref)
        action_h = round(available * (action_pref / pref_sum))
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
        """将窗口居中显示。"""
        screen = (
            self.windowHandle().screen()
            if self.windowHandle()
            else QGuiApplication.primaryScreen()
        )
        if not screen:
            return
        screen_geo = screen.availableGeometry()
        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(screen_geo.center())
        self.move(frame_geo.topLeft())

    def show_welcome_wizard(self):
        """显示欢迎向导，防重入控制。"""
        if hasattr(self, "_wizard_running") and self._wizard_running:
            return
        self._wizard_running = True
        try:
            w = WelcomeWizard(self)
            w.exec()
        finally:
            self._wizard_running = False

    def load_settings_to_ui(self):
        """从配置文件加载设置到UI。"""
        data, loaded_encoder_settings = self.config_manager.load()
        self.encoder_settings = loaded_encoder_settings

        # 旧版本遗留的中文标签值迁移到规范值（仅影响旧配置文件）
        data["save_mode"] = self.OLD_VALUE_MAP.get(data["save_mode"], data["save_mode"])
        for enc_conf in self.encoder_settings.values():
            enc_conf["loudnorm_mode"] = self.OLD_VALUE_MAP.get(
                enc_conf["loudnorm_mode"], enc_conf["loudnorm_mode"]
            )

        if not os.path.exists(self.config_manager.config_path):
            self.is_first_run = True
            self.save_settings_file(DEFAULT_SETTINGS, self.encoder_settings)
        else:
            self.is_first_run = False

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

        concurrency_mode_index = self.combo_transcode_mode.findData(
            data.get("transcode_concurrency_mode", "auto")
        )
        if concurrency_mode_index > -1:
            self.combo_transcode_mode.setCurrentIndex(concurrency_mode_index)
        try:
            concurrency = int(data.get("transcode_concurrency", "2"))
        except (TypeError, ValueError):
            concurrency = 2
        self.spin_transcode_concurrency.setValue(max(1, min(4, concurrency)))
        self.toggle_transcode_concurrency_ui()

        color_mode_index = self.combo_color.findData(data.get("color_mode", "Auto"))
        if color_mode_index > -1:
            self.combo_color.setCurrentIndex(color_mode_index)

        self.global_settings = data

        # 初始加载后同步日志块数上限；非法值回退 LOG_MAX_BLOCKS
        try:
            self.log_manager.set_log_cap(int(data.get("log_cap")))
        except (TypeError, ValueError):
            self.log_manager.set_log_cap(LOG_MAX_BLOCKS)

        # Load settings to the new settings interface
        if hasattr(self, "settings_interface"):
            self.settings_interface.load_settings(data)

    def load_encoder_settings_to_ui(self, enc_name):
        """加载指定编码器的设置到UI。"""
        settings = self.encoder_settings.get(enc_name, ENCODER_CONFIGS.get(enc_name))
        if not settings:
            return

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
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)
        else:
            self.combo_preset.setCurrentIndex(3)

        self.block_signals_for_settings(False)

        if ENC_NVENC in enc_name:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.nvidia"))
        elif ENC_AMF in enc_name:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.amd"))
        else:
            self.lbl_aq.setText(tr("home.settings_card.nv_aq.label.intel"))
        self.sw_nv_aq.setEnabled(True)

        is_hw = (
            (ENC_AMF in enc_name) or (ENC_NVENC in enc_name) or (ENC_QSV in enc_name)
        )
        self.lbl_offset.setEnabled(is_hw)
        self.spin_offset.setEnabled(is_hw)

    def block_signals_for_settings(self, block):
        """阻止或取消阻止设置控件的信号，以避免在加载设置时触发不必要的操作。"""
        widgets = [
            self.line_vmaf,
            self.line_audio,
            self.line_loudnorm,
            self.combo_loudnorm,
            self.sw_nv_aq,
            self.combo_preset,
            self.spin_offset,
            self.combo_color,
        ]
        for w in widgets:
            w.blockSignals(block)

    def on_encoder_changed(self, index):
        """当用户更改编码器时调用，保存旧编码器的设置并加载新编码器的设置。"""
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
            "amf_offset": str(self.spin_offset.value()),
        }
        self.encoder_settings[self.last_encoder_name].update(prev_settings)

        self.last_encoder_name = new_encoder
        self.load_encoder_settings_to_ui(new_encoder)

        self.auto_save_settings()

    def bind_auto_save_signals(self):
        """绑定所有设置控件的信号到自动保存槽函数。"""
        self.combo_preset.currentIndexChanged.connect(
            lambda _: self.auto_save_settings()
        )
        self.combo_theme.currentIndexChanged.connect(
            lambda _: self.auto_save_settings()
        )
        self.combo_save_mode.currentIndexChanged.connect(
            lambda _: self.auto_save_settings()
        )
        self.sw_nv_aq.checkedChanged.connect(lambda _: self.auto_save_settings())
        self.combo_loudnorm.currentIndexChanged.connect(
            lambda _: self.auto_save_settings()
        )
        self.line_vmaf.textChanged.connect(lambda _: self.auto_save_settings())
        self.line_audio.textChanged.connect(lambda _: self.auto_save_settings())
        self.line_loudnorm.textChanged.connect(lambda _: self.auto_save_settings())
        self.line_export.textChanged.connect(lambda _: self.auto_save_settings())
        self.spin_offset.valueChanged.connect(lambda _: self.auto_save_settings())
        self.combo_color.currentIndexChanged.connect(
            lambda _: self.auto_save_settings()
        )
        self.combo_transcode_mode.currentIndexChanged.connect(
            lambda _: self.auto_save_settings()
        )
        self.spin_transcode_concurrency.valueChanged.connect(
            lambda _: self.auto_save_settings()
        )

    def auto_save_settings(self):
        """自动保存当前设置。"""
        if self._auto_save_blocked:
            return
        self.save_current_settings(show_tip=False)

    def save_settings_file(self, settings_dict, encoder_settings=None):
        """将设置字典写入配置文件。"""
        self.config_manager.save(settings_dict, encoder_settings)

    def save_current_settings(self, show_tip=False):
        """保存当前UI上的所有设置到文件。"""
        curr_enc = self.combo_encoder.currentText()
        if curr_enc in self.encoder_settings:
            self.encoder_settings[curr_enc].update(
                {
                    "vmaf": self.line_vmaf.text(),
                    "audio_bitrate": self.line_audio.text(),
                    "preset": self.combo_preset.text(),
                    "loudnorm": self.line_loudnorm.text(),
                    "loudnorm_mode": self.combo_loudnorm.currentData(),
                    "nv_aq": str(self.sw_nv_aq.isChecked()),
                    "amf_offset": str(self.spin_offset.value()),
                }
            )
        settings = {
            "encoder": curr_enc,
            "theme": THEMES[self.combo_theme.currentIndex()],
            "save_mode": self.combo_save_mode.currentData(),
            "export_dir": self.line_export.text().strip(),
            "language": translator.current_lang,
            "color_mode": self.combo_color.currentData() or "Auto",
            "transcode_concurrency_mode": self.combo_transcode_mode.currentData()
            or "auto",
            "transcode_concurrency": str(self.spin_transcode_concurrency.value()),
        }
        if hasattr(self, "global_settings"):
            self.global_settings.update(settings)
        self.save_settings_file(settings, self.encoder_settings)
        if show_tip:
            orig_text = self.btn_save_conf.text()
            self.btn_save_conf.setText(tr("button.save.saved"))
            self.btn_save_conf.setStyleSheet("color: #FB7299; font-weight: bold;")

            QTimer.singleShot(
                1000,
                lambda: [
                    self.btn_save_conf.setText(orig_text),
                    self.btn_save_conf.setStyleSheet(""),
                ],
            )

            InfoBar.success(
                tr("infobar.success.settings_saved.title"),
                tr("infobar.success.settings_saved.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )

    def restore_defaults(self):
        """恢复所有设置为默认值。"""
        self._auto_save_blocked = True
        self.setUpdatesEnabled(False)

        widgets_to_block = [
            self.combo_encoder,
            self.combo_preset,
            self.combo_theme,
            self.combo_save_mode,
            self.combo_loudnorm,
            self.sw_nv_aq,
            self.line_vmaf,
            self.line_audio,
            self.line_loudnorm,
            self.line_export,
            self.spin_offset,
            self.combo_color,
            self.combo_transcode_mode,
            self.spin_transcode_concurrency,
        ]
        for w in widgets_to_block:
            w.blockSignals(True)

        # 从 ConfigManager 获取默认配置（深拷贝，不污染全局常量）
        default_settings, default_encoder_settings = self.config_manager.reset()
        self.encoder_settings = default_encoder_settings

        current_enc = self.combo_encoder.currentText()
        self.load_encoder_settings_to_ui(current_enc)

        self.combo_theme.setCurrentIndex(0)
        self.on_theme_changed(0)

        self.combo_save_mode.setCurrentIndex(
            self.combo_save_mode.findData(SAVE_MODE_OVERWRITE)
        )
        self.line_export.clear()
        self.combo_color.setCurrentIndex(self.combo_color.findData("Auto"))
        self.combo_transcode_mode.setCurrentIndex(
            self.combo_transcode_mode.findData("auto")
        )
        self.spin_transcode_concurrency.setValue(2)
        # 直接应用默认全局设置到内存，保证 reset 返回值真实生效
        self.global_settings = default_settings
        # 恢复默认后同步日志块数上限；非法值回退 LOG_MAX_BLOCKS
        try:
            self.log_manager.set_log_cap(int(default_settings.get("log_cap")))
        except (TypeError, ValueError):
            self.log_manager.set_log_cap(LOG_MAX_BLOCKS)
        # 同步系统设置页控件，避免后续保存把旧值写回。
        # 屏蔽语言/主题控件的信号：避免 setCurrentIndex 触发 on_language_changed 弹模态框
        # 或 on_theme_changed 强制切换语言/主题；仅同步其余系统设置控件。
        # DEFAULT_SETTINGS 无 language 键，load_settings 会回落到 zh_CN，
        # 因此加载默认值后需把设置页语言下拉框恢复到当前语言，避免后续保存写回 zh_CN。
        if hasattr(self, "settings_interface"):
            sig_blocks = [
                self.settings_interface.combo_lang,
                self.settings_interface.combo_theme,
            ]
            orig_lang_data = self.settings_interface.combo_lang.currentData()
            try:
                for sig_w in sig_blocks:
                    sig_w.blockSignals(True)
                self.settings_interface.load_settings(default_settings)
            finally:
                # 恢复语言下拉框（仍在信号屏蔽窗口内，不触发任何槽）
                if orig_lang_data is not None:
                    lang_idx = self.settings_interface.combo_lang.findData(
                        orig_lang_data
                    )
                    if lang_idx >= 0:
                        self.settings_interface.combo_lang.setCurrentIndex(lang_idx)
                for sig_w in sig_blocks:
                    sig_w.blockSignals(False)

        for w in widgets_to_block:
            w.blockSignals(False)

        self.toggle_export_ui()
        self.toggle_transcode_concurrency_ui()
        self.setUpdatesEnabled(True)
        self._auto_save_blocked = False

        self.save_current_settings(show_tip=False)

        orig_text = self.btn_reset_conf.text()
        self.btn_reset_conf.setText(tr("button.reset.restored"))
        self.btn_reset_conf.setStyleSheet("color: #FB7299; font-weight: bold;")
        QTimer.singleShot(
            1000,
            lambda: [
                self.btn_reset_conf.setText(orig_text),
                self.btn_reset_conf.setStyleSheet(""),
            ],
        )

        InfoBar.info(
            tr("infobar.info.settings_reset.title"),
            tr("infobar.info.settings_reset.content"),
            parent=self,
            position=InfoBarPosition.TOP,
        )

        QApplication.processEvents()

        if self.transcode_controller.is_running():
            InfoBar.warning(
                tr("infobar.warning.dependency_check_skipped.title"),
                tr("infobar.warning.dependency_check_skipped.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        else:
            self.log(tr("log.recalibrating"), "info")
            QTimer.singleShot(200, self.check_dependencies)

    def apply_preset_light(self):
        """启用轻量洗版术模板"""
        self.line_vmaf.setText("91.0")
        idx = self.combo_preset.findText("5")
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)
        InfoBar.success(
            tr("infobar.success.preset_light.title"),
            tr("infobar.success.preset_light.content"),
            parent=self,
            position=InfoBarPosition.TOP,
        )
        self.auto_save_settings()

    def apply_preset_balanced(self):
        """启用黄金均衡法则模板"""
        self.line_vmaf.setText("93.0")
        idx = self.combo_preset.findText("4")
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)
        InfoBar.success(
            tr("infobar.success.preset_balanced.title"),
            tr("infobar.success.preset_balanced.content"),
            parent=self,
            position=InfoBarPosition.TOP,
        )
        self.auto_save_settings()

    def apply_preset_heavenly(self):
        """启用圣殿至高典藏模板"""
        self.line_vmaf.setText("95.5")
        idx = self.combo_preset.findText("3")
        if idx >= 0:
            self.combo_preset.setCurrentIndex(idx)
        InfoBar.success(
            tr("infobar.success.preset_heavenly.title"),
            tr("infobar.success.preset_heavenly.content"),
            parent=self,
            position=InfoBarPosition.TOP,
        )
        self.auto_save_settings()

    def on_theme_changed(self, index):
        """当用户在设置中更改主题时调用。"""
        if index == 0:
            setTheme(Theme.AUTO)
        elif index == 1:
            setTheme(Theme.LIGHT)
        elif index == 2:
            setTheme(Theme.DARK)
        setThemeColor("#FB7299")

        combos = [self.combo_theme]
        if hasattr(self, "info_interface"):
            combos.append(self.info_interface.combo_theme)
        if hasattr(self, "profile_interface"):
            combos.append(self.profile_interface.combo_theme)
        if hasattr(self, "credits_interface"):
            combos.append(self.credits_interface.combo_theme)
        if hasattr(self, "settings_interface"):
            combos.append(self.settings_interface.combo_theme)
        for c in combos:
            if c.currentIndex() != index:
                c.blockSignals(True)
                c.setCurrentIndex(index)
                c.blockSignals(False)

        QTimer.singleShot(50, self._update_card_style)

        QTimer.singleShot(0, self.update_selected_zone_border)
        QTimer.singleShot(120, self.update_selected_zone_border)

    def on_settings_save_requested(self, settings):
        """处理设置页面的保存请求。"""
        # 在现有已持久化设置的基础上合并本次修改，并写盘
        current_settings = self.config_manager.merge_settings(settings)
        self.global_settings = current_settings

        # 同步日志块数上限；非法值回退 LOG_MAX_BLOCKS
        try:
            self.log_manager.set_log_cap(int(self.global_settings.get("log_cap")))
        except (TypeError, ValueError):
            self.log_manager.set_log_cap(LOG_MAX_BLOCKS)

        # Save to file
        self.save_settings_file(current_settings, self.encoder_settings)

        # Apply theme and language changes immediately
        if "theme" in settings:
            try:
                idx = THEMES.index(settings["theme"])
                self.combo_theme.setCurrentIndex(idx)
                self.on_theme_changed(idx)
            except ValueError:
                pass

        if "language" in settings:
            lang_code = settings["language"]
            self.on_language_changed(self.combo_lang.findData(lang_code))

        InfoBar.success(
            tr("infobar.success.settings_saved.title"),
            tr("infobar.success.settings_saved.content"),
            parent=self,
            position=InfoBarPosition.TOP,
        )

    def _update_card_style(self):
        """根据主题调整卡片样式 (解决浅色模式太白的问题)。"""
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
        """弹出文件夹选择对话框，并将选择的文件夹路径设置到指定的LineEdit。"""
        folder = QFileDialog.getExistingDirectory(
            self, tr("home.action_card.choose_button")
        )
        if folder:
            line_edit.setText(folder)

    def add_source_paths(self, paths):
        """将给定的路径（文件或文件夹）添加到待处理文件列表中（委托给 manager）。"""
        return self.file_list_manager.add_source_paths(paths)

    def handle_dropped_paths(self, paths):
        """处理拖放的文件路径。"""
        added = self.add_source_paths(paths)
        if added == 0:
            InfoBar.warning(
                tr("infobar.warning.no_new_files_dropped.title"),
                tr("infobar.warning.no_new_files_dropped.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        else:
            InfoBar.success(
                tr("infobar.success.files_added.title"),
                tr("infobar.success.drag_drop_added.content", count=added),
                parent=self,
                position=InfoBarPosition.TOP,
            )

    def clear_selected_list_visual_state(self):
        """清除文件列表的视觉选择状态（委托给 manager）。"""
        if hasattr(self, "file_list_manager"):
            self.file_list_manager.clear_selected_list_visual_state()

    def on_selected_zone_drag_active_changed(self, active):
        """当拖拽进入或离开文件列表区域时调用（委托给 manager）。"""
        if hasattr(self, "file_list_manager"):
            self.file_list_manager.set_drag_active(active)

    def update_selected_zone_border(self):
        """更新文件列表区域的边框样式，以响应拖拽状态（委托给 manager）。"""
        if hasattr(self, "file_list_manager"):
            self.file_list_manager.update_selected_zone_border()

    def choose_source_folder(self):
        """弹出文件夹选择对话框以选择源文件夹。"""
        folder = QFileDialog.getExistingDirectory(
            self, tr("home.source_card.folder_button")
        )
        if not folder:
            return
        added = self.add_source_paths([folder])
        if added == 0:
            InfoBar.warning(
                tr("infobar.warning.no_files_found.title"),
                tr("infobar.warning.no_files_found.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        else:
            InfoBar.success(
                tr("infobar.success.files_added.title"),
                tr("infobar.success.files_added.content", count=added),
                parent=self,
                position=InfoBarPosition.TOP,
            )

    def browse_files(self):
        """弹出文件选择对话框以选择源文件。"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("home.source_card.file_button"),
            "",
            "Video Files (*.mkv *.mp4 *.avi *.mov *.wmv *.flv *.webm *.m4v *.ts);;All Files (*.*)",
        )
        if files:
            self.add_source_paths(files)

    def open_file_location(self, item):
        """在文件浏览器中打开所选文件的位置。"""
        if not item:
            return
        row = self.list_selected_files.row(item)
        selected_files = self.file_list_manager.selected_files
        if 0 <= row < len(selected_files):
            path = selected_files[row]
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            except Exception:  # noqa: S110, BLE001
                pass

    def process_duration_queue(self):
        """处理等待中的视频时长分析任务（委托给 manager）。"""
        self.file_list_manager.process_duration_queue()

    def start_duration_worker(self, path):
        """启动一个新的线程来分析视频时长（委托给 manager）。"""
        self.file_list_manager.start_duration_worker(path)

    def on_duration_worker_finished(self, path):
        """视频时长分析线程完成时的清理工作（委托给 manager）。"""
        self.file_list_manager.on_duration_worker_finished(path)

    def get_file_duration(self, path):
        """请求获取指定文件的视频时长（委托给 manager）。"""
        self.file_list_manager.get_file_duration(path)

    def update_file_duration_label(self, path, duration_str, duration_sec, meta=None):
        """更新文件列表中的视频时长标签（委托给 manager）。"""
        self.file_list_manager.update_file_duration_label(
            path, duration_str, duration_sec, meta
        )

    def process_thumbnail_queue(self):
        """处理等待中的视频缩略图生成任务（委托给 manager）。"""
        self.file_list_manager.process_thumbnail_queue()

    def start_thumbnail_worker(self, path, duration_sec):
        """启动一个新的线程来生成视频缩略图（委托给 manager）。"""
        self.file_list_manager.start_thumbnail_worker(path, duration_sec)

    def on_thumbnail_worker_finished(self, path):
        """视频缩略图生成线程完成时的清理工作（委托给 manager）。"""
        self.file_list_manager.on_thumbnail_worker_finished(path)

    def get_file_thumbnail(self, path, duration_sec):
        """请求获取指定文件的视频缩略图（委托给 manager）。"""
        self.file_list_manager.get_file_thumbnail(path, duration_sec)

    def update_file_thumbnail(self, path, image):
        """更新文件列表中的视频缩略图（委托给 manager）。"""
        self.file_list_manager.update_file_thumbnail(path, image)

    def clear_all_selected_files(self):
        """清空所有已选择的文件。"""
        if not self.file_list_manager.selected_files:
            return

        if self.transcode_controller.is_running():
            InfoBar.warning(
                tr("infobar.warning.task_running.title"),
                tr("infobar.warning.task_running.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        title = tr("dialog.clear_list.title")
        content = tr("dialog.clear_list.content")
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText(tr("dialog.clear_list.yes_button"))
        dialog.cancelButton.setText(tr("dialog.clear_list.cancel_button"))
        if not dialog.exec():
            return

        self.file_list_manager.clear()
        self.log(tr("log.list_cleared"), "info")

    def set_duration_text_in_list(self, path, text):
        """在文件列表中设置指定文件的时长文本（委托给 manager）。"""
        self.file_list_manager.set_duration_text_in_list(path, text)

    def remove_selected_file(self, file_path):
        """从文件列表中移除指定的文件（委托给 manager）。"""
        self.file_list_manager.remove_selected_file(file_path)

    def format_file_size(self, size_bytes):
        """格式化文件大小为可读字符串（委托给 manager）。"""
        return self.file_list_manager.format_file_size(size_bytes)

    def update_selected_count(self):
        """更新文件列表中的文件数量显示（委托给 manager）。"""
        if hasattr(self, "file_list_manager"):
            self.file_list_manager.update_selected_count()

    def update_file_progress(self, filepath, percent):
        """更新指定文件的进度条（委托给 manager）。"""
        self.file_list_manager.update_file_progress(filepath, percent)

    def update_file_stats(self, filepath, speed, eta):
        """更新指定文件的统计信息（委托给 manager）。"""
        self.file_list_manager.update_file_stats(filepath, speed, eta)

    def update_file_status(self, filepath, status):
        """更新指定文件的状态图标（委托给 manager）。"""
        self.file_list_manager.update_file_status(filepath, status)

    def toggle_export_ui(self):
        """根据保存模式显示或隐藏导出路径UI。"""
        current_save_mode_key = self.combo_save_mode.currentData()
        is_save_as = current_save_mode_key == SAVE_MODE_SAVE_AS
        self.export_container.setVisible(is_save_as)
        self.export_container.updateGeometry()
        if self.card_action.layout():
            self.card_action.layout().activate()
        self.card_action.updateGeometry()
        self.sync_settings_selected_card_height()
        QTimer.singleShot(0, self.sync_settings_selected_card_height)

    def toggle_transcode_concurrency_ui(self):
        is_manual = self.combo_transcode_mode.currentData() == "manual"
        self.spin_transcode_concurrency.setEnabled(is_manual)
        self.lbl_transcode_count.setEnabled(is_manual)

    def log(self, msg, level="info"):
        """将日志消息交给 LogManager 缓冲（线程安全，供 worker 信号连接）。"""
        self.log_manager.log(msg, level)

    def process_log_queue(self):
        """定期将 LogManager 队列中的日志刷新到日志区域（定时器槽）。"""
        self.log_manager.flush()

    def auto_clean_cache_startup(self):
        """启动时静默清除ab-av1生成的临时缓存文件。"""
        if (
            not hasattr(self, "global_settings")
            or self.global_settings.get("auto_clean_on_launch", "True") != "True"
        ):
            return
        try:
            cache_path = self.line_cache.text().strip() or get_default_cache_dir()
            if not os.path.exists(cache_path):
                return
            removed = cleanup_stale_sessions(
                cache_path,
                active_session_ids=(),
                min_age_seconds=24 * 60 * 60,
            )
            if removed:
                self.log(
                    f"🧹 [自动肃清] 成功清除缓存目录下的 {len(removed)} 个临时会话目录。",
                    "info",
                )
        except Exception as e:  # noqa: BLE001
            self.log(f"⚠️ [自动肃清] 清理缓存文件失败: {e!s}", "warning")

    def clear_cache_files(self):
        """清除ab-av1生成的临时缓存文件。"""
        cache_path = self.line_cache.text().strip() or get_default_cache_dir()
        if not os.path.exists(cache_path):
            InfoBar.warning(
                tr("infobar.warning.invalid_cache_path.title"),
                tr("infobar.warning.invalid_cache_path.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
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
            InfoBar.success(
                tr("infobar.success.cache_cleared.title"),
                tr("infobar.success.cache_cleared.content", count=count),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        except Exception as e:  # noqa: BLE001
            InfoBar.error(
                tr("infobar.error.cache_clear_failed.title"),
                str(e),
                parent=self,
                position=InfoBarPosition.TOP,
            )

    def _connect_transcode_signals(self):
        """连接 TranscodeController 的全部信号到既有 UI/日志/文件列表处理器。"""
        self.transcode_controller.log_signal.connect(self.log)
        self.transcode_controller.progress_total_signal.connect(
            self.pbar_total.setValue
        )
        self.transcode_controller.progress_current_signal.connect(
            self.pbar_current.setValue
        )
        self.transcode_controller.file_progress_signal.connect(
            self.file_list_manager.update_file_progress
        )
        self.transcode_controller.file_stats_signal.connect(
            self.file_list_manager.update_file_stats
        )
        self.transcode_controller.file_status_signal.connect(
            self.file_list_manager.update_file_status
        )
        self.transcode_controller.finished_signal.connect(self.on_finished)
        self.transcode_controller.ask_error_decision.connect(self.on_worker_error)
        self.transcode_controller.concurrency_status_signal.connect(
            self.lbl_concurrency_status.setText
        )

    def start_task(self):
        """开始编码任务。"""
        selected_files, file_metadata = self.file_list_manager.snapshot()
        if not selected_files:
            InfoBar.warning(
                title=tr("infobar.warning.no_files_selected.title"),
                content=tr("infobar.warning.no_files_selected.content"),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                parent=self,
            )
            return

        save_mode = self.combo_save_mode.currentData()
        export_dir = self.line_export.text().strip()
        if save_mode == SAVE_MODE_SAVE_AS and not export_dir:
            InfoBar.warning(
                tr("infobar.warning.no_export_dir.title"),
                tr("infobar.warning.no_export_dir.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        try:
            vmaf_val = float(self.line_vmaf.text())
        except ValueError:
            InfoBar.error(
                tr("infobar.error.vmaf_not_number.title"),
                tr("infobar.error.vmaf_not_number.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
            return

        config = {
            "selected_files": selected_files,
            "encoder": self.combo_encoder.currentText(),
            "export_dir": export_dir,
            "save_mode": self.combo_save_mode.currentData(),
            "cache_dir": self.line_cache.text().strip() or get_default_cache_dir(),
            "preset": self.combo_preset.text(),
            "vmaf": vmaf_val,
            "metadata": file_metadata,
            "audio_bitrate": self.line_audio.text(),
            "loudnorm": self.line_loudnorm.text(),
            "nv_aq": self.sw_nv_aq.isChecked(),
            "amf_offset": self.spin_offset.value(),
            "loudnorm_mode": self.combo_loudnorm.currentData(),
            "gpu_cooling_time": int(self.global_settings.get("gpu_cooling_time", "3"))
            if hasattr(self, "global_settings")
            else 3,
            "hw_decoding": (self.global_settings.get("hw_decoding", "True") == "True")
            if hasattr(self, "global_settings")
            else True,
            "color_mode": self.combo_color.currentData() or "Auto",
            "transcode_concurrency_mode": self.combo_transcode_mode.currentData()
            or "auto",
            "transcode_concurrency": self.spin_transcode_concurrency.value(),
        }
        os.makedirs(config["cache_dir"], exist_ok=True)

        # 委托给 TranscodeController 创建/绑定/启动 coordinator；不再直接构造
        # EncodingCoordinator，也不持有 self.worker。
        if not self.transcode_controller.start(config):
            return

        self.btn_start.setEnabled(False)
        self.btn_clear_list.setEnabled(False)
        self.btn_start.setText(tr("button.start.in_progress"))
        self.btn_pause.setEnabled(True)
        self.combo_encoder.setEnabled(False)
        self.combo_save_mode.setEnabled(False)
        self.combo_transcode_mode.setEnabled(False)
        self.spin_transcode_concurrency.setEnabled(False)
        self.btn_pause.setText(tr("home.action_card.pause_button"))
        self.btn_stop.setEnabled(True)
        self.pbar_total.setValue(0)
        self.pbar_current.setValue(0)

    def on_worker_error(self, task_id, title, content):
        """当工作线程遇到错误时，弹出一个对话框让用户决定是跳过还是停止。"""
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

        decision = "continue" if res else "stop"
        self.transcode_controller.decide_error(task_id, decision)

    def stop_task(self):
        """停止当前正在运行的编码任务。"""
        if self.transcode_controller.is_running():
            self.log(tr("log.task_stop_request"), "error")
            self.transcode_controller.stop()
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)

    def pause_task(self):
        """暂停或恢复当前正在运行的编码任务。"""
        if self.transcode_controller.is_running():
            if self.transcode_controller.is_paused:
                self.transcode_controller.set_paused(False)
                self.btn_pause.setText(tr("home.action_card.pause_button"))
                self.log(tr("log.task_resume"), "info")
            else:
                self.transcode_controller.set_paused(True)
                self.btn_pause.setText(tr("home.action_card.pause_button"))
                self.log(tr("log.task_pause"), "info")

    def on_finished(self):
        """当编码任务完成时调用，恢复UI状态。"""
        self.btn_start.setEnabled(True)
        self.btn_clear_list.setEnabled(True)
        self.btn_start.setText(tr("home.action_card.start_button"))
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.combo_encoder.setEnabled(True)
        self.combo_save_mode.setEnabled(True)
        self.combo_transcode_mode.setEnabled(True)
        self.toggle_transcode_concurrency_ui()
        self.lbl_concurrency_status.setText(tr("home.action_card.concurrency.idle"))
        # coordinator 的引用清理由 TranscodeController 在 finished 回调中完成，
        # 这里不再置空 worker/coordinator。

    def apply_encoder_availability(self, has_qsv, has_nvenc, has_amf):
        """根据可用的编码器更新编码器选择下拉框。"""
        mapping = [
            (ENC_QSV, 0, has_qsv),
            (ENC_NVENC, 1, has_nvenc),
            (ENC_AMF, 2, has_amf),
        ]

        for _, idx, enabled in mapping:
            self.combo_encoder.setItemEnabled(idx, enabled)

        available = [(name, idx) for name, idx, enabled in mapping if enabled]
        if not available:
            self.combo_encoder.setEnabled(False)
            return None

        if not self.transcode_controller.is_running():
            self.combo_encoder.setEnabled(True)

        current = self.combo_encoder.currentText()
        valid_names = {name for name, _ in available}
        if current not in valid_names:
            self.combo_encoder.setCurrentIndex(available[0][1])
            return available[0][0]

        return None

    def check_dependencies(self):
        """检查所需的外部依赖（如ffmpeg）是否存在。"""
        if self.dep_worker:
            try:
                if self.dep_worker.isRunning():
                    self.log(
                        tr("infobar.warning.duplicate_dependency_check.content"),
                        "warning",
                    )
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
        """依赖检查线程完成时的清理工作。"""
        self.dep_worker = None

    def on_dependency_missing(self, missing):
        """当检测到有依赖缺失时调用，弹出一个对话框提示用户。"""
        # [Fix] 先记录日志，确保在弹窗阻塞主线程前，错误信息已经进入队列并显示
        self.log(tr("log.fatal_error_component_missing"), "error")

        title = tr("dialog.dependency_missing.title")
        content = tr(
            "dialog.dependency_missing.content", missing_files=chr(10).join(missing)
        )

        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText(tr("dialog.dependency_missing.yes_button"))
        dialog.cancelButton.setText(tr("dialog.dependency_missing.cancel_button"))

        if dialog.exec():
            QDesktopServices.openUrl(
                QUrl.fromUserInput(
                    "https://github.com/LingMoe404/MagicalGirlWorkshop/blob/main/docs/FAQ.md"
                )
            )

        self.btn_start.setEnabled(False)
        self.btn_start.setText(tr("button.start.missing_components"))
        self.apply_encoder_availability(False, False, False)

    def on_dependency_check_finished(self, has_qsv, has_nvenc, has_amf):
        """当依赖检查完成时调用，更新编码器可用性并记录日志。"""
        switched_to = self.apply_encoder_availability(has_qsv, has_nvenc, has_amf)

        if not has_qsv and not has_nvenc and not has_amf:
            self.log(tr("log.dependency_check_finished.fail"), "error")
            InfoBar.warning(
                tr("infobar.warning.hardware_unsupported.title"),
                tr("infobar.warning.hardware_unsupported.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        else:
            msg = tr("log.dependency_check_finished.success")
            if has_qsv:
                msg += f" [{ENC_QSV}]"
            if has_nvenc:
                msg += f" [{ENC_NVENC}]"
            if has_amf:
                msg += f" [{ENC_AMF}]"
            self.log(msg + " (Ready)", "success")
            if switched_to:
                self.log(tr("log.autoselect_encoder", encoder=switched_to), "info")

    def add_source_paths_from_info(self, path):
        """从“真理之眼”界面添加文件到主列表。"""
        added = self.add_source_paths([path])
        if added > 0:
            self.switchTo(self.home_interface)
            InfoBar.success(
                tr("infobar.success.synced.title"),
                tr("infobar.success.synced.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )

    def closeEvent(self, event):
        """窗口关闭事件，确保所有后台线程都已停止。"""
        if self.transcode_controller.is_running():
            title = tr("dialog.close_warning.title") or "⚠️ 结界强行切断警告"
            content = (
                tr("dialog.close_warning.content")
                or "炼成仪式（转码）正处于奇迹发生阶段。强行关闭终端可能导致魔力逆流（后台残留 FFmpeg 幽灵进程）。\n\n确定要立即破弃契约并退出吗？"
            )
            dialog = MessageDialog(title, content, self)
            dialog.yesButton.setText(
                tr("dialog.close_warning.yes_button") or "确定破弃 (Quit)"
            )
            dialog.cancelButton.setText(
                tr("dialog.close_warning.cancel_button") or "维持仪式 (Stay)"
            )
            if not dialog.exec():
                event.ignore()
                return

            # 委托 TranscodeController 异步停止并等待（默认 2000ms），
            # 保证系统级安全强杀后台进程；不再直接操作 coordinator/worker。
            self.transcode_controller.shutdown(2000)

        # 强杀依赖自检线程，杜绝关闭后残留
        if (
            hasattr(self, "dep_worker")
            and self.dep_worker
            and self.dep_worker.isRunning()
        ):
            try:
                self.dep_worker.stop()
                self.dep_worker.wait(500)
            except Exception:  # noqa: S110, BLE001
                pass

        # 停止文件列表的时长/缩略图 worker（委托给 manager）
        self.file_list_manager.stop_workers()

        self.info_interface.stop_worker()

        # 停止日志刷新定时器与 LogManager，关闭后不再消费新日志
        self.log_timer.stop()
        self.log_manager.stop()

        super().closeEvent(event)
