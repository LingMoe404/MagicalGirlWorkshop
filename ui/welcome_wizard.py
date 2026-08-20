"""初次运行欢迎向导。

从 `ui/main_window.py` 抽出的 `WelcomeWizard`（MessageBoxBase 子类），
负责展示欢迎语/向导页与语言切换。约束：
- 本模块**不导入** MainWindow，语言同步通过 parent/duck typing：
  检测宿主是否具备 `retranslate_ui` / `combo_lang` 属性，避免循环依赖。
- 不操作任何后台线程。
"""

from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    MessageBoxBase,
    StrongBodyLabel,
    SubtitleLabel,
    isDarkTheme,
)

from i18n.translator import tr, translator


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
