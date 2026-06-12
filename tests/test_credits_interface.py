import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from i18n.translator import translator
from ui.interfaces import CreditsInterface


class CreditsInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.previous_language = translator.current_lang
        translator.current_lang = "zh_CN"

    def tearDown(self):
        translator.current_lang = self.previous_language

    def test_credits_page_is_a_compact_memorial_card(self):
        page = CreditsInterface()
        self.addCleanup(page.close)

        self.assertEqual(page.contributor_name.text(), "lose2me (REwaTLE)")
        self.assertEqual(page.role.text(), "启蒙协力")
        self.assertEqual(
            page.intro.text(),
            "感谢在工坊早期分享开发经验与工具链思路。\n\n"
            "那些最初的指引，已经成为独立探索更强术式的起点。",
        )
        self.assertEqual(page.btn_github.text(), "GitHub")
        self.assertEqual(page.btn_bili.text(), "Bilibili")
        self.assertFalse(hasattr(page, "contributions_data"))
        self.assertFalse(hasattr(page, "contribution_widgets"))
        self.assertFalse(hasattr(page, "footer_lbl"))


if __name__ == "__main__":
    unittest.main()
