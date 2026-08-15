import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    IconWidget,
    ImageLabel,
    InfoBar,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    SpinBox,
    SubtitleLabel,
    SwitchButton,
    TextEdit,
    isDarkTheme,
)

from config import VERSION, VIDEO_EXTS
from i18n.translator import tr, translator
from utils import resource_path
from workers.analyzer import AnalysisWorker


class MediaInfoInterface(QWidget):
    """“真理之眼”界面，用于分析媒体文件并显示其详细信息。"""

    addFileRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("mediaInfoInterface")
        self.setAcceptDrops(True)
        self.current_path = None
        self.worker = None
        self.init_ui()
        self.retranslate_ui()

    def init_ui(self):
        """初始化界面布局和组件。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.title = SubtitleLabel(self)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)

        self.combo_lang = ComboBox(self)
        self.combo_lang.setMinimumWidth(120)
        lang_map = translator.get_language_map()
        for lang_code, lang_name in lang_map.items():
            self.combo_lang.addItem(lang_name, userData=lang_code)
        header_layout.addWidget(self.combo_lang)

        self.combo_theme = ComboBox(self)
        self.combo_theme.setMinimumWidth(140)
        self.combo_theme.addItem(
            tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.light"), icon=FluentIcon.BRIGHTNESS
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.dark"), icon=FluentIcon.QUIET_HOURS
        )
        header_layout.addWidget(self.combo_theme)

        layout.addLayout(header_layout)

        self.drop_card = CardWidget(self)
        self.drop_card.setFixedHeight(200)
        card_layout = QVBoxLayout(self.drop_card)
        card_layout.setContentsMargins(20, 20, 20, 20)

        self.eye_icon = IconWidget(FluentIcon.SEARCH, self.drop_card)
        self.eye_icon.setFixedSize(64, 64)
        h_eye = QHBoxLayout()
        h_eye.addStretch(1)
        h_eye.addWidget(self.eye_icon)
        h_eye.addStretch(1)
        card_layout.addLayout(h_eye)

        self.drop_title = SubtitleLabel(self.drop_card)
        self.drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint = BodyLabel(self.drop_card)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setTextColor(QColor("#999999"), QColor("#999999"))

        card_layout.addWidget(self.drop_title)
        card_layout.addWidget(self.hint)

        layout.addWidget(self.drop_card)

        self.info_text = TextEdit(self)
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            TextEdit {
                font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace;
                font-size: 13px;
                background-color: rgba(0, 0, 0, 0.02);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.info_text)

        bottom_layout = QHBoxLayout()

        self.btn_add_list = PushButton(FluentIcon.ADD, "", self)
        self.btn_add_list.clicked.connect(self.add_to_main_list)
        self.btn_add_list.hide()

        self.btn_clear = PushButton(FluentIcon.DELETE, "", self)
        self.btn_clear.clicked.connect(self.clear_report)

        self.btn_copy = PrimaryPushButton(FluentIcon.COPY, "", self)
        self.btn_copy.clicked.connect(self.copy_report)

        bottom_layout.addWidget(self.btn_add_list)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_clear)
        bottom_layout.addWidget(self.btn_copy)

        layout.addLayout(bottom_layout)

    def retranslate_ui(self):
        """根据当前语言重新翻译界面文本。"""
        self.title.setText(tr("info.title"))
        self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
        self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
        self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))
        self.drop_title.setText(tr("info.drop_card.title"))
        self.hint.setText(tr("info.drop_card.hint"))
        self.info_text.setPlaceholderText(tr("info.text_edit.placeholder"))
        self.btn_add_list.setText(tr("info.buttons.add_to_list"))
        self.btn_clear.setText(tr("info.buttons.clear"))
        self.btn_copy.setText(tr("info.buttons.copy"))

    def stop_worker(self):
        """如果分析线程正在运行，则停止它。"""
        if self.worker:
            try:
                if self.worker.isRunning():
                    self.worker.stop()
                    self.worker.quit()
                    self.worker.wait()
            except RuntimeError:
                pass
            self.worker = None

    def copy_report(self):
        """复制分析报告到剪贴板。"""
        text = self.info_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success(
                tr("info.infobar.copy_success.title"),
                tr("info.infobar.copy_success.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )
        else:
            InfoBar.warning(
                tr("info.infobar.copy_warning.title"),
                tr("info.infobar.copy_warning.content"),
                parent=self,
                position=InfoBarPosition.TOP,
            )

    def clear_report(self):
        """清空当前的分析报告。"""
        self.current_path = None
        self.info_text.clear()
        self.btn_add_list.hide()
        self.stop_worker()

    def add_to_main_list(self):
        """请求将当前文件添加到主界面的文件列表中。"""
        if self.current_path:
            self.addFileRequested.emit(self.current_path)

    def dragEnterEvent(self, event):
        """处理文件拖入事件，过滤并高亮视频拖放区域。"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            # 至少包含一个可识别的视频文件
            has_video = any(u.toLocalFile().lower().endswith(VIDEO_EXTS) for u in urls)
            if has_video:
                event.accept()
                bg_color = "#2D2023" if isDarkTheme() else "#FFF0F3"
                self.drop_card.setStyleSheet(
                    f"CardWidget {{ border: 2px dashed #FB7299; background-color: {bg_color}; }}"
                )
                self.eye_icon.setIcon(FluentIcon.ZOOM_IN)
                return
        event.ignore()

    def dragLeaveEvent(self, event):
        """处理文件拖出事件，恢复拖放区域样式。"""
        self.drop_card.setStyleSheet("")
        self.eye_icon.setIcon(FluentIcon.SEARCH)

    def dropEvent(self, event):
        """处理文件放下事件，只开始分析视频文件。"""
        self.drop_card.setStyleSheet("")
        files = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(VIDEO_EXTS)
        ]
        if files:
            self.analyze_file(files[0])

    def analyze_file(self, filepath):
        """使用后台线程分析给定的文件。"""
        self.current_path = filepath
        self.stop_worker()
        self.info_text.setHtml(
            f"<div style=\"color: #FB7299; font-size: 14px; font-family: 'Microsoft YaHei UI';\">{tr('info.analysis.in_progress')}</div>"
        )
        self.btn_add_list.hide()

        self.worker = AnalysisWorker(filepath)
        self.worker.report_signal.connect(self.on_report_ready)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        """分析线程完成后的清理工作。"""
        self.worker = None

    def on_report_ready(self, html, should_hide):
        """当分析报告准备好时，在界面上显示报告。"""
        self.info_text.setHtml(html)
        if should_hide:
            self.btn_add_list.hide()
        else:
            self.btn_add_list.show()


class ProfileInterface(QWidget):
    """“观测者档案”界面，显示作者的个人信息和社交链接。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("profileInterface")
        self.init_ui()
        self.retranslate_ui()

    def init_ui(self):
        """初始化界面布局和组件。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.title = SubtitleLabel(self)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)

        self.combo_lang = ComboBox(self)
        self.combo_lang.setMinimumWidth(120)
        lang_map = translator.get_language_map()
        for lang_code, lang_name in lang_map.items():
            self.combo_lang.addItem(lang_name, userData=lang_code)
        header_layout.addWidget(self.combo_lang)

        self.combo_theme = ComboBox(self)
        self.combo_theme.setMinimumWidth(140)
        self.combo_theme.addItem(
            tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.light"), icon=FluentIcon.BRIGHTNESS
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.dark"), icon=FluentIcon.QUIET_HOURS
        )
        header_layout.addWidget(self.combo_theme)

        layout.addLayout(header_layout)

        self.card = CardWidget(self)
        card_grid = QGridLayout(self.card)
        card_grid.setContentsMargins(0, 0, 0, 0)
        card_grid.setSpacing(0)

        banner = QFrame(self.card)
        banner.setFixedHeight(150)
        banner.setObjectName("banner")
        banner.setStyleSheet("""
            QFrame#banner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFD1DC, stop:1 #FB7299);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        card_grid.addWidget(banner, 0, 0, Qt.AlignmentFlag.AlignTop)

        content_widget = QWidget(self.card)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 64, 30, 30)
        content_layout.setSpacing(20)

        avatar_path = resource_path("LingMoe404.ico")
        if os.path.exists(avatar_path):
            pixmap = QIcon(avatar_path).pixmap(256, 256)
            avatar = ImageLabel(pixmap, content_widget)
            avatar.setFixedSize(192, 192)
            avatar.setBorderRadius(96, 96, 96, 96)
            avatar.setStyleSheet(
                "border: 6px solid white; background: white; border-radius: 96px;"
            )

            h_avatar = QHBoxLayout()
            h_avatar.addStretch(1)
            h_avatar.addWidget(avatar)
            h_avatar.addStretch(1)
            content_layout.addLayout(h_avatar)

        name = SubtitleLabel("泠萌404", content_widget)
        name.setStyleSheet(
            "font-family: 'Segoe UI Variable Display', 'Segoe UI Variable Text', 'Microsoft YaHei UI'; font-size: 36px; font-weight: bold; color: #FB7299;"
        )
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(name)

        self.desc = BodyLabel(content_widget)
        self.desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc.setTextColor(QColor("#999999"), QColor("#999999"))
        content_layout.addWidget(self.desc)

        self.motto = BodyLabel(content_widget)
        self.motto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motto.setStyleSheet("font-style: italic; color: #666666;")
        content_layout.addWidget(self.motto)

        line = QFrame(content_widget)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(128, 128, 128, 0.1);")
        content_layout.addWidget(line)

        v_btns = QVBoxLayout()
        v_btns.setSpacing(12)

        def create_social_btn(color, url):
            btn = PushButton(content_widget)
            btn.setMinimumHeight(45)
            btn.setFixedWidth(280)
            btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
            btn.setStyleSheet(f"""
                PushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-family: 'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif;
                }}
                PushButton:hover {{
                    background-color: {color};
                    opacity: 0.85;
                }}
            """)
            return btn

        self.btn_bilibili = create_social_btn(
            "#FB7299", "https://space.bilibili.com/136850"
        )
        self.btn_youtube = create_social_btn(
            "#FF0000", "https://www.youtube.com/@LingMoe404"
        )
        self.btn_douyin = create_social_btn(
            "#1C0B1A",
            "https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q",
        )
        self.btn_github = create_social_btn("#24292e", "https://github.com/LingMoe404")

        v_btns.addWidget(self.btn_bilibili, 0, Qt.AlignmentFlag.AlignCenter)
        v_btns.addWidget(self.btn_youtube, 0, Qt.AlignmentFlag.AlignCenter)
        v_btns.addWidget(self.btn_douyin, 0, Qt.AlignmentFlag.AlignCenter)
        v_btns.addWidget(self.btn_github, 0, Qt.AlignmentFlag.AlignCenter)

        h_btns = QHBoxLayout()
        h_btns.addStretch(1)
        h_btns.addLayout(v_btns)
        h_btns.addStretch(1)
        content_layout.addLayout(h_btns)

        self.ver = BodyLabel(content_widget)
        self.ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ver.setTextColor(QColor("#999999"), QColor("#999999"))
        content_layout.addSpacing(10)
        content_layout.addWidget(self.ver)

        self.btn_wizard = PushButton(content_widget)
        self.btn_wizard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wizard.setMinimumWidth(140)
        self.btn_wizard.setFixedHeight(28)
        self.btn_wizard.clicked.connect(self.show_wizard)

        self.btn_wizard.setStyleSheet("""
            PushButton {
                background: transparent;
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 14px;
                color: #999999;
                font-size: 12px;
            }
            PushButton:hover {
                background: rgba(251, 114, 153, 0.08);
                color: #FB7299;
                border: 1px solid #FB7299;
            }
        """)

        h_wiz = QHBoxLayout()
        h_wiz.addStretch(1)
        h_wiz.addWidget(self.btn_wizard)
        h_wiz.addStretch(1)

        content_layout.addSpacing(8)
        content_layout.addLayout(h_wiz)

        card_grid.addWidget(content_widget, 0, 0)
        layout.addWidget(self.card)
        layout.addStretch(1)

    def retranslate_ui(self):
        """根据当前语言重新翻译界面文本。"""
        self.title.setText(tr("profile.title"))
        self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
        self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
        self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))
        self.desc.setText(tr("profile.card.author_desc"))
        self.motto.setText(tr("profile.card.author_motto"))
        self.btn_bilibili.setText(tr("profile.buttons.bilibili"))
        self.btn_youtube.setText(tr("profile.buttons.youtube"))
        self.btn_douyin.setText(tr("profile.buttons.douyin"))
        self.btn_github.setText(tr("profile.buttons.github"))
        self.ver.setText(f"Version: {VERSION} | Author: 泠萌404")
        self.btn_wizard.setText(tr("profile.buttons.show_wizard"))

    def show_wizard(self):
        """显示欢迎向导。"""
        win = self.window()
        if hasattr(win, "show_welcome_wizard"):
            win.show_welcome_wizard()


class SettingsInterface(QWidget):
    """“系统设置”界面，用于配置全局行为参数。"""

    saveRequested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("settingsInterface")
        self.init_ui()
        self.retranslate_ui()

    def init_ui(self):
        """初始化界面布局和组件。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.title = SubtitleLabel(self)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)

        self.combo_lang = ComboBox(self)
        self.combo_lang.setMinimumWidth(120)
        lang_map = translator.get_language_map()
        for lang_code, lang_name in lang_map.items():
            self.combo_lang.addItem(lang_name, userData=lang_code)
        header_layout.addWidget(self.combo_lang)

        self.combo_theme = ComboBox(self)
        self.combo_theme.setMinimumWidth(140)
        self.combo_theme.addItem(
            tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC, userData="Auto"
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.light"),
            icon=FluentIcon.BRIGHTNESS,
            userData="Light",
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.dark"),
            icon=FluentIcon.QUIET_HOURS,
            userData="Dark",
        )
        header_layout.addWidget(self.combo_theme)

        layout.addLayout(header_layout)

        self.card = CardWidget(self)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # GPU 检测超时设置
        gpu_row = QHBoxLayout()
        self.lbl_gpu_timeout = BodyLabel("硬件探测超时 (秒)", self)
        self.spin_gpu_timeout = SpinBox(self.card)
        self.spin_gpu_timeout.setRange(1, 60)
        self.spin_gpu_timeout.setMinimumHeight(36)
        gpu_row.addWidget(self.lbl_gpu_timeout)
        gpu_row.addStretch(1)
        gpu_row.addWidget(self.spin_gpu_timeout)
        card_layout.addLayout(gpu_row)

        # GPU 冷却时间设置
        cooling_row = QHBoxLayout()
        self.lbl_cooling_time = BodyLabel("核心冷却间隔 (秒)", self)
        self.spin_cooling_time = SpinBox(self.card)
        self.spin_cooling_time.setRange(0, 30)
        self.spin_cooling_time.setMinimumHeight(36)
        cooling_row.addWidget(self.lbl_cooling_time)
        cooling_row.addStretch(1)
        cooling_row.addWidget(self.spin_cooling_time)
        card_layout.addLayout(cooling_row)

        # 硬件解码加速开关
        decoding_row = QHBoxLayout()
        self.lbl_hw_decoding = BodyLabel(
            "硬件解码超载术式 (GPU Decoding Acceleration)", self
        )
        self.sw_hw_decoding = SwitchButton("开启", self.card)
        self.sw_hw_decoding.setOnText("开启")
        self.sw_hw_decoding.setOffText("关闭")
        decoding_row.addWidget(self.lbl_hw_decoding)
        decoding_row.addStretch(1)
        decoding_row.addWidget(self.sw_hw_decoding)
        card_layout.addLayout(decoding_row)

        # 启动时自动肃清缓存
        clean_row = QHBoxLayout()
        self.lbl_auto_clean = BodyLabel(
            "法阵开启时自动肃清残渣 (Auto Clean on Startup)", self
        )
        self.sw_auto_clean = SwitchButton("开启", self.card)
        self.sw_auto_clean.setOnText("开启")
        self.sw_auto_clean.setOffText("关闭")
        clean_row.addWidget(self.lbl_auto_clean)
        clean_row.addStretch(1)
        clean_row.addWidget(self.sw_auto_clean)
        card_layout.addLayout(clean_row)

        # 元数据并发读取限制
        thread_row = QHBoxLayout()
        self.lbl_thread_limit = BodyLabel("视界元数据读取并发限制 (Thread Limit)", self)
        self.spin_thread_limit = SpinBox(self.card)
        self.spin_thread_limit.setRange(1, 10)
        self.spin_thread_limit.setMinimumHeight(36)
        thread_row.addWidget(self.lbl_thread_limit)
        thread_row.addStretch(1)
        thread_row.addWidget(self.spin_thread_limit)
        card_layout.addLayout(thread_row)

        # 日志行数限制
        logcap_row = QHBoxLayout()
        self.lbl_log_cap = BodyLabel("虚空日志保存上限 (Log Cap)", self)
        self.combo_log_cap = ComboBox(self.card)
        self.combo_log_cap.addItem("1000 行", userData="1000")
        self.combo_log_cap.addItem("2000 行 (默认)", userData="2000")
        self.combo_log_cap.addItem("5000 行", userData="5000")
        self.combo_log_cap.addItem("10000 行", userData="10000")
        self.combo_log_cap.setMinimumHeight(36)
        self.combo_log_cap.setMinimumWidth(160)
        logcap_row.addWidget(self.lbl_log_cap)
        logcap_row.addStretch(1)
        logcap_row.addWidget(self.combo_log_cap)
        card_layout.addLayout(logcap_row)

        layout.addWidget(self.card)
        layout.addStretch(1)

        self.btn_save = PrimaryPushButton(FluentIcon.SAVE, "保存设置", self)
        self.btn_save.setMinimumHeight(40)
        self.btn_save.clicked.connect(self.on_save_clicked)
        layout.addWidget(self.btn_save)

    def retranslate_ui(self):
        """根据当前语言重新翻译界面文本。"""
        self.title.setText(tr("settings.title"))
        self.lbl_gpu_timeout.setText(tr("settings.gpu_timeout_label"))
        self.lbl_cooling_time.setText(
            tr("settings.gpu_cooling_time_label") or "核心冷却间隔 (秒)"
        )
        self.lbl_hw_decoding.setText(
            tr("settings.hw_decoding_label") or "硬件解码超载术式 (GPU Decoding)"
        )
        self.lbl_auto_clean.setText(
            tr("settings.auto_clean_label") or "法阵开启时自动肃清残渣 (Auto Clean)"
        )
        self.lbl_thread_limit.setText(
            tr("settings.thread_limit_label") or "视界元数据读取并发限制 (Thread Limit)"
        )
        self.lbl_log_cap.setText(
            tr("settings.log_cap_label") or "虚空日志保存上限 (Log Cap)"
        )
        self.btn_save.setText(tr("settings.save_button"))
        self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
        self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
        self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))

    def on_save_clicked(self):
        """发送请求保存设置。"""
        settings = {
            "gpu_check_timeout": str(self.spin_gpu_timeout.value()),
            "gpu_cooling_time": str(self.spin_cooling_time.value()),
            "hw_decoding": str(self.sw_hw_decoding.isChecked()),
            "auto_clean_on_launch": str(self.sw_auto_clean.isChecked()),
            "thread_limit": str(self.spin_thread_limit.value()),
            "log_cap": self.combo_log_cap.currentData(),
            "theme": self.combo_theme.currentData(),
            "language": self.combo_lang.currentData(),
        }
        self.saveRequested.emit(settings)

    def load_settings(self, settings_dict):
        """加载设置到界面控件。"""
        self.spin_gpu_timeout.setValue(int(settings_dict.get("gpu_check_timeout", 20)))

        # 语言
        lang = settings_dict.get("language", "zh_CN")
        idx = self.combo_lang.findData(lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)

        # 主题
        theme = settings_dict.get("theme", "Auto")
        theme_map = {"Auto": 0, "Light": 1, "Dark": 2}
        t_idx = theme_map.get(theme, 0)
        self.combo_theme.setCurrentIndex(t_idx)

        # 核心冷却间隔
        cooling_time = settings_dict.get("gpu_cooling_time", "3")
        self.spin_cooling_time.setValue(int(cooling_time))

        # 硬件解码超载术式
        hw_decoding = settings_dict.get("hw_decoding", "True")
        self.sw_hw_decoding.setChecked(hw_decoding == "True")

        # 自动肃清残渣
        auto_clean = settings_dict.get("auto_clean_on_launch", "True")
        self.sw_auto_clean.setChecked(auto_clean == "True")

        # 元数据读取并发数
        thread_limit = settings_dict.get("thread_limit", "4")
        self.spin_thread_limit.setValue(int(thread_limit))

        # 虚空日志保存上限
        log_cap = settings_dict.get("log_cap", "2000")
        idx_log = self.combo_log_cap.findData(log_cap)
        if idx_log >= 0:
            self.combo_log_cap.setCurrentIndex(idx_log)


class CreditsInterface(QWidget):
    """“羁绊之证”界面，显示项目贡献者名单。"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("creditsInterface")
        self.init_ui()
        self.retranslate_ui()

    def init_ui(self):
        """初始化界面布局和组件。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.title = SubtitleLabel(self)
        header_layout.addWidget(self.title)
        header_layout.addStretch(1)

        self.combo_lang = ComboBox(self)
        self.combo_lang.setMinimumWidth(120)
        lang_map = translator.get_language_map()
        for lang_code, lang_name in lang_map.items():
            self.combo_lang.addItem(lang_name, userData=lang_code)
        header_layout.addWidget(self.combo_lang)

        self.combo_theme = ComboBox(self)
        self.combo_theme.setMinimumWidth(140)
        self.combo_theme.addItem(
            tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.light"), icon=FluentIcon.BRIGHTNESS
        )
        self.combo_theme.addItem(
            tr("home.header.theme_combo.dark"), icon=FluentIcon.QUIET_HOURS
        )
        header_layout.addWidget(self.combo_theme)

        layout.addLayout(header_layout)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(24)

        h_info = QHBoxLayout()
        h_info.setSpacing(20)

        v_text = QVBoxLayout()
        v_text.setSpacing(6)

        self.contributor_name = SubtitleLabel("lose2me (REwaTLE)", card)
        self.role = BodyLabel(card)
        self.role.setTextColor(QColor("#5f6368"), QColor("#a0a0a0"))

        v_text.addWidget(self.contributor_name)
        v_text.addWidget(self.role)
        h_info.addLayout(v_text)
        h_info.addStretch(1)

        self.btn_github = PushButton(FluentIcon.GITHUB, "GitHub", card)
        self.btn_github.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/lose2me"))
        )

        self.btn_bili = PushButton(FluentIcon.VIDEO, "Bilibili", card)
        self.btn_bili.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://space.bilibili.com/341660795")
            )
        )

        h_info.addWidget(self.btn_github)
        h_info.addWidget(self.btn_bili)

        card_layout.addLayout(h_info)

        line = QFrame(card)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(128, 128, 128, 0.15);")
        card_layout.addWidget(line)

        self.intro = BodyLabel(card)
        self.intro.setWordWrap(True)
        card_layout.addWidget(self.intro)
        card_layout.addStretch(1)

        layout.addWidget(card)
        layout.addStretch(1)

    def retranslate_ui(self):
        """根据当前语言重新翻译界面文本。"""
        self.title.setText(tr("credits.title"))
        self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
        self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
        self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))
        self.role.setText(tr("credits.card.contributor_role"))
        self.intro.setText(tr("credits.card.intro"))
