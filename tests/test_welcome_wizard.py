"""WelcomeWizard 结构测试。

验证欢迎向导从 MainWindow 抽取到 ui/welcome_wizard.py 之后：
- WelcomeWizard 可从 ui.welcome_wizard 独立导入
- welcome_wizard 模块不导入 MainWindow（避免循环依赖）
- MainWindow 只导入 WelcomeWizard 并保留 show_welcome_wizard（仍可被 showEvent 调用）
- 向导保留 pages / 语言切换 / 翻译行为；语言同步使用 parent/duck typing，
  不依赖 MainWindow 类

不依赖真实 ffprobe/ffmpeg / 不弹真实模态框。
"""

import inspect
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget
from qfluentwidgets import ComboBox

from ui.welcome_wizard import WelcomeWizard


class _ParentStub(QWidget):
    """最小宿主桩：模拟 MainWindow 的 retranslate_ui / combo_lang（duck typing）。"""

    def __init__(self):
        super().__init__()
        self.resize(800, 600)
        self.retranslate_called = False
        self.combo_lang = ComboBox(self)
        lang_map = _lang_map()
        for lang_code, lang_name in lang_map.items():
            self.combo_lang.addItem(lang_name, userData=lang_code)

    def retranslate_ui(self):
        self.retranslate_called = True


def _lang_map():
    """读取当前翻译器语言表（与向导/主窗口一致）。"""
    from i18n.translator import translator

    return translator.get_language_map()


class WelcomeWizardStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _make_wizard(self, parent=None):
        # MessageBoxBase/MaskDialogBase 需要非 None parent 来计算几何。
        # 父 stub 必须保持 Python 引用（挂到 wizard 属性上），否则被 GC 后
        # C++ 父对象销毁会连带销毁子向导。
        if parent is None:
            parent = _ParentStub()
        wiz = WelcomeWizard(parent=parent)
        wiz._test_parent = parent  # 测试中保持父对象存活
        self.addCleanup(wiz.deleteLater)
        return wiz

    # --- 1. 模块可导入 ---
    def test_welcome_wizard_importable(self):
        self.assertTrue(callable(WelcomeWizard))

    # --- 2. 不导入 MainWindow（避免循环依赖） ---
    def test_wizard_module_does_not_import_main_window(self):
        import ui.welcome_wizard as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import MainWindow", src)
        self.assertNotIn("from ui.main_window", src)
        self.assertNotIn("from .main_window", src)

    # --- 3. 向导保留 pages / 语言 / 翻译 / 按钮行为 ---
    def test_wizard_preserves_pages_and_lang_combo(self):
        wiz = self._make_wizard()
        # 5 个页面 + 标题 + 语言下拉
        self.assertEqual(len(wiz.pages_config), 5)
        self.assertEqual(wiz.view.count(), 5)
        self.assertTrue(hasattr(wiz, "lang_combo"))
        self.assertTrue(hasattr(wiz, "titleLabel"))
        # 语言下拉已填充全部语言
        self.assertGreaterEqual(wiz.lang_combo.count(), 4)
        # 按钮行为：确认键接管为 next_page（无限循环）
        self.assertTrue(callable(wiz.next_page))
        self.assertTrue(callable(wiz.retranslate_wizard))
        # 标题与页面文本已被翻译填充
        self.assertTrue(wiz.titleLabel.text())

    def test_wizard_next_page_cycles(self):
        wiz = self._make_wizard()
        start = wiz.view.currentIndex()
        wiz.next_page()
        self.assertEqual(wiz.view.currentIndex(), (start + 1) % len(wiz.pages_config))

    # --- 4. 语言切换通过 duck typing 同步宿主 ---
    def test_wizard_language_change_syncs_duck_typed_parent(self):
        stub = _ParentStub()
        wiz = self._make_wizard(parent=stub)
        idx = wiz.lang_combo.findData("en_US")
        self.assertGreaterEqual(idx, 0)

        with mock.patch("ui.welcome_wizard.translator") as m_trans:
            m_trans.current_lang = "zh_CN"
            m_trans.set_language = mock.Mock()
            # 手动触发槽（blockSignals 避免 setCurrentIndex 再次触发）
            wiz.lang_combo.blockSignals(True)
            wiz.lang_combo.setCurrentIndex(idx)
            wiz.lang_combo.blockSignals(False)
            wiz.on_wizard_language_changed(idx)

        m_trans.set_language.assert_called_once_with("en_US")
        # duck typing：宿主 retranslate_ui 被调用，combo_lang 被同步
        self.assertTrue(stub.retranslate_called)
        self.assertEqual(stub.combo_lang.currentIndex(), idx)

    # --- 5. 向导使用 parent 而非 MainWindow 类 ---
    def test_wizard_uses_parent_duck_typing_not_main_window(self):
        src = inspect.getsource(WelcomeWizard)
        # 仅断言未通过 import 引入 MainWindow 类（注释提及"MainWindow"允许）
        self.assertNotIn("from ui.main_window import", src)
        self.assertNotIn("from .main_window import", src)
        self.assertNotIn("import MainWindow", src)

    # --- 6. MainWindow 导入 WelcomeWizard 并保留 show_welcome_wizard ---
    def test_main_window_imports_wizard_and_keeps_show_method(self):
        import ui.main_window as mw
        import ui.welcome_wizard as ww

        # 主窗口模块级引用同一 WelcomeWizard（从独立模块导入）
        self.assertIs(mw.WelcomeWizard, ww.WelcomeWizard)
        self.assertTrue(hasattr(mw.MainWindow, "show_welcome_wizard"))
        # show_welcome_wizard 内部实例化 WelcomeWizard（showEvent 仍可调用）
        src = inspect.getsource(mw.MainWindow.show_welcome_wizard)
        self.assertIn("WelcomeWizard", src)


if __name__ == "__main__":
    unittest.main()
