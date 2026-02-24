# i18n/translator.py
import os
import importlib
from config import (
    DEFAULT_SETTINGS
)
import configparser
from utils import (
    get_config_path
)


class Translator:
    def __init__(self):
        self.locales_dir_path = 'i18n/locales'
        self.locales_module_path = 'i18n.locales'
        self.languages = {}
        self.language_map = {}
        # Default to 'en_US' if the system's locale is not supported
        self.current_lang = 'zh_CN'
        self._load_languages()
        self.load_language_setting()


    def _load_languages(self):
        self.languages = {}
        self.language_map = {}
        if not os.path.exists(self.locales_dir_path):
            return
        
        for filename in os.listdir(self.locales_dir_path):
            if filename.endswith('.py') and not filename.startswith('__'):
                locale_name = filename[:-3]
                try:
                    module = importlib.import_module(f'.{locale_name}', self.locales_module_path)
                    if hasattr(module, 'translation') and hasattr(module, 'language_name'):
                        self.languages[locale_name] = module.translation
                        self.language_map[locale_name] = module.language_name
                except ImportError as e:
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
