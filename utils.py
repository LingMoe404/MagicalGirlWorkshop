# utils.py
import sys
import os
import subprocess

def get_subprocess_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

def resource_path(relative_path):
    """ 获取资源绝对路径 """
    # 1. 优先检查 EXE 同级目录 (支持用户自定义/外部工具)
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        external_path = os.path.join(base_path, relative_path)
        if os.path.exists(external_path):
            return external_path
    
    # 2. 检查内部路径 (开发环境 或 Nuitka/PyInstaller 内部解压目录)
    try:
        # 兼容 PyInstaller (sys._MEIPASS) 和 Nuitka (__file__)
        base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_path = os.path.abspath(".")

    internal_path = os.path.join(base_path, relative_path)
    if os.path.exists(internal_path):
        return internal_path

    # 3. 最后尝试当前工作目录
    return os.path.join(os.path.abspath("."), relative_path)

def tool_path(filename):
    """ 获取 tools 目录下工具的绝对路径 """
    return resource_path(os.path.join("tools", filename))

def safe_decode(bytes_data):
    if not bytes_data:
        return ""
    try:
        return bytes_data.decode('utf-8').strip()
    except UnicodeDecodeError:
        try:
            return bytes_data.decode('gbk').strip()
        except UnicodeDecodeError:
            return bytes_data.decode('utf-8', errors='ignore').strip()

def time_str_to_seconds(time_str):
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0.0

def to_long_path(path):
    """ 转换路径以支持 Windows 长路径 (超过 260 字符) """
    if os.name == 'nt':
        path = os.path.abspath(path)
        if not path.startswith('\\\\?\\'):
            return '\\\\?\\' + path
    return path

def get_default_cache_dir():
    """ 获取默认缓存目录 (软件根目录/cache) """
    base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    return os.path.join(base_path, "cache")

def get_config_path():
    """ 获取配置文件路径 (exe同级) """
    base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    return os.path.join(base_path, "config.ini")
