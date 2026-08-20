"""配置读写服务：统一接管 config.ini 的读取、保存、合并与重置。

保持现有 `[Settings]` 与 `[Encoder:<name>]` section、键名、字符串值格式不变，
并保留“缺失键回落到默认值”的合并行为。本模块不操作 UI 控件。
"""

import configparser
import copy
import os

from config import DEFAULT_SETTINGS, ENCODER_CONFIGS
from utils import get_config_path


class ConfigManager:
    """封装 config.ini 的读写，支持注入路径便于测试。"""

    def __init__(self, config_path=None):
        # config_path 为 None 时使用默认路径（exe 同级 config.ini）
        self.config_path = config_path or get_config_path()

    def _default_settings(self):
        return DEFAULT_SETTINGS.copy()

    def _default_encoder_settings(self):
        return copy.deepcopy(ENCODER_CONFIGS)

    def load(self):
        """从配置文件加载设置。

        返回 (settings, encoder_settings)：
        - settings: [Settings] 合并后的全局设置（缺失键回落到 DEFAULT_SETTINGS）
        - encoder_settings: 各编码器 `[Encoder:<name>]` 合并后的设置（缺失键回落）
        """
        data = self._default_settings()
        encoders = self._default_encoder_settings()

        if not os.path.exists(self.config_path):
            return data, encoders

        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.config_path, encoding="utf-8")
        except Exception:  # noqa: BLE001 - 与旧行为一致：解析失败时静默回落到默认
            return data, encoders

        if "Settings" in config:
            sect = config["Settings"]
            for key in data:
                data[key] = sect.get(key, data[key])

        for enc_name in encoders:
            if enc_name in config:
                sect = config[enc_name]
                defaults = encoders[enc_name]
                for key in defaults:
                    encoders[enc_name][key] = sect.get(key, defaults[key])

        return data, encoders

    def save(self, settings, encoder_settings):
        """将设置写入配置文件。

        所有值均以字符串写入；未提供的 section 也会补齐并写入，以保持文件完整。
        """
        config = configparser.ConfigParser(interpolation=None)

        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding="utf-8")

        if "Settings" not in config:
            config["Settings"] = {}

        for key, value in settings.items():
            config["Settings"][key] = str(value)

        if encoder_settings:
            for enc_name, enc_conf in encoder_settings.items():
                if enc_name not in config:
                    config[enc_name] = {}
                for key, value in enc_conf.items():
                    config[enc_name][key] = str(value)

        with open(self.config_path, "w", encoding="utf-8") as f:
            config.write(f)

    def merge_settings(self, updates):
        """将 updates 合并到全局设置并返回新 dict，不隐式写盘。"""
        data = self._default_settings()
        if os.path.exists(self.config_path):
            try:
                config = configparser.ConfigParser(interpolation=None)
                config.read(self.config_path, encoding="utf-8")
                if "Settings" in config:
                    data.update(dict(config["Settings"]))
            except Exception:  # noqa: BLE001 - 解析失败时回落到默认值
                data = self._default_settings()
        data.update(updates)
        return data

    def reset(self):
        """返回一组全新的默认设置（深拷贝），不污染全局常量、不写盘。"""
        return self._default_settings(), self._default_encoder_settings()
