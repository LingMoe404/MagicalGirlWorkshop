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
from utils import resource_path
from workers.analyzer import AnalysisWorker

class MediaInfoInterface(QWidget):
    addFileRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("mediaInfoInterface")
        self.setAcceptDrops(True) # 允许拖拽
        self.current_path = None
        self.worker = None # [Add] 初始化 worker 变量
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header row for Title and Theme Switcher
        header_layout = QHBoxLayout()
        title = SubtitleLabel("真理之眼", self)
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        # 右上角主题切换
        self.combo_theme = ComboBox(self)
        self.combo_theme.addItem("世界线收束 (Auto)", FluentIcon.SYNC)
        self.combo_theme.addItem("光之加护 (Light)", FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem("深渊凝视 (Dark)", FluentIcon.QUIET_HOURS)
        self.combo_theme.setFixedWidth(160)
        header_layout.addWidget(self.combo_theme)
        layout.addLayout(header_layout)

        # 顶部拖拽区
        self.drop_card = CardWidget(self)
        self.drop_card.setFixedHeight(200)
        card_layout = QVBoxLayout(self.drop_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        
        # [Add] 巨大的真理之眼图标
        self.eye_icon = IconWidget(FluentIcon.SEARCH, self.drop_card)
        self.eye_icon.setFixedSize(64, 64)
        h_eye = QHBoxLayout()
        h_eye.addStretch(1)
        h_eye.addWidget(self.eye_icon)
        h_eye.addStretch(1)
        card_layout.addLayout(h_eye)
        
        self.drop_title = SubtitleLabel("真理之眼 · 物质解析", self.drop_card)
        self.drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        hint = BodyLabel("将未知的遗物投入此地以窥探真理... (拖拽文件)", self.drop_card)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setTextColor(QColor("#999999"), QColor("#999999"))
        
        card_layout.addWidget(self.drop_title)
        card_layout.addWidget(hint)
        
        layout.addWidget(self.drop_card)
        
        # 底部信息展示区
        self.info_text = TextEdit(self)
        self.info_text.setReadOnly(True)
        self.info_text.setPlaceholderText("等待魔力注入... (Waiting for file drop)")
        # 统一真理之眼展示区字体
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
        
        # 底部按钮区
        bottom_layout = QHBoxLayout()
        
        self.btn_add_list = PushButton(FluentIcon.ADD, "纳入祭坛 (Add to List)", self)
        self.btn_add_list.clicked.connect(self.add_to_main_list)
        self.btn_add_list.hide()
        
        self.btn_clear = PushButton(FluentIcon.DELETE, "因果切断 (Clear)", self)
        self.btn_clear.clicked.connect(self.clear_report)
        
        self.btn_copy = PrimaryPushButton(FluentIcon.COPY, "誊抄报告 (Copy)", self)
        self.btn_copy.clicked.connect(self.copy_report)
        
        bottom_layout.addWidget(self.btn_add_list)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.btn_clear)
        bottom_layout.addWidget(self.btn_copy)
        
        layout.addLayout(bottom_layout)
        
    def stop_worker(self):
        if self.worker:
            try:
                if self.worker.isRunning():
                    self.worker.stop()
                    self.worker.quit()
                    self.worker.wait()
            except RuntimeError:
                pass # 对象已删除，忽略
            self.worker = None

    def copy_report(self):
        text = self.info_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success("誊抄完成", "鉴定报告已写入剪贴板 (Copied)", parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.warning("空空如也", "还没有解析任何物质哦...", parent=self, position=InfoBarPosition.TOP)

    def clear_report(self):
        self.current_path = None
        self.info_text.clear()
        self.btn_add_list.hide()
        self.stop_worker()

    def add_to_main_list(self):
        if self.current_path:
            self.addFileRequested.emit(self.current_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            bg_color = "#2D2023" if isDarkTheme() else "#FFF0F3" # 深色模式下使用深粉色背景
            self.drop_card.setStyleSheet(f"CardWidget {{ border: 2px dashed #FB7299; background-color: {bg_color}; }}")
            self.eye_icon.setIcon(FluentIcon.ZOOM_IN)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_card.setStyleSheet("")
        self.eye_icon.setIcon(FluentIcon.SEARCH)

    def dropEvent(self, event):
        self.drop_card.setStyleSheet("")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.analyze_file(files[0])

    def analyze_file(self, filepath):
        self.current_path = filepath
        self.stop_worker() # 确保先停止上一个任务
        self.info_text.setHtml('<div style="color: #FB7299; font-size: 14px; font-family: \'Microsoft YaHei UI\';">✨ 正在窥探真理，请稍候...</div>')
        self.btn_add_list.hide()
        
        self.worker = AnalysisWorker(filepath)
        self.worker.report_signal.connect(self.on_report_ready)
        self.worker.finished.connect(self.worker.deleteLater) # 释放分析线程
        self.worker.finished.connect(self._on_worker_finished) # [Add] 清理引用
        self.worker.start()

    def _on_worker_finished(self):
        self.worker = None

        # 统一加载提示字体
    def on_report_ready(self, html, should_hide):
        self.info_text.setHtml(html)
        if should_hide:
            self.btn_add_list.hide()
        else:
            self.btn_add_list.show()

# --- 个人资料界面 (观测者档案) ---
class ProfileInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("profileInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header row for Title and Theme Switcher
        header_layout = QHBoxLayout()
        title = SubtitleLabel("观测者档案", self) # Main page title
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        self.combo_theme = ComboBox(self)
        self.combo_theme.addItem("世界线收束 (Auto)", FluentIcon.SYNC)
        self.combo_theme.addItem("光之加护 (Light)", FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem("深渊凝视 (Dark)", FluentIcon.QUIET_HOURS)
        self.combo_theme.setFixedWidth(160)
        header_layout.addWidget(self.combo_theme)
        layout.addLayout(header_layout)

        # Center Card
        self.card = CardWidget(self)
        # 使用网格布局实现叠加效果，解决头像遮挡和位置问题
        card_grid = QGridLayout(self.card)
        card_grid.setContentsMargins(0, 0, 0, 0)
        card_grid.setSpacing(0)
        
        # 1. Banner Area (顶部装饰横幅)
        banner = QFrame(self.card)
        banner.setFixedHeight(150) # 设定横幅高度，为头像提供背景支撑
        banner.setObjectName("banner")
        banner.setStyleSheet("""
            QFrame#banner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFD1DC, stop:1 #FB7299);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        card_grid.addWidget(banner, 0, 0, Qt.AlignmentFlag.AlignTop)

        # 2. Content Area (主体内容层)
        content_widget = QWidget(self.card)
        content_layout = QVBoxLayout(content_widget)
        # 设置顶部内边距 (64px)，使 192px 的头像部分重叠在横幅上，形成悬浮视觉效果
        content_layout.setContentsMargins(30, 64, 30, 30)
        content_layout.setSpacing(20)
        
        # Avatar (头像)
        avatar_path = resource_path("LingMoe404.ico")
        if os.path.exists(avatar_path):
            pixmap = QIcon(avatar_path).pixmap(256, 256)
            avatar = ImageLabel(pixmap, content_widget)
            avatar.setFixedSize(192, 192)
            avatar.setBorderRadius(96, 96, 96, 96)
            # 添加白色描边，使其在横幅上更突出
            avatar.setStyleSheet("border: 6px solid white; background: white; border-radius: 96px;")
            
            h_avatar = QHBoxLayout()
            h_avatar.addStretch(1)
            h_avatar.addWidget(avatar)
            h_avatar.addStretch(1)
            content_layout.addLayout(h_avatar)

        # Name & Info (名称与简介)
        name = SubtitleLabel("泠萌404", content_widget)
        # 统一标题类字体
        name.setStyleSheet("font-family: 'Segoe UI Variable Display', 'Segoe UI Variable Text', 'Microsoft YaHei UI'; font-size: 36px; font-weight: bold; color: #FB7299;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(name)
        
        desc = BodyLabel("「 🌙 上班族 | 🎥 UP主 | 🛠️ 喜欢数码 」", content_widget)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setTextColor(QColor("#999999"), QColor("#999999"))
        content_layout.addWidget(desc)

        # Motto (座右铭)
        motto = BodyLabel("“在代码的海洋里寻找魔法，在数码的世界里观测真理。”", content_widget)
        motto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motto.setStyleSheet("font-style: italic; color: #666666;")
        content_layout.addWidget(motto)

        # 分割线
        line = QFrame(content_widget)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(128, 128, 128, 0.1);")
        content_layout.addWidget(line)

        # Social Buttons arranged vertically (社交按钮竖排)
        v_btns = QVBoxLayout()
        v_btns.setSpacing(12)
        
        def create_social_btn(text, color, url):
            btn = PushButton(text, content_widget)
            btn.setMinimumHeight(45)
            btn.setFixedWidth(280) # 稍微加宽按钮，使其在单列布局中更协调
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

        v_btns.addWidget(create_social_btn("📺 哔哩哔哩秘密基地", "#FB7299", "https://space.bilibili.com/136850"), 0, Qt.AlignmentFlag.AlignCenter)
        v_btns.addWidget(create_social_btn("▶️ Youtube 观测站", "#FF0000", "https://www.youtube.com/@LingMoe404"), 0, Qt.AlignmentFlag.AlignCenter)
        v_btns.addWidget(create_social_btn("🎵 抖音记录点", "#1C0B1A", "https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q"), 0, Qt.AlignmentFlag.AlignCenter)
        v_btns.addWidget(create_social_btn("🐙 GitHub 异次元仓库", "#24292e", "https://github.com/LingMoe404"), 0, Qt.AlignmentFlag.AlignCenter)
        
        h_btns = QHBoxLayout()
        h_btns.addStretch(1)
        h_btns.addLayout(v_btns)
        h_btns.addStretch(1)
        content_layout.addLayout(h_btns)

        # Version Info (版本信息)
        ver = BodyLabel(f"Version: {VERSION} | Author: 泠萌404", content_widget)
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setTextColor(QColor("#999999"), QColor("#999999"))
        content_layout.addSpacing(10)
        content_layout.addWidget(ver)

        card_grid.addWidget(content_widget, 0, 0)
        layout.addWidget(self.card)
        layout.addStretch(1)

# --- 鸣谢界面 (特别鸣谢) ---
class CreditsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("creditsInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header row for Title and Theme Switcher
        header_layout = QHBoxLayout()
        title = SubtitleLabel("羁绊之证", self)
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        # [Add] 右上角主题切换
        self.combo_theme = ComboBox(self)
        self.combo_theme.addItem("世界线收束 (Auto)", FluentIcon.SYNC)
        self.combo_theme.addItem("光之加护 (Light)", FluentIcon.BRIGHTNESS)
        self.combo_theme.addItem("深渊凝视 (Dark)", FluentIcon.QUIET_HOURS)
        self.combo_theme.setFixedWidth(160)
        header_layout.addWidget(self.combo_theme)
        layout.addLayout(header_layout)

        # Contributor Card
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(24)

        # Contributor Info Row
        h_info = QHBoxLayout()
        h_info.setSpacing(20)

        v_text = QVBoxLayout()
        v_text.setSpacing(6)
        
        name = SubtitleLabel("lose2me (REwaTLE)", card)
        role = BodyLabel("代码重构与优化 / Refactoring & Optimization", card)
        # [Fix] 移除突兀的粉色，改用更专业的中性灰 (适配深浅色)
        role.setTextColor(QColor("#5f6368"), QColor("#a0a0a0"))
        
        v_text.addWidget(name)
        v_text.addWidget(role)
        h_info.addLayout(v_text)
        h_info.addStretch(1)

        # Social Buttons
        btn_github = PushButton(FluentIcon.GITHUB, "GitHub", card)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/lose2me")))
        
        btn_bili = PushButton(FluentIcon.VIDEO, "Bilibili", card)
        btn_bili.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/341660795")))
        
        h_info.addWidget(btn_github)
        h_info.addWidget(btn_bili)

        card_layout.addLayout(h_info)
        
        # Divider
        line = QFrame(card)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(128, 128, 128, 0.15);")
        card_layout.addWidget(line)

        # Contributions Grid
        intro = BodyLabel(f"v{VERSION} 架构重构的主要推动者，贡献如下：", card)
        card_layout.addWidget(intro)

        grid_contrib = QGridLayout()
        grid_contrib.setSpacing(12)
        
        contributions = [
            ("📦", "引入 uv 包管理", "优化环境同步"),
            ("🐍", "锁定 Python 3.12", "提升运行稳定性"),
            ("🎨", "迁移至 PySide6", "拥抱开源与高性能"),
            ("🚀", "采用 Nuitka 编译", "体积更小、启动更快"),
            ("🛠️", "重构工具链", "支持灵活分发"),
            ("🤖", "自动化 CI 构建", "实现云端自动打包")
        ]

        for i, (icon, title, desc) in enumerate(contributions):
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
            lbl_title = StrongBodyLabel(title, item)
            lbl_title.setStyleSheet("background: transparent; border: none;")
            
            lbl_desc = BodyLabel(desc, item)
            lbl_desc.setTextColor(QColor("#707070"), QColor("#808080")) # 使用更清晰的灰色
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

        card_layout.addLayout(grid_contrib)
        card_layout.addStretch(1)
        
        # Footer Thanks
        footer_lbl = BodyLabel("Special Thanks to: PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", card)
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_lbl.setTextColor(QColor("#AAAAAA"), QColor("#666666"))
        card_layout.addWidget(footer_lbl)

        layout.addWidget(card)
        layout.addStretch(1)