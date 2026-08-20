"""设置编排控制器。

从 `ui/main_window.py` 抽出的设置编排逻辑：加载/保存/恢复默认/预设模板/
主题切换/设置页保存请求。约束：
- 本模块**不导入** MainWindow，通过显式 `window` 参数访问宿主窗口，避免循环依赖。
- 控制器内部显式持有 window，只调用现有 ConfigManager、Qt 控件以及 window 的
  薄兼容方法（`_populate_combo` / `block_signals_for_settings` /
  `toggle_export_ui` / `toggle_transcode_concurrency_ui` / `save_settings_file` /
  `auto_save_settings` / `on_language_changed` / `_update_card_style` 等）。
- 不直接操作后台线程：依赖检查、转码运行状态等一律经 window 现有方法委托。
"""

import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    InfoBar,
    InfoBarPosition,
    Theme,
    setTheme,
    setThemeColor,
)

from config import (
    DEFAULT_SETTINGS,
    ENC_AMF,
    ENC_NVENC,
    ENC_QSV,
    ENCODER_CONFIGS,
    LOG_MAX_BLOCKS,
    SAVE_MODE_OVERWRITE,
    THEMES,
)
from i18n.translator import tr, translator


class SettingsController:
    """主窗口的设置编排控制器：显式持有 window，加载/保存/恢复默认/主题/预设。"""

    def __init__(self, window):
        self.window = window

    # --- 兼容别名：被 MainWindow 转发调用时保持语义一致 ---
    @property
    def config_manager(self):
        return self.window.config_manager

    @property
    def encoder_settings(self):
        return self.window.encoder_settings

    @property
    def global_settings(self):
        return self.window.global_settings

    @global_settings.setter
    def global_settings(self, value):
        self.window.global_settings = value

    # --- 加载 ---
    def load_settings_to_ui(self):
        """从配置文件加载设置到UI。"""
        data, loaded_encoder_settings = self.config_manager.load()
        self.window.encoder_settings = loaded_encoder_settings

        # 旧版本遗留的中文标签值迁移到规范值（仅影响旧配置文件）
        data["save_mode"] = self.window.OLD_VALUE_MAP.get(
            data["save_mode"], data["save_mode"]
        )
        for enc_conf in self.window.encoder_settings.values():
            enc_conf["loudnorm_mode"] = self.window.OLD_VALUE_MAP.get(
                enc_conf["loudnorm_mode"], enc_conf["loudnorm_mode"]
            )

        if not os.path.exists(self.config_manager.config_path):
            self.window.is_first_run = True
            self.window.save_settings_file(
                DEFAULT_SETTINGS, self.window.encoder_settings
            )
        else:
            self.window.is_first_run = False

        enc_idx = 0
        if ENC_NVENC in data["encoder"]:
            enc_idx = 1
        elif ENC_AMF in data["encoder"]:
            enc_idx = 2

        self.window.last_encoder_name = self.window.combo_encoder.itemText(enc_idx)
        self.window.combo_encoder.setCurrentIndex(enc_idx)
        self.load_encoder_settings_to_ui(self.window.last_encoder_name)

        try:
            self.window.combo_theme.setCurrentIndex(THEMES.index(data["theme"]))
        except ValueError:
            self.window.combo_theme.setCurrentIndex(0)
        self.on_theme_changed(self.window.combo_theme.currentIndex())

        save_mode_index = self.window.combo_save_mode.findData(data["save_mode"])
        if save_mode_index > -1:
            self.window.combo_save_mode.setCurrentIndex(save_mode_index)
        self.window.line_export.setText(data.get("export_dir", ""))
        self.window.toggle_export_ui()

        concurrency_mode_index = self.window.combo_transcode_mode.findData(
            data.get("transcode_concurrency_mode", "auto")
        )
        if concurrency_mode_index > -1:
            self.window.combo_transcode_mode.setCurrentIndex(concurrency_mode_index)
        try:
            concurrency = int(data.get("transcode_concurrency", "2"))
        except (TypeError, ValueError):
            concurrency = 2
        self.window.spin_transcode_concurrency.setValue(max(1, min(4, concurrency)))
        self.window.toggle_transcode_concurrency_ui()

        color_mode_index = self.window.combo_color.findData(
            data.get("color_mode", "Auto")
        )
        if color_mode_index > -1:
            self.window.combo_color.setCurrentIndex(color_mode_index)

        self.global_settings = data

        # 初始加载后同步日志块数上限；非法值回退 LOG_MAX_BLOCKS
        try:
            self.window.log_manager.set_log_cap(int(data.get("log_cap")))
        except (TypeError, ValueError):
            self.window.log_manager.set_log_cap(LOG_MAX_BLOCKS)

        # Load settings to the new settings interface
        if hasattr(self.window, "settings_interface"):
            self.window.settings_interface.load_settings(data)

    def load_encoder_settings_to_ui(self, enc_name):
        """加载指定编码器的设置到UI。"""
        settings = self.window.encoder_settings.get(
            enc_name, ENCODER_CONFIGS.get(enc_name)
        )
        if not settings:
            return

        self.window.block_signals_for_settings(True)

        self.window.line_vmaf.setText(settings["vmaf"])
        self.window.line_audio.setText(settings["audio_bitrate"])
        self.window.line_loudnorm.setText(settings["loudnorm"])

        loudnorm_mode_index = self.window.combo_loudnorm.findData(
            settings["loudnorm_mode"]
        )
        if loudnorm_mode_index > -1:
            self.window.combo_loudnorm.setCurrentIndex(loudnorm_mode_index)

        self.window.sw_nv_aq.setChecked(settings["nv_aq"] == "True")
        self.window.spin_offset.setValue(int(settings.get("amf_offset", 0)))

        idx = self.window.combo_preset.findText(settings["preset"])
        if idx >= 0:
            self.window.combo_preset.setCurrentIndex(idx)
        else:
            self.window.combo_preset.setCurrentIndex(3)

        self.window.block_signals_for_settings(False)

        if ENC_NVENC in enc_name:
            self.window.lbl_aq.setText(tr("home.settings_card.nv_aq.label.nvidia"))
        elif ENC_AMF in enc_name:
            self.window.lbl_aq.setText(tr("home.settings_card.nv_aq.label.amd"))
        else:
            self.window.lbl_aq.setText(tr("home.settings_card.nv_aq.label.intel"))
        self.window.sw_nv_aq.setEnabled(True)

        is_hw = (
            (ENC_AMF in enc_name) or (ENC_NVENC in enc_name) or (ENC_QSV in enc_name)
        )
        self.window.lbl_offset.setEnabled(is_hw)
        self.window.spin_offset.setEnabled(is_hw)

    # --- 保存 ---
    def save_current_settings(self, show_tip=False):
        """保存当前UI上的所有设置到文件。"""
        curr_enc = self.window.combo_encoder.currentText()
        if curr_enc in self.window.encoder_settings:
            self.window.encoder_settings[curr_enc].update(
                {
                    "vmaf": self.window.line_vmaf.text(),
                    "audio_bitrate": self.window.line_audio.text(),
                    "preset": self.window.combo_preset.text(),
                    "loudnorm": self.window.line_loudnorm.text(),
                    "loudnorm_mode": self.window.combo_loudnorm.currentData(),
                    "nv_aq": str(self.window.sw_nv_aq.isChecked()),
                    "amf_offset": str(self.window.spin_offset.value()),
                }
            )
        settings = {
            "encoder": curr_enc,
            "theme": THEMES[self.window.combo_theme.currentIndex()],
            "save_mode": self.window.combo_save_mode.currentData(),
            "export_dir": self.window.line_export.text().strip(),
            "language": translator.current_lang,
            "color_mode": self.window.combo_color.currentData() or "Auto",
            "transcode_concurrency_mode": self.window.combo_transcode_mode.currentData()
            or "auto",
            "transcode_concurrency": str(
                self.window.spin_transcode_concurrency.value()
            ),
        }
        if hasattr(self.window, "global_settings"):
            self.global_settings.update(settings)
        self.window.save_settings_file(settings, self.window.encoder_settings)
        if show_tip:
            orig_text = self.window.btn_save_conf.text()
            self.window.btn_save_conf.setText(tr("button.save.saved"))
            self.window.btn_save_conf.setStyleSheet(
                "color: #FB7299; font-weight: bold;"
            )

            QTimer.singleShot(
                1000,
                lambda: [
                    self.window.btn_save_conf.setText(orig_text),
                    self.window.btn_save_conf.setStyleSheet(""),
                ],
            )

            InfoBar.success(
                tr("infobar.success.settings_saved.title"),
                tr("infobar.success.settings_saved.content"),
                parent=self.window,
                position=InfoBarPosition.TOP,
            )

    # --- 恢复默认 ---
    def restore_defaults(self):
        """恢复所有设置为默认值。"""
        self.window._auto_save_blocked = True
        self.window.setUpdatesEnabled(False)

        widgets_to_block = [
            self.window.combo_encoder,
            self.window.combo_preset,
            self.window.combo_theme,
            self.window.combo_save_mode,
            self.window.combo_loudnorm,
            self.window.sw_nv_aq,
            self.window.line_vmaf,
            self.window.line_audio,
            self.window.line_loudnorm,
            self.window.line_export,
            self.window.spin_offset,
            self.window.combo_color,
            self.window.combo_transcode_mode,
            self.window.spin_transcode_concurrency,
        ]
        for w in widgets_to_block:
            w.blockSignals(True)

        # 从 ConfigManager 获取默认配置（深拷贝，不污染全局常量）
        default_settings, default_encoder_settings = self.config_manager.reset()
        self.window.encoder_settings = default_encoder_settings

        current_enc = self.window.combo_encoder.currentText()
        self.load_encoder_settings_to_ui(current_enc)

        self.window.combo_theme.setCurrentIndex(0)
        self.on_theme_changed(0)

        self.window.combo_save_mode.setCurrentIndex(
            self.window.combo_save_mode.findData(SAVE_MODE_OVERWRITE)
        )
        self.window.line_export.clear()
        self.window.combo_color.setCurrentIndex(
            self.window.combo_color.findData("Auto")
        )
        self.window.combo_transcode_mode.setCurrentIndex(
            self.window.combo_transcode_mode.findData("auto")
        )
        self.window.spin_transcode_concurrency.setValue(2)
        # 直接应用默认全局设置到内存，保证 reset 返回值真实生效
        self.global_settings = default_settings
        # 恢复默认后同步日志块数上限；非法值回退 LOG_MAX_BLOCKS
        try:
            self.window.log_manager.set_log_cap(int(default_settings.get("log_cap")))
        except (TypeError, ValueError):
            self.window.log_manager.set_log_cap(LOG_MAX_BLOCKS)
        # 同步系统设置页控件，避免后续保存把旧值写回。
        # 屏蔽语言/主题控件的信号：避免 setCurrentIndex 触发 on_language_changed 弹模态框
        # 或 on_theme_changed 强制切换语言/主题；仅同步其余系统设置控件。
        # DEFAULT_SETTINGS 无 language 键，load_settings 会回落到 zh_CN，
        # 因此加载默认值后需把设置页语言下拉框恢复到当前语言，避免后续保存写回 zh_CN。
        if hasattr(self.window, "settings_interface"):
            sig_blocks = [
                self.window.settings_interface.combo_lang,
                self.window.settings_interface.combo_theme,
            ]
            orig_lang_data = self.window.settings_interface.combo_lang.currentData()
            try:
                for sig_w in sig_blocks:
                    sig_w.blockSignals(True)
                self.window.settings_interface.load_settings(default_settings)
            finally:
                # 恢复语言下拉框（仍在信号屏蔽窗口内，不触发任何槽）
                if orig_lang_data is not None:
                    lang_idx = self.window.settings_interface.combo_lang.findData(
                        orig_lang_data
                    )
                    if lang_idx >= 0:
                        self.window.settings_interface.combo_lang.setCurrentIndex(
                            lang_idx
                        )
                for sig_w in sig_blocks:
                    sig_w.blockSignals(False)

        for w in widgets_to_block:
            w.blockSignals(False)

        self.window.toggle_export_ui()
        self.window.toggle_transcode_concurrency_ui()
        self.window.setUpdatesEnabled(True)
        self.window._auto_save_blocked = False

        self.save_current_settings(show_tip=False)

        orig_text = self.window.btn_reset_conf.text()
        self.window.btn_reset_conf.setText(tr("button.reset.restored"))
        self.window.btn_reset_conf.setStyleSheet("color: #FB7299; font-weight: bold;")
        QTimer.singleShot(
            1000,
            lambda: [
                self.window.btn_reset_conf.setText(orig_text),
                self.window.btn_reset_conf.setStyleSheet(""),
            ],
        )

        InfoBar.info(
            tr("infobar.info.settings_reset.title"),
            tr("infobar.info.settings_reset.content"),
            parent=self.window,
            position=InfoBarPosition.TOP,
        )

        QApplication.processEvents()

        if self.window.transcode_controller.is_running():
            InfoBar.warning(
                tr("infobar.warning.dependency_check_skipped.title"),
                tr("infobar.warning.dependency_check_skipped.content"),
                parent=self.window,
                position=InfoBarPosition.TOP,
            )
        else:
            self.window.log(tr("log.recalibrating"), "info")
            QTimer.singleShot(200, self.window.check_dependencies)

    # --- 预设模板 ---
    def apply_preset_light(self):
        """启用轻量洗版术模板"""
        self.window.line_vmaf.setText("91.0")
        idx = self.window.combo_preset.findText("5")
        if idx >= 0:
            self.window.combo_preset.setCurrentIndex(idx)
        InfoBar.success(
            tr("infobar.success.preset_light.title"),
            tr("infobar.success.preset_light.content"),
            parent=self.window,
            position=InfoBarPosition.TOP,
        )
        self.window.auto_save_settings()

    def apply_preset_balanced(self):
        """启用黄金均衡法则模板"""
        self.window.line_vmaf.setText("93.0")
        idx = self.window.combo_preset.findText("4")
        if idx >= 0:
            self.window.combo_preset.setCurrentIndex(idx)
        InfoBar.success(
            tr("infobar.success.preset_balanced.title"),
            tr("infobar.success.preset_balanced.content"),
            parent=self.window,
            position=InfoBarPosition.TOP,
        )
        self.window.auto_save_settings()

    def apply_preset_heavenly(self):
        """启用圣殿至高典藏模板"""
        self.window.line_vmaf.setText("95.5")
        idx = self.window.combo_preset.findText("3")
        if idx >= 0:
            self.window.combo_preset.setCurrentIndex(idx)
        InfoBar.success(
            tr("infobar.success.preset_heavenly.title"),
            tr("infobar.success.preset_heavenly.content"),
            parent=self.window,
            position=InfoBarPosition.TOP,
        )
        self.window.auto_save_settings()

    # --- 主题切换 ---
    def on_theme_changed(self, index):
        """当用户在设置中更改主题时调用。"""
        if index == 0:
            setTheme(Theme.AUTO)
        elif index == 1:
            setTheme(Theme.LIGHT)
        elif index == 2:
            setTheme(Theme.DARK)
        setThemeColor("#FB7299")

        combos = [self.window.combo_theme]
        for attr in [
            "info_interface",
            "profile_interface",
            "credits_interface",
            "settings_interface",
        ]:
            if hasattr(self.window, attr):
                combos.append(getattr(self.window, attr).combo_theme)
        for c in combos:
            if c.currentIndex() != index:
                c.blockSignals(True)
                c.setCurrentIndex(index)
                c.blockSignals(False)

        QTimer.singleShot(50, self.window._update_card_style)

        QTimer.singleShot(0, self.window.update_selected_zone_border)
        QTimer.singleShot(120, self.window.update_selected_zone_border)

    # --- 设置页保存请求 ---
    def on_settings_save_requested(self, settings):
        """处理设置页面的保存请求。"""
        # 在现有已持久化设置的基础上合并本次修改，并写盘
        current_settings = self.config_manager.merge_settings(settings)
        self.global_settings = current_settings

        # 同步日志块数上限；非法值回退 LOG_MAX_BLOCKS
        try:
            self.window.log_manager.set_log_cap(
                int(self.global_settings.get("log_cap"))
            )
        except (TypeError, ValueError):
            self.window.log_manager.set_log_cap(LOG_MAX_BLOCKS)

        # Save to file
        self.window.save_settings_file(current_settings, self.window.encoder_settings)

        # Apply theme and language changes immediately
        if "theme" in settings:
            try:
                idx = THEMES.index(settings["theme"])
                self.window.combo_theme.setCurrentIndex(idx)
                self.on_theme_changed(idx)
            except ValueError:
                pass

        if "language" in settings:
            lang_code = settings["language"]
            self.window.on_language_changed(self.window.combo_lang.findData(lang_code))

        InfoBar.success(
            tr("infobar.success.settings_saved.title"),
            tr("infobar.success.settings_saved.content"),
            parent=self.window,
            position=InfoBarPosition.TOP,
        )
