# i18n/translator.py
import os
import importlib
import pkgutil
import configparser
from config import (
    DEFAULT_SETTINGS
)
from utils import (
    get_config_path
)

# 导入语言包的根目录，作为动态扫描的锚点
import i18n.locales

class Translator:
    def __init__(self):
        self.languages = {}
        self.language_map = {}
        # Default to 'zh_CN'
        self.current_lang = 'zh_CN'
        self._load_languages()
        self.load_language_setting()


    def _load_languages(self):
        self.languages = {}
        self.language_map = {}
        
        # 【核心魔法】使用 pkgutil 动态遍历模块，而非物理文件
        # 无论是在本地源码环境，还是被 Nuitka 编译成二进制，它都能精准捕捉所有语言模块
        for _, locale_name, _ in pkgutil.iter_modules(i18n.locales.__path__):
            try:
                # 动态导入每个扫描到的模块 (例如 'i18n.locales.zh_CN')
                module = importlib.import_module(f'i18n.locales.{locale_name}')
                
                # 验证模块是否包含所需的变量
                if hasattr(module, 'translation') and hasattr(module, 'language_name'):
                    self.languages[locale_name] = module.translation
                    self.language_map[locale_name] = module.language_name
            except Exception as e:
                print(f"Could not import {locale_name} translations: {e}")


    def set_language(self, lang):
        if lang in self.languages:
            self.current_lang = lang
            self.save_language_setting(lang)
        else:
            print(f"Language '{lang}' not supported.")

    def get_available_languages(self):
        return list(self.languages.keys())

    def get_language_map(self):
        return self.language_map

    def tr(self, key, *args, **kwargs):
        translation = self.languages.get(self.current_lang, {}).get(key, key)
        if args or kwargs:
            try:
                return translation.format(*args, **kwargs)
            except (KeyError, IndexError):
                # Fallback if format fails
                return key
        return translation
    
    def load_language_setting(self):
        cfg_path = get_config_path()
        config = configparser.ConfigParser()
        if os.path.exists(cfg_path):
            try:
                config.read(cfg_path, encoding='utf-8')
                if "Settings" in config:
                    lang = config["Settings"].get("language", self.current_lang)
                    if lang in self.languages:
                        self.current_lang = lang
            except Exception:
                pass

    def save_language_setting(self, lang):
        cfg_path = get_config_path()
        config = configparser.ConfigParser()
        try:
            if os.path.exists(cfg_path):
                config.read(cfg_path, encoding='utf-8')
            
            if "Settings" not in config:
                config["Settings"] = {}
            
            config["Settings"]["language"] = lang

            with open(cfg_path, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            print(f"Error saving language setting: {e}")


# Global translator instance
translator = Translator()

def tr(key, *args, **kwargs):
    return translator.tr(key, *args, **kwargs)
