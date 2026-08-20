"""SettingsController 结构测试。

验证设置编排从 MainWindow 抽取到 ui/settings_controller.py 之后：
- SettingsController 可从 ui.settings_controller 独立导入
- settings_controller 模块不导入 MainWindow（避免循环依赖）
- MainWindow 在 init_ui 完成后构造 settings_controller 并委托
- MainWindow 保留薄转发方法（load_settings_to_ui / restore_defaults /
  on_theme_changed / on_settings_save_requested / apply_preset_* 等），
  保持现有测试与信号连接兼容
- 主窗口行数 <=1500
- 不改变配置迁移 / 百分号配置 / 恢复默认同步系统设置 /
  非中文语言恢复行为 / 主题切换 / 预设行为

不依赖真实 ffprobe/ffmpeg。
"""

import inspect
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config import DEFAULT_SETTINGS, ENC_NVENC, ENC_QSV, ENCODER_CONFIGS
from ui.config_manager import ConfigManager
from ui.main_window import MainWindow
from ui.settings_controller import SettingsController


class _FakeWorker:
    """模拟 Duration/Thumbnail worker：不启动真实 QThread。"""

    def __init__(self, *args, **kwargs):
        self.result = mock.Mock()
        self.finished = mock.Mock()
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        pass

    def deleteLater(self):
        pass


class SettingsControllerStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.config_path = os.path.join(cls._tmpdir.name, "config.ini")

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def _make_window(self):
        w = MainWindow(config_manager=ConfigManager(config_path=self.config_path))
        w.file_list_manager.duration_worker_cls = _FakeWorker
        w.file_list_manager.thumbnail_worker_cls = _FakeWorker
        w.info_interface.stop_worker = lambda: None
        self.addCleanup(w.file_list_manager.stop_workers)
        self.addCleanup(w.info_interface.stop_worker)
        self.addCleanup(w.deleteLater)
        return w

    # --- 1. 模块可导入 ---
    def test_settings_controller_importable(self):
        self.assertTrue(callable(SettingsController))

    # --- 2. 不导入 MainWindow（避免循环依赖） ---
    def test_controller_module_does_not_import_main_window(self):
        import ui.settings_controller as mod

        src = inspect.getsource(mod)
        self.assertNotIn("import MainWindow", src)
        self.assertNotIn("from ui.main_window", src)
        self.assertNotIn("from .main_window", src)

    # --- 3. 主窗口行数 <=1500 ---
    def test_main_window_line_count_at_most_1500(self):
        main_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "ui", "main_window.py")
        )
        with open(main_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertLessEqual(
            len(lines), 1500, f"ui/main_window.py 当前 {len(lines)} 行，应 <=1500"
        )

    # --- 4. 主窗口构造 settings_controller 并委托 ---
    def test_main_window_constructs_settings_controller(self):
        w = self._make_window()
        self.assertIsInstance(w.settings_controller, SettingsController)
        # controller 显式持有主窗口
        self.assertIs(w.settings_controller.window, w)

    # --- 5. 主窗口保留薄转发方法 ---
    def test_main_window_keeps_thin_forwarding_methods(self):
        for name in [
            "load_settings_to_ui",
            "load_encoder_settings_to_ui",
            "save_current_settings",
            "restore_defaults",
            "apply_preset_light",
            "apply_preset_balanced",
            "apply_preset_heavenly",
            "on_theme_changed",
            "on_settings_save_requested",
        ]:
            self.assertTrue(hasattr(MainWindow, name), f"MainWindow.{name} 应保留转发")

    # --- 6. 转发方法委托给 controller ---
    def test_forwarding_delegates_to_controller(self):
        w = self._make_window()
        for name in [
            "load_settings_to_ui",
            "restore_defaults",
            "apply_preset_light",
            "apply_preset_balanced",
            "apply_preset_heavenly",
            "on_settings_save_requested",
        ]:
            with mock.patch.object(w.settings_controller, name) as m:
                getattr(w, name)(
                    *([{}] if name == "on_settings_save_requested" else [])
                )
                m.assert_called_once()

    # --- 7. 主题切换行为保留 ---
    def test_theme_changed_forwards_to_controller(self):
        w = self._make_window()
        with mock.patch.object(w.settings_controller, "on_theme_changed") as m:
            w.on_theme_changed(1)
            m.assert_called_once_with(1)

    # --- 8. 配置迁移 / 默认值行为保留（经转发链） ---
    def test_restore_defaults_still_resets_encoder_and_global(self):
        w = self._make_window()
        w.encoder_settings[ENC_NVENC]["preset"] = "1"
        w.encoder_settings[ENC_QSV]["vmaf"] = "88.0"
        w.global_settings["theme"] = "Dark"
        w.line_vmaf.setText("88.0")

        w.restore_defaults()

        self.assertEqual(w.encoder_settings[ENC_NVENC]["preset"], "4")
        self.assertEqual(w.encoder_settings[ENC_QSV]["vmaf"], "93.0")
        self.assertEqual(w.global_settings["theme"], "Auto")
        # 未污染全局常量
        self.assertEqual(ENCODER_CONFIGS[ENC_NVENC]["preset"], "4")
        self.assertEqual(DEFAULT_SETTINGS["theme"], "Auto")

    # --- 9. 非中文语言恢复行为保留（经转发链） ---
    def test_restore_defaults_keeps_non_zh_language(self):
        import i18n.translator as tr_mod

        old_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)
        try:
            original_lang = tr_mod.translator.current_lang
            tr_mod.translator.set_language("en_US")
            w = self._make_window()
            try:
                w.settings_interface.combo_lang.setCurrentIndex(
                    w.settings_interface.combo_lang.findData("en_US")
                )
                w.settings_interface.combo_theme.setCurrentIndex(0)
                w.restore_defaults()
                self.assertEqual(tr_mod.translator.current_lang, "en_US")
                self.assertEqual(w.settings_interface.combo_lang.currentData(), "en_US")
            finally:
                w.deleteLater()
        finally:
            tr_mod.translator.set_language(original_lang)
            os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
