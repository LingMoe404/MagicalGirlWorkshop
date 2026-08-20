"""ConfigManager tests using temp config paths (no real config.ini / Qt)."""

import os
import tempfile
import unittest

from config import DEFAULT_SETTINGS, ENC_AMF, ENC_NVENC, ENC_QSV, ENCODER_CONFIGS
from ui.config_manager import ConfigManager


class ConfigManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cfg_path = os.path.join(self._tmp.name, "config.ini")
        self.mgr = ConfigManager(config_path=self.cfg_path)

    def test_load_without_file_returns_defaults(self):
        settings, encoder_settings = self.mgr.load()
        self.assertIsInstance(settings, dict)
        self.assertIsInstance(encoder_settings, dict)
        for key, value in DEFAULT_SETTINGS.items():
            self.assertIn(key, settings)
            self.assertEqual(settings[key], value)
        for name, config in ENCODER_CONFIGS.items():
            self.assertIn(name, encoder_settings)
            for key, value in config.items():
                self.assertEqual(encoder_settings[name][key], value)

    def test_save_then_load_preserves_sections_and_values(self):
        settings, encoder_settings = self.mgr.load()
        settings["theme"] = "Dark"
        settings["save_mode"] = "Save As"
        settings["export_dir"] = r"D:\anime"
        encoder_settings[ENC_QSV]["vmaf"] = "91.5"
        encoder_settings[ENC_NVENC]["preset"] = "2"
        encoder_settings[ENC_AMF]["amf_offset"] = "-8"
        self.mgr.save(settings, encoder_settings)

        loaded_settings, loaded_encoders = self.mgr.load()
        for key, value in settings.items():
            self.assertEqual(loaded_settings[key], value)
        for name, config in encoder_settings.items():
            for key, value in config.items():
                self.assertEqual(loaded_encoders[name][key], value)

    def test_missing_keys_filled_with_defaults(self):
        self.mgr.save({"theme": "Dark"}, {ENC_QSV: {"vmaf": "90.0"}})

        loaded_settings, loaded_encoders = self.mgr.load()
        # 仅写入的部分保留，未写出的键回落到默认值
        self.assertEqual(loaded_settings["theme"], "Dark")
        for key in DEFAULT_SETTINGS:
            self.assertIn(key, loaded_settings)
        self.assertEqual(loaded_settings["encoder"], DEFAULT_SETTINGS["encoder"])
        # Encoder section 使用 ENCODER_CONFIGS 作为基线，缺失键补默认
        self.assertEqual(loaded_encoders[ENC_QSV]["vmaf"], "90.0")
        for key, value in ENCODER_CONFIGS[ENC_QSV].items():
            if key != "vmaf":
                self.assertEqual(loaded_encoders[ENC_QSV][key], value)

    def test_merge_settings_only_changes_given_keys(self):
        settings, _ = self.mgr.load()
        updates = {"theme": "Light", "language": "zh_TW"}
        merged = self.mgr.merge_settings(updates)
        self.assertEqual(merged["theme"], "Light")
        self.assertEqual(merged["language"], "zh_TW")
        # 未更新的键保持默认，未被修改
        for key in DEFAULT_SETTINGS:
            if key not in updates:
                self.assertEqual(merged[key], settings[key])
        # merge_settings 不写盘
        self.assertFalse(os.path.exists(self.cfg_path))

    def test_reset_returns_deep_copy_without_polluting_defaults(self):
        settings, encoder_settings = self.mgr.reset()
        # reset 结果与默认值一致
        for key, value in DEFAULT_SETTINGS.items():
            self.assertEqual(settings[key], value)
        for name, config in ENCODER_CONFIGS.items():
            for key, value in config.items():
                self.assertEqual(encoder_settings[name][key], value)

        # 修改 reset 返回的字典不得污染全局默认值
        settings["theme"] = "Dark"
        encoder_settings[ENC_NVENC]["preset"] = "1"
        self.assertEqual(DEFAULT_SETTINGS["theme"], "Auto")
        self.assertEqual(ENCODER_CONFIGS[ENC_NVENC]["preset"], "4")
        # 亦不得污染后续 reset 的返回值
        settings2, encoders2 = self.mgr.reset()
        self.assertEqual(settings2["theme"], "Auto")
        self.assertEqual(encoders2[ENC_NVENC]["preset"], "4")

        # 与 DEFAULT_SETTINGS / ENCODER_CONFIGS 非同一对象
        self.assertIsNot(settings, DEFAULT_SETTINGS)
        self.assertIsNot(encoder_settings, ENCODER_CONFIGS)
        self.assertIsNot(encoder_settings[ENC_QSV], ENCODER_CONFIGS[ENC_QSV])

    def test_percent_values_preserved_without_interpolation_fallback(self):
        """回归：ConfigParser 使用 BasicInterpolation 时，值含 % 会抛
        InterpolationSyntaxError 并被宽泛捕获后整份配置回落默认。
        现在统一使用 interpolation=None，应完整保留原始 % 值且不回落。"""
        # Settings 与 Encoder 值都包含 % 字面量
        settings, encoder_settings = self.mgr.load()
        settings["export_dir"] = r"D:\100% 魔法少女"
        settings["encoder"] = ENC_QSV
        settings["theme"] = "Dark"
        encoder_settings[ENC_QSV]["loudnorm"] = (
            "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
        )
        encoder_settings[ENC_NVENC]["vmaf"] = "95.5"
        expected_loudnorm = encoder_settings[ENC_QSV]["loudnorm"]
        self.mgr.save(settings, encoder_settings)

        loaded_settings, loaded_encoders = self.mgr.load()

        # 原始 % 值完整保留，未触发 InterpolationSyntaxError 回落默认
        self.assertEqual(loaded_settings["export_dir"], r"D:\100% 魔法少女")
        self.assertEqual(loaded_settings["theme"], "Dark")
        # Encoder section 同样保留
        self.assertEqual(loaded_encoders[ENC_QSV]["loudnorm"], expected_loudnorm)
        self.assertEqual(loaded_encoders[ENC_NVENC]["vmaf"], "95.5")
        # 未写出的键仍正常回落默认（证明整体未被整份丢弃）
        self.assertEqual(loaded_settings["save_mode"], DEFAULT_SETTINGS["save_mode"])
        self.assertEqual(
            loaded_settings["hw_decoding"], DEFAULT_SETTINGS["hw_decoding"]
        )
        self.assertEqual(
            loaded_encoders[ENC_QSV]["vmaf"], ENCODER_CONFIGS[ENC_QSV]["vmaf"]
        )


class ConfigManagerUIResetTests(unittest.TestCase):
    """回归：MainWindow.restore_defaults() 使用 config_manager.reset() 的结果。"""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])
        # 类级稳定临时目录：MainWindow 在 __init__ 及 restore_defaults 期间可能触发
        # 自动保存（auto_save_settings），若用 per-test 临时目录，前一个测试清理后
        # 后一个测试的 MainWindow 会把 config.ini 写到已删除目录。
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.config_path = os.path.join(cls._tmpdir.name, "config.ini")

    @classmethod
    def tearDownClass(cls):
        cls._tmpdir.cleanup()

    def _make_window(self):
        from ui.main_window import MainWindow

        mgr = ConfigManager(config_path=self.config_path)
        return MainWindow(config_manager=mgr)

    def test_restore_defaults_uses_config_manager_reset(self):
        w = self._make_window()
        try:
            # 打乱当前编码器/全局设置，验证 reset 后全部恢复默认
            w.encoder_settings[ENC_NVENC]["preset"] = "1"
            w.encoder_settings[ENC_QSV]["vmaf"] = "88.0"
            w.global_settings["theme"] = "Dark"
            w.line_vmaf.setText("88.0")
            w.line_audio.setText("320k")

            w.restore_defaults()

            # 编码器设置恢复为默认（来自 reset() 的深拷贝）
            self.assertEqual(w.encoder_settings[ENC_NVENC]["preset"], "4")
            self.assertEqual(w.encoder_settings[ENC_QSV]["vmaf"], "93.0")
            # 全局设置恢复为默认（来自 reset()）
            self.assertEqual(w.global_settings["theme"], "Auto")
            # UI 控件恢复为默认
            self.assertEqual(w.line_vmaf.text(), "93.0")
            self.assertEqual(w.line_audio.text(), "96k")

            # 深度隔离：UI 持有的 encoder_settings 与全局常量不是同一对象，
            # 修改它不会污染 ENCODER_CONFIGS / DEFAULT_SETTINGS
            w.encoder_settings[ENC_NVENC]["preset"] = "1"
            w.global_settings["theme"] = "Dark"
            self.assertEqual(ENCODER_CONFIGS[ENC_NVENC]["preset"], "4")
            self.assertEqual(DEFAULT_SETTINGS["theme"], "Auto")
        finally:
            w.deleteLater()

    def test_restore_defaults_syncs_settings_interface(self):
        w = self._make_window()
        try:
            # 修改系统设置页的控件，使其偏离默认值
            w.settings_interface.spin_gpu_timeout.setValue(42)
            w.settings_interface.spin_thread_limit.setValue(9)
            w.settings_interface.spin_cooling_time.setValue(7)
            w.settings_interface.sw_hw_decoding.setChecked(False)
            w.settings_interface.sw_auto_clean.setChecked(False)
            log_idx = w.settings_interface.combo_log_cap.findData("5000")
            if log_idx >= 0:
                w.settings_interface.combo_log_cap.setCurrentIndex(log_idx)

            w.restore_defaults()

            # 系统设置页控件恢复为 DEFAULT_SETTINGS 对应值
            self.assertEqual(
                w.settings_interface.spin_gpu_timeout.value(),
                int(DEFAULT_SETTINGS["gpu_check_timeout"]),
            )
            self.assertEqual(
                w.settings_interface.spin_thread_limit.value(),
                int(DEFAULT_SETTINGS["thread_limit"]),
            )
            self.assertEqual(
                w.settings_interface.spin_cooling_time.value(),
                int(DEFAULT_SETTINGS["gpu_cooling_time"]),
            )
            self.assertEqual(
                w.settings_interface.sw_hw_decoding.isChecked(),
                DEFAULT_SETTINGS["hw_decoding"] == "True",
            )
            self.assertEqual(
                w.settings_interface.sw_auto_clean.isChecked(),
                DEFAULT_SETTINGS["auto_clean_on_launch"] == "True",
            )
            self.assertEqual(
                w.settings_interface.combo_log_cap.currentData(),
                DEFAULT_SETTINGS["log_cap"],
            )

            # 同步后保存不会把旧值写回：临时接管 saveRequested 槽，
            # 避开 on_settings_save_requested 弹出的语言切换模态对话框
            captured = {}
            w.settings_interface.saveRequested.disconnect()
            w.settings_interface.saveRequested.connect(captured.update)
            w.settings_interface.on_save_clicked()
            self.assertEqual(
                captured["gpu_check_timeout"], DEFAULT_SETTINGS["gpu_check_timeout"]
            )
            self.assertEqual(captured["thread_limit"], DEFAULT_SETTINGS["thread_limit"])
            self.assertEqual(captured["hw_decoding"], DEFAULT_SETTINGS["hw_decoding"])
            self.assertEqual(
                captured["auto_clean_on_launch"],
                DEFAULT_SETTINGS["auto_clean_on_launch"],
            )
            self.assertEqual(captured["log_cap"], DEFAULT_SETTINGS["log_cap"])
        finally:
            w.deleteLater()

    def test_restore_defaults_non_zh_language_no_dialog_no_switch(self):
        # 临时 cwd：避免 translator 从真实 config.ini 读取语言设置
        old_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)
        try:
            from i18n.translator import translator

            original_lang = translator.current_lang
            translator.set_language("en_US")
            try:
                w = self._make_window()
                try:
                    # 使语言/主题下拉框与 settings_interface 当前选中不一致，
                    # 若信号未屏蔽将触发 on_language_changed / on_theme_changed
                    lang_idx = w.settings_interface.combo_lang.findData("en_US")
                    self.assertGreaterEqual(lang_idx, 0)
                    w.settings_interface.combo_lang.setCurrentIndex(lang_idx)
                    w.settings_interface.combo_theme.setCurrentIndex(0)

                    w.restore_defaults()

                    # 语言保持原值，未被强制切回中文
                    self.assertEqual(translator.current_lang, "en_US")
                    # 无模态对话框弹出（调用 restore_defaults 期间未阻塞即可证明，
                    # 若弹出 MessageDialog.exec() 会永久阻塞）
                    # 设置页语言/主题下拉框保持当前值，未被 load_settings 改动
                    self.assertEqual(
                        w.settings_interface.combo_lang.currentData(), "en_US"
                    )
                    self.assertEqual(
                        w.settings_interface.combo_theme.currentData(), "Auto"
                    )
                    # 其它系统设置控件已同步默认值
                    self.assertEqual(
                        w.settings_interface.spin_gpu_timeout.value(),
                        int(DEFAULT_SETTINGS["gpu_check_timeout"]),
                    )
                    self.assertEqual(
                        w.settings_interface.sw_hw_decoding.isChecked(),
                        DEFAULT_SETTINGS["hw_decoding"] == "True",
                    )
                finally:
                    w.deleteLater()
            finally:
                translator.set_language(original_lang)
        finally:
            os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
