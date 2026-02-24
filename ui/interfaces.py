import os
import subprocess
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QFrame, QGridLayout)
from PySide6.QtGui import QIcon, QColor, QDesktopServices

from qfluentwidgets import (SubtitleLabel, StrongBodyLabel, BodyLabel,
                            PushButton, PrimaryPushButton, TextEdit, ComboBox, CardWidget, InfoBar,
                            InfoBarPosition, setTheme, Theme, FluentIcon, setThemeColor, isDarkTheme, ImageLabel,
                            IconWidget)

from config import VERSION
from i18n.translator import tr, translator
from utils import resource_path
from workers.analyzer import AnalysisWorker


class MediaInfoInterface(QWidget):
    """ “真理之眼”界面，用于分析媒体文件并显示其详细信息。 """
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
        """ 初始化界面布局和组件。 """
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
        self.combo_theme.addItem(tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC)
        self.combo_theme.addItem(tr("home.header.theme_combo.light"), icon=FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem(tr("home.header.theme_combo.dark"), icon=FluentIcon.QUIET_HOURS)
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
        """ 根据当前语言重新翻译界面文本。 """
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
        """ 如果分析线程正在运行，则停止它。 """
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
        """ 复制分析报告到剪贴板。 """
        text = self.info_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success(tr("info.infobar.copy_success.title"), tr("info.infobar.copy_success.content"), parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.warning(tr("info.infobar.copy_warning.title"), tr("info.infobar.copy_warning.content"), parent=self, position=InfoBarPosition.TOP)

    def clear_report(self):
        """ 清空当前的分析报告。 """
        self.current_path = None
        self.info_text.clear()
        self.btn_add_list.hide()
        self.stop_worker()

    def add_to_main_list(self):
        """ 请求将当前文件添加到主界面的文件列表中。 """
        if self.current_path:
            self.addFileRequested.emit(self.current_path)

    def dragEnterEvent(self, event):
        """ 处理文件拖入事件，高亮拖放区域。 """
        if event.mimeData().hasUrls():
            event.accept()
            bg_color = "#2D2023" if isDarkTheme() else "#FFF0F3"
            self.drop_card.setStyleSheet(f"CardWidget {{ border: 2px dashed #FB7299; background-color: {bg_color}; }}")
            self.eye_icon.setIcon(FluentIcon.ZOOM_IN)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """ 处理文件拖出事件，恢复拖放区域样式。 """
        self.drop_card.setStyleSheet("")
        self.eye_icon.setIcon(FluentIcon.SEARCH)

    def dropEvent(self, event):
        """ 处理文件放下事件，开始分析文件。 """
        self.drop_card.setStyleSheet("")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.analyze_file(files[0])

    def analyze_file(self, filepath):
        """ 使用后台线程分析给定的文件。 """
        self.current_path = filepath
        self.stop_worker()
        self.info_text.setHtml(f'<div style="color: #FB7299; font-size: 14px; font-family: \'Microsoft YaHei UI\';">{tr("info.analysis.in_progress")}</div>')
        self.btn_add_list.hide()

        self.worker = AnalysisWorker(filepath)
        self.worker.report_signal.connect(self.on_report_ready)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_finished(self):
        """ 分析线程完成后的清理工作。 """
        self.worker = None

    def on_report_ready(self, html, should_hide):
        """ 当分析报告准备好时，在界面上显示报告。 """
        self.info_text.setHtml(html)
        if should_hide:
            self.btn_add_list.hide()
        else:
            self.btn_add_list.show()


class ProfileInterface(QWidget):
    """ “观测者档案”界面，显示作者的个人信息和社交链接。 """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("profileInterface")
        self.init_ui()
        self.retranslate_ui()


    def init_ui(self):
        """ 初始化界面布局和组件。 """
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
        self.combo_theme.addItem(tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC)
        self.combo_theme.addItem(tr("home.header.theme_combo.light"), icon=FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem(tr("home.header.theme_combo.dark"), icon=FluentIcon.QUIET_HOURS)
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
            avatar.setStyleSheet("border: 6px solid white; background: white; border-radius: 96px;")

            h_avatar = QHBoxLayout()
            h_avatar.addStretch(1)
            h_avatar.addWidget(avatar)
            h_avatar.addStretch(1)
            content_layout.addLayout(h_avatar)

        name = SubtitleLabel("泠萌404", content_widget)
        name.setStyleSheet("font-family: 'Segoe UI Variable Display', 'Segoe UI Variable Text', 'Microsoft YaHei UI'; font-size: 36px; font-weight: bold; color: #FB7299;")
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

        self.btn_bilibili = create_social_btn("#FB7299", "https://space.bilibili.com/136850")
        self.btn_youtube = create_social_btn("#FF0000", "https://www.youtube.com/@LingMoe404")
        self.btn_douyin = create_social_btn("#1C0B1A", "https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q")
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
        """ 根据当前语言重新翻译界面文本。 """
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
        """ 显示欢迎向导。 """
        win = self.window()
        if hasattr(win, 'show_welcome_wizard'):
            win.show_welcome_wizard()


class CreditsInterface(QWidget):
    """ “羁绊之证”界面，显示项目贡献者名单。 """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("creditsInterface")
        self.init_ui()
        self.retranslate_ui()


    def init_ui(self):
        """ 初始化界面布局和组件。 """
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
        self.combo_theme.addItem(tr("home.header.theme_combo.auto"), icon=FluentIcon.SYNC)
        self.combo_theme.addItem(tr("home.header.theme_combo.light"), icon=FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem(tr("home.header.theme_combo.dark"), icon=FluentIcon.QUIET_HOURS)
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

        name = SubtitleLabel("lose2me (REwaTLE)", card)
        self.role = BodyLabel(card)
        self.role.setTextColor(QColor("#5f6368"), QColor("#a0a0a0"))

        v_text.addWidget(name)
        v_text.addWidget(self.role)
        h_info.addLayout(v_text)
        h_info.addStretch(1)

        btn_github = PushButton(FluentIcon.GITHUB, "GitHub", card)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/lose2me")))

        btn_bili = PushButton(FluentIcon.VIDEO, "Bilibili", card)
        btn_bili.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/341660795")))

        h_info.addWidget(btn_github)
        h_info.addWidget(btn_bili)

        card_layout.addLayout(h_info)

        line = QFrame(card)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(128, 128, 128, 0.15);")
        card_layout.addWidget(line)

        self.intro = BodyLabel(card)
        card_layout.addWidget(self.intro)

        grid_contrib = QGridLayout()
        grid_contrib.setSpacing(12)

        self.contributions_data = [
            ("📦", "credits.contributions.item1.title", "credits.contributions.item1.desc"),
            ("🐍", "credits.contributions.item2.title", "credits.contributions.item2.desc"),
            ("🎨", "credits.contributions.item3.title", "credits.contributions.item3.desc"),
            ("🚀", "credits.contributions.item4.title", "credits.contributions.item4.desc"),
            ("🛠️", "credits.contributions.item5.title", "credits.contributions.item5.desc"),
            ("🤖", "credits.contributions.item6.title", "credits.contributions.item6.desc")
        ]
        
        self.contribution_widgets = []
        for i, (icon, title_key, desc_key) in enumerate(self.contributions_data):
            item = QFrame(card)
            item.setStyleSheet("""
                QFrame {
                    background-color: rgba(128, 128, 128, 0.04);
                    border-radius: 8px;
                    border: 1px solid rgba(128, 128, 128, 0.08);
                }
            """)
            l_item = QHBoxLayout(item)
            l_item.setContentsMargins(12, 12, 12, 12)

            lbl_icon = BodyLabel(icon, item)
            lbl_icon.setStyleSheet("font-size: 22px; background: transparent; border: none;")

            v_desc = QVBoxLayout()
            v_desc.setSpacing(2)
            lbl_title = StrongBodyLabel(item)
            lbl_title.setStyleSheet("background: transparent; border: none;")

            lbl_desc = BodyLabel(item)
            lbl_desc.setTextColor(QColor("#707070"), QColor("#808080"))
            lbl_desc.setStyleSheet("font-size: 12px; background: transparent; border: none;")

            v_desc.addWidget(lbl_title)
            v_desc.addWidget(lbl_desc)

            l_item.addWidget(lbl_icon)
            l_item.addSpacing(10)
            l_item.addLayout(v_desc)
            l_item.addStretch(1)

            row = i // 2
            col = i % 2
            grid_contrib.addWidget(item, row, col)
            self.contribution_widgets.append((lbl_title, lbl_desc))


        card_layout.addLayout(grid_contrib)
        card_layout.addStretch(1)

        self.footer_lbl = BodyLabel(card)
        self.footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_lbl.setTextColor(QColor("#AAAAAA"), QColor("#666666"))
        card_layout.addWidget(self.footer_lbl)

        layout.addWidget(card)
        layout.addStretch(1)

    def retranslate_ui(self):
        """ 根据当前语言重新翻译界面文本。 """
        self.title.setText(tr("credits.title"))
        self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
        self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
        self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))
        self.role.setText(tr("credits.card.contributor_role"))
        self.intro.setText(tr("credits.card.intro").format(version=VERSION))
        
        for i, (_, title_key, desc_key) in enumerate(self.contributions_data):
            lbl_title, lbl_desc = self.contribution_widgets[i]
            lbl_title.setText(tr(title_key))
            lbl_desc.setText(tr(desc_key))
            
        self.footer_lbl.setText(tr("credits.card.footer"))
