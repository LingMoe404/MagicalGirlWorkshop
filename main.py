import sys
import os
import shutil
import time
import re
import ctypes
import random
import subprocess
import json
import configparser

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize, QUrl, QPropertyAnimation, pyqtProperty, QTimer
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFileDialog, QFrame, QSpacerItem, QSizePolicy)
from PyQt6.QtGui import QIcon, QColor, QDesktopServices, QPainter, QPainterPath, QPixmap

# 引入 Fluent Widgets (Win11 风格组件)
from qfluentwidgets import (FluentWindow, SubtitleLabel, StrongBodyLabel, BodyLabel, 
                            LineEdit, PrimaryPushButton, PushButton, ProgressBar, 
                            TextEdit, SwitchButton, ComboBox, CardWidget, InfoBar, 
                            InfoBarPosition, setTheme, Theme, IconWidget, FluentIcon, setThemeColor, isDarkTheme, ImageLabel, MessageDialog)

# --- 核心工具函数 ---
def resource_path(relative_path):
    """ 获取资源绝对路径：优先找打包内部资源，其次找 exe 同级目录 """
    if hasattr(sys, '_MEIPASS'):
        # 如果是打包状态，先检查临时目录(内部资源)
        p = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(p):
            return p
    
    # 开发环境或寻找外部文件时
    base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def safe_decode(bytes_data):
    if not bytes_data: return ""
    try: return bytes_data.decode('utf-8').strip()
    except:
        try: return bytes_data.decode('gbk').strip()
        except: return bytes_data.decode('utf-8', errors='ignore').strip()

def time_str_to_seconds(time_str):
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except:
        return 0.0

DEFAULT_SETTINGS = {
    "vmaf": "93.0",
    "audio_bitrate": "96k",
    "preset": "4",
    "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
    "theme": "Auto"
}

def get_config_path():
    """ 获取配置文件路径 (exe同级) """
    base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath(".")
    return os.path.join(base_path, "config.ini")

# --- 工作线程 (负责耗时的转码任务) ---
class EncoderWorker(QThread):
    # 定义信号，用于通知 UI 更新
    log_signal = pyqtSignal(str, str) # msg, level (info/success/error)
    progress_total_signal = pyqtSignal(int)
    progress_current_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()
    ask_error_decision = pyqtSignal(str, str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_running = True
        self.is_paused = False
        self.current_proc = None

    def stop(self):
        self.is_running = False
        if self.current_proc:
            try:
                # 使用 Popen 异步执行 taskkill，避免阻塞 UI 线程导致假死
                subprocess.Popen(["taskkill", "/F", "/T", "/PID", str(self.current_proc.pid)], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            except: pass

    def set_paused(self, paused):
        self.is_paused = paused

    def set_system_awake(self, keep_awake=True):
        try:
            if keep_awake:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except: pass

    def receive_decision(self, decision):
        self.decision = decision
        self.waiting_decision = False

    def run(self):
        # 解包配置
        src_dir = self.config['src_dir']
        export_dir = self.config['export_dir']
        cache_dir = self.config['cache_dir']
        overwrite = self.config['overwrite']
        preset = self.config['preset']
        target_vmaf = self.config['vmaf']
        audio_bitrate = self.config['audio_bitrate']
        loudnorm = self.config['loudnorm']
        shutdown = self.config['shutdown']

        ffmpeg = resource_path("ffmpeg.exe")
        ffprobe = resource_path("ffprobe.exe")
        ab_av1 = resource_path("ab-av1.exe")
        
        os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        exts = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts')

        try:
            self.set_system_awake(True)
            tasks = []
            for dp, dn, filenames in os.walk(src_dir):
                for f in filenames:
                    if f.lower().endswith(exts):
                        tasks.append(os.path.join(dp, f))
            
            total_tasks = len(tasks)
            if total_tasks == 0:
                self.log_signal.emit("侦测不到任何魔力残留... (｡•ˇ‸ˇ•｡)", "error")
                self.finished_signal.emit()
                return

            self.log_signal.emit(f"捕捉到 {total_tasks} 个待净化异变体！( •̀ ω •́ )y", "info")

            for i, filepath in enumerate(tasks):
                if not self.is_running: break

                fname = os.path.basename(filepath)
                self.log_signal.emit(f"[{i+1}/{total_tasks}] 正在对 {fname} 展开固有结界...", "info")
                
                self.progress_total_signal.emit(int((i / total_tasks) * 100))
                self.progress_current_signal.emit(0)

                # 1. 探测是否已是 AV1
                try:
                    cmd_probe = [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                    raw_codec = subprocess.check_output(cmd_probe, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    codec = safe_decode(raw_codec).lower()
                    if "av1" in codec and fname.lower().endswith(".mkv"):
                        self.log_signal.emit(f" -> 此物质已是纯净形态 (AV1)，跳过~ (Pass)", "success")
                        continue
                except: pass

                # 2. 获取时长
                duration_sec = 0.0
                try:
                    cmd_dur = [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
                    out_dur = subprocess.check_output(cmd_dur, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    duration_sec = float(safe_decode(out_dur))
                except: pass

                # 3. ab-av1 搜索
                cmd_search = [
                    ab_av1, "crf-search", "-i", filepath,
                    "--encoder", "av1_qsv",
                    "--min-vmaf", str(target_vmaf),
                    "--preset", preset,
                    "--pix-format", "yuv420p10le"
                ]
                if cache_dir and os.path.isdir(cache_dir):
                    cmd_search.extend(["--temp-dir", cache_dir])

                self.log_signal.emit(" -> 正在推演最强术式 (ab-av1)...", "info")
                # 这里可以发送信号让 UI 进度条变成 indeterminate 模式，为了简化逻辑暂略

                best_icq = 24
                search_success = False
                
                try:
                    self.current_proc = subprocess.Popen(cmd_search, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    while True:
                        if not self.is_running:
                            self.current_proc.kill()
                            break
                        
                        while self.is_paused:
                            if not self.is_running: break
                            time.sleep(0.1)

                        line = self.current_proc.stdout.readline()
                        if not line and self.current_proc.poll() is not None: break
                        if line:
                            decoded = safe_decode(line)
                            match = re.search(r"crf\s+(\d+)", decoded, re.IGNORECASE)
                            if match and "VMAF" in decoded:
                                best_icq = int(match.group(1))
                                search_success = True
                    self.current_proc.wait()
                except: pass

                if not self.is_running: break

                if search_success:
                    self.log_signal.emit(f" -> 术式解析完毕 (ICQ): {best_icq} (๑•̀ㅂ•́)و✧", "success")
                else:
                    self.log_signal.emit(f" -> 解析失败，强制使用基础术式 ICQ: {best_icq} (T_T)", "error")

                # 4. FFmpeg 转码
                base_name = os.path.splitext(fname)[0]
                if cache_dir and os.path.isdir(cache_dir):
                    temp_file = os.path.join(cache_dir, f"{base_name}_{int(time.time())}.temp.mkv")
                else:
                    temp_file = os.path.join(os.path.dirname(filepath), base_name + ".temp.mkv")
                
                if overwrite:
                    final_dest = os.path.join(os.path.dirname(filepath), base_name + ".mkv")
                else:
                    if not os.path.exists(export_dir): os.makedirs(export_dir, exist_ok=True)
                    final_dest = os.path.join(export_dir, base_name + ".mkv")

                # [Fix] MP4/MOV 容器中的 mov_text 字幕无法直接 copy 到 MKV，需转为 srt
                sub_codec = "copy"
                if fname.lower().endswith(('.mp4', '.mov', '.m4v')):
                    sub_codec = "srt"

                # [关键] 针对 Ultra 7 265T 优化的参数
                cmd = [
                    ffmpeg, "-y", "-hide_banner",
                    "-init_hw_device", "qsv=hw",
                    "-i", filepath,
                    "-c:v", "av1_qsv", "-preset", preset,
                    "-global_quality:v", str(best_icq), 
                    "-pix_fmt", "p010le",
                    "-async_depth", "1", # 修复显存溢出/Invalid FrameType
                    
                    "-c:a", "libopus", "-b:a", audio_bitrate,
                    "-ar", "48000", "-ac", "2",
                    "-af", loudnorm,
                    "-c:s", sub_codec,

                    "-map", "0:v:0", 
                    "-map", "0:a:0?", 
                    "-map", "0:s?",
                    "-progress", "pipe:1",

                    temp_file
                ]

                try:
                    self.current_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startupinfo, bufsize=0)
                    err_log = []
                    while True:
                        if not self.is_running:
                            self.current_proc.kill()
                            break
                        
                        while self.is_paused:
                            if not self.is_running: break
                            time.sleep(0.1)

                        line = self.current_proc.stdout.readline()
                        if not line and self.current_proc.poll() is not None: break
                        if line:
                            d = safe_decode(line)
                            if "time=" in d and duration_sec > 0:
                                t_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d+)", d)
                                if t_match:
                                    current_sec = time_str_to_seconds(t_match.group(1))
                                    percent = int((current_sec / duration_sec) * 100)
                                    self.progress_current_signal.emit(percent)
                            
                            if "frame=" not in d:
                                err_log.append(d)
                                if len(err_log) > 20: err_log.pop(0)
                    
                    self.current_proc.wait()

                    if not self.is_running:
                        if os.path.exists(temp_file): os.remove(temp_file)
                        break

                    if self.current_proc.returncode == 0 and os.path.exists(temp_file) and os.path.getsize(temp_file) > 1024:
                        try:
                            if overwrite:
                                # 安全覆盖逻辑
                                if os.path.exists(final_dest): os.remove(final_dest)
                                shutil.move(temp_file, final_dest)
                                os.remove(filepath)
                                self.log_signal.emit(" -> 净化完成！旧世界已被重写 (Overwrite) (ﾉ>ω<)ﾉ", "success")
                            else:
                                if os.path.exists(final_dest): os.remove(final_dest)
                                shutil.move(temp_file, final_dest)
                                self.log_signal.emit(" -> 净化完成！新世界已确立 (Export) (ﾉ>ω<)ﾉ", "success")
                        except Exception as e:
                            self.log_signal.emit(f" -> 封印仪式失败: {e} (T_T)", "error")
                    else:
                        self.log_signal.emit(" -> 术式失控 (Crash)... (T_T)", "error")
                        for l in err_log: self.log_signal.emit(f"   {l}", "error")
                        if os.path.exists(temp_file): os.remove(temp_file)
                        
                        # 遇到错误时询问用户
                        if self.is_running:
                            self.waiting_decision = True
                            self.decision = None
                            self.ask_error_decision.emit("术式崩坏警告", f"任务 {fname} 遭遇未知错误。\n是否跳过此任务并继续？")
                            while self.waiting_decision and self.is_running:
                                time.sleep(0.1)
                            if self.decision == 'stop':
                                break

                except Exception as e:
                    self.log_signal.emit(f" -> 魔力逆流: {e} (×_×)", "error")

            if self.is_running:
                self.log_signal.emit(">>> 奇迹达成！(๑•̀ㅂ•́)و✧", "success")
                self.progress_total_signal.emit(100)
                self.progress_current_signal.emit(100)
                if shutdown:
                    self.log_signal.emit(">>> 60秒后强制进入休眠结界... (Sleep)", "error")
                    os.system("shutdown /s /t 60")
            else:
                self.log_signal.emit(">>> 契约被强制切断。", "error")

        except Exception as e:
            self.log_signal.emit(f"世界线变动率异常 (Fatal): {e}", "error")
        finally:
            self.set_system_awake(False)
            self.finished_signal.emit()

# --- 异步分析线程 (防止界面卡死) ---
class AnalysisWorker(QThread):
    report_signal = pyqtSignal(str)

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        ffprobe = resource_path("ffprobe.exe")
        try:
            # 调用 ffprobe 获取 JSON 格式的详细信息
            cmd = [
                ffprobe, "-v", "quiet", "-print_format", "json", 
                "-show_format", "-show_streams", "-show_chapters",
                self.filepath
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            output = subprocess.check_output(cmd, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            data = json.loads(output)
            
            # 格式化输出
            report = []
            report.append(f"📜 物质分析报告 (Report): {os.path.basename(self.filepath)}")
            report.append("="*60)
            
            # 1. 容器信息
            fmt = data.get('format', {})
            report.append(f"📦 容器形态 (Container)")
            report.append(f"   • 真名 (Format): {fmt.get('format_long_name', 'Unknown')}")
            report.append(f"   • 质量 (Size):   {int(fmt.get('size', 0))/1024/1024:.2f} MB")
            report.append(f"   • 观测时长 (Duration): {float(fmt.get('duration', 0)):.2f} s")
            report.append(f"   • 魔力流动 (Bitrate):  {int(fmt.get('bit_rate', 0))/1000:.0f} kbps")
            report.append(f"   • 标签信息 (Tags):     {json.dumps(fmt.get('tags', {}), ensure_ascii=False)}")
            report.append("-" * 60)

            # 2. 流信息
            for stream in data.get('streams', []):
                idx = stream.get('index')
                st_type = stream.get('codec_type', 'unknown').upper()
                codec = stream.get('codec_long_name', stream.get('codec_name', 'Unknown'))
                
                if st_type == 'VIDEO':
                    report.append(f"👁️ 视觉投影 (Stream #{idx} - Video)")
                    report.append(f"   • 核心编码 (Codec):    {codec}")
                    report.append(f"   • 视界范围 (Res):      {stream.get('width')} x {stream.get('height')}")
                    report.append(f"   • 帧率 (FPS):          {stream.get('r_frame_rate')} (Avg: {stream.get('avg_frame_rate')})")
                    report.append(f"   • 色彩空间 (PixFmt):   {stream.get('pix_fmt')}")
                    report.append(f"   • 描述 (Profile):      {stream.get('profile', 'N/A')} (Level {stream.get('level', 'N/A')})")
                    report.append(f"   • 色域 (Color):        {stream.get('color_primaries', 'N/A')} / {stream.get('color_transfer', 'N/A')}")
                    if 'bit_rate' in stream:
                        report.append(f"   • 强度 (Bitrate):      {int(stream.get('bit_rate'))/1000:.0f} kbps")
                
                elif st_type == 'AUDIO':
                    report.append(f"🔊 听觉共鸣 (Stream #{idx} - Audio)")
                    report.append(f"   • 核心编码 (Codec):    {codec}")
                    report.append(f"   • 采样率 (SampleRate): {stream.get('sample_rate')} Hz")
                    report.append(f"   • 声道 (Channels):     {stream.get('channels')} ({stream.get('channel_layout', 'N/A')})")
                    if 'bit_rate' in stream:
                        report.append(f"   • 强度 (Bitrate):      {int(stream.get('bit_rate'))/1000:.0f} kbps")
                
                elif st_type == 'SUBTITLE':
                    report.append(f"📝 铭文记载 (Stream #{idx} - Subtitle)")
                    report.append(f"   • 核心编码 (Codec):    {codec}")
                    if 'tags' in stream and 'language' in stream['tags']:
                        report.append(f"   • 语言 (Lang):         {stream['tags']['language']}")
                
                report.append("-" * 60)

            self.report_signal.emit("\n".join(report))

        except Exception as e:
            self.report_signal.emit(f"💥 解析失败 (Error): {str(e)}\n\n请确保 ffprobe.exe 就在身边哦！")

# --- 详细信息界面 (真理之眼) ---
class MediaInfoInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("mediaInfoInterface")
        self.setAcceptDrops(True) # 允许拖拽
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 顶部拖拽区
        self.drop_card = CardWidget(self)
        self.drop_card.setFixedHeight(180)
        card_layout = QVBoxLayout(self.drop_card)
        
        title = SubtitleLabel("真理之眼 · 解析", self.drop_card)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        hint = BodyLabel("将未知的遗物投入此地以解析... (拖拽文件)", self.drop_card)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setTextColor(QColor("#999999"), QColor("#999999"))
        
        card_layout.addStretch(1)
        card_layout.addWidget(title)
        card_layout.addWidget(hint)
        card_layout.addStretch(1)
        
        layout.addWidget(self.drop_card)
        
        # 底部信息展示区
        self.info_text = TextEdit(self)
        self.info_text.setReadOnly(True)
        self.info_text.setPlaceholderText("等待魔力注入... (Waiting for file drop)")
        # 设置等宽字体以便对齐
        self.info_text.setStyleSheet("font-family: Consolas, 'Microsoft YaHei'; font-size: 10pt;")
        layout.addWidget(self.info_text)
        
        # 复制按钮
        self.btn_copy = PrimaryPushButton("📋 誊抄鉴定结果 (Copy)", self)
        self.btn_copy.clicked.connect(self.copy_report)
        layout.addWidget(self.btn_copy, 0, Qt.AlignmentFlag.AlignRight)

    def copy_report(self):
        text = self.info_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success("誊抄完成", "鉴定报告已写入剪贴板 (Copied)", parent=self, position=InfoBarPosition.TOP)
        else:
            InfoBar.warning("空空如也", "还没有解析任何物质哦...", parent=self, position=InfoBarPosition.TOP)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            bg_color = "#2D2023" if isDarkTheme() else "#FFF0F3" # 深色模式下使用深粉色背景
            self.drop_card.setStyleSheet(f"CardWidget {{ border: 2px dashed #FB7299; background-color: {bg_color}; }}")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_card.setStyleSheet("")

    def dropEvent(self, event):
        self.drop_card.setStyleSheet("")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.analyze_file(files[0])

    def analyze_file(self, filepath):
        self.info_text.setText("✨ 正在解析物质构成... (Analyzing...)")
        
        self.worker = AnalysisWorker(filepath)
        self.worker.report_signal.connect(self.info_text.setText)
        self.worker.start()

# --- 个人资料界面 (观测者档案) ---
class ProfileInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("profileInterface")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Center Card
        self.card = CardWidget(self)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)
        
        # Title
        name = SubtitleLabel("泠萌404", self.card)
        name.setStyleSheet("font-size: 28px; font-weight: bold; color: #FB7299;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = BodyLabel("「 🌙 上班族 | 🎥 UP主 | 🛠️ 喜欢数码 」\n(🌙 9-to-5er | 🎥 Content Creator | 🛠️ Tech Geek)", self.card)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setTextColor(QColor("#999999"), QColor("#999999"))
        
        # 版本信息
        ver = BodyLabel("Version: 1.0.0 | Author: 泠萌404", self.card)
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setTextColor(QColor("#999999"), QColor("#999999"))
        
        card_layout.addStretch(1)
        
        # Avatar
        avatar_path = resource_path("lemon404.ico")
        if os.path.exists(avatar_path):
            # 强制加载 256x256 的高清图标，避免默认加载小尺寸导致模糊
            pixmap = QIcon(avatar_path).pixmap(256, 256)
            avatar = ImageLabel(pixmap, self.card)
            avatar.setFixedSize(100, 100)
            avatar.setBorderRadius(50, 50, 50, 50)
            avatar.scaledToWidth(100)
            
            h_avatar = QHBoxLayout()
            h_avatar.addStretch(1)
            h_avatar.addWidget(avatar)
            h_avatar.addStretch(1)
            card_layout.addLayout(h_avatar)
            card_layout.addSpacing(10)

        card_layout.addWidget(name)
        card_layout.addWidget(desc)
        card_layout.addWidget(ver)
        card_layout.addSpacing(30)
        
        # Buttons
        # Bilibili
        btn_bili = PushButton("📺 哔哩哔哩秘密基地", self.card)
        btn_bili.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/136850")))
        btn_bili.setFixedWidth(280)
        btn_bili.setMinimumHeight(45)
        btn_bili.setStyleSheet("PushButton { background-color: #FB7299; color: white; border: none; border-radius: 8px; font-weight: bold; font-family: 'Microsoft YaHei'; } PushButton:hover { background-color: #FF85A5; }")
        
        # Youtube
        btn_yt = PushButton("▶️ Youtube 观测站", self.card)
        btn_yt.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.youtube.com/@LingMeng404")))
        btn_yt.setFixedWidth(280)
        btn_yt.setMinimumHeight(45)
        btn_yt.setStyleSheet("PushButton { background-color: #FF0000; color: white; border: none; border-radius: 8px; font-weight: bold; font-family: 'Microsoft YaHei'; } PushButton:hover { background-color: #FF4444; }")
        
        # Douyin
        btn_douyin = PushButton("🎵 抖音记录点", self.card)
        btn_douyin.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q")))
        btn_douyin.setFixedWidth(280)
        btn_douyin.setMinimumHeight(45)
        btn_douyin.setStyleSheet("PushButton { background-color: #1C0B1A; color: white; border: none; border-radius: 8px; font-weight: bold; font-family: 'Microsoft YaHei'; } PushButton:hover { background-color: #3D2C3B; }")

        # GitHub
        btn_github = PushButton("🐙 GitHub 异次元仓库", self.card)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/Lemon4289")))
        btn_github.setFixedWidth(280)
        btn_github.setMinimumHeight(45)
        btn_github.setStyleSheet("PushButton { background-color: #24292e; color: white; border: none; border-radius: 8px; font-weight: bold; font-family: 'Microsoft YaHei'; } PushButton:hover { background-color: #444c56; }")

        # Center buttons
        for btn in [btn_bili, btn_yt, btn_douyin, btn_github]:
            h_box = QHBoxLayout()
            h_box.addStretch(1)
            h_box.addWidget(btn)
            h_box.addStretch(1)
            card_layout.addLayout(h_box)

        card_layout.addStretch(1)
        
        layout.addWidget(self.card)

# --- 主窗口 (Win11 风格) ---
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("魔法少女工坊 ")
        self.resize(800, 750)
        
        # 启用 Mica 效果 (Win11 特有半透明背景)
        self.windowEffect.setMicaEffect(self.winId())
        setThemeColor('#FB7299') # Bilibili Pink / 魔法少女粉

        # 设置窗口图标 (任务栏和左上角)
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            icon = QIcon()
            # 使用 addFile 加载多分辨率图标，配合 AppUserModelID 解决模糊问题
            icon.addFile(icon_path)
            self.setWindowIcon(icon)

        # 核心变量
        self.worker = None
        
        # 初始化 UI
        self.init_ui()
        self.load_settings_to_ui()
        
        # 欢迎语
        kaomojis = ["(｡•̀ᴗ-)✧", "(*/ω＼*)", "ヽ(✿ﾟ▽ﾟ)ノ", "(๑•̀ㅂ•́)و✧"]
        self.log(f"系统就绪... {random.choice(kaomojis)}", "info")
        
        # 启动 0.5 秒后检查结界完整性 (依赖检查)
        QTimer.singleShot(500, self.check_dependencies)

    def init_ui(self):
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 1. 标题栏区域
        header_layout = QVBoxLayout()
        title = SubtitleLabel("炼成祭坛", self)
        subtitle = BodyLabel("Intel Arc 显卡魔力驱动 · 绝对领域 Edition", self)
        subtitle.setTextColor(QColor("#999999"), QColor("#999999")) # 灰色副标题
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        self.main_layout.addLayout(header_layout)

        # 2. 卡片区域 (使用 CardWidget)
        # --- 输入输出卡片 ---
        self.card_io = CardWidget(self)
        io_layout = QVBoxLayout(self.card_io)
        
        # 视频源
        io_layout.addWidget(StrongBodyLabel("素材次元 (Source)", self.card_io))
        h1 = QHBoxLayout()
        self.line_src = LineEdit(self.card_io)
        self.line_src.setPlaceholderText("选择包含视频的文件夹...")
        self.btn_src = PushButton("浏览", self.card_io)
        self.btn_src.clicked.connect(lambda: self.browse_folder(self.line_src))
        h1.addWidget(self.line_src)
        h1.addWidget(self.btn_src)
        io_layout.addLayout(h1)

        # 缓存
        io_layout.addWidget(StrongBodyLabel("魔力回路缓冲 (Cache)", self.card_io))
        h2 = QHBoxLayout()
        self.line_cache = LineEdit(self.card_io)
        self.line_cache.setPlaceholderText("ab-av1 临时文件存放处...")
        self.btn_cache = PushButton("浏览", self.card_io)
        self.btn_cache.clicked.connect(lambda: self.browse_folder(self.line_cache))
        h2.addWidget(self.line_cache)
        h2.addWidget(self.btn_cache)
        
        self.btn_clear_cache = PushButton("🧹 净化残渣", self.card_io)
        self.btn_clear_cache.clicked.connect(self.clear_cache_files)
        h2.addWidget(self.btn_clear_cache)
        
        io_layout.addLayout(h2)
        
        self.main_layout.addWidget(self.card_io)

        # --- 参数设置卡片 ---
        self.card_settings = CardWidget(self)
        set_layout = QVBoxLayout(self.card_settings)
        
        # 第一行参数
        row1 = QHBoxLayout()
        
        v1 = QVBoxLayout()
        v1.addWidget(StrongBodyLabel("视界还原度 (VMAF)", self.card_settings))
        self.line_vmaf = LineEdit(self.card_settings)
        v1.addWidget(self.line_vmaf)
        
        v2 = QVBoxLayout()
        v2.addWidget(StrongBodyLabel("共鸣频率 (Bitrate)", self.card_settings))
        self.line_audio = LineEdit(self.card_settings)
        v2.addWidget(self.line_audio)

        v3 = QVBoxLayout()
        v3.addWidget(StrongBodyLabel("咏唱速度 (Preset)", self.card_settings))
        self.combo_preset = ComboBox(self.card_settings)
        self.combo_preset.addItems(["1", "2", "3", "4", "5", "6", "7"])
        v3.addWidget(self.combo_preset)

        v4 = QVBoxLayout()
        v4.addWidget(StrongBodyLabel("世界线风格 (Theme)", self.card_settings))
        self.combo_theme = ComboBox(self.card_settings)
        self.combo_theme.addItems(["世界线收束 (Auto)", "光之加护 (Light)", "深渊凝视 (Dark)"])
        self.combo_theme.currentIndexChanged.connect(self.on_theme_changed)
        v4.addWidget(self.combo_theme)

        row1.addLayout(v1)
        row1.addLayout(v2)
        row1.addLayout(v3)
        row1.addLayout(v4)
        set_layout.addLayout(row1)

        # 第二行参数
        set_layout.addWidget(StrongBodyLabel("音量均一化术式 (Loudnorm)", self.card_settings))
        self.line_loudnorm = LineEdit(self.card_settings)
        set_layout.addWidget(self.line_loudnorm)

        # 保存/恢复按钮
        h_btns = QHBoxLayout()
        self.btn_save_conf = PushButton("💾 铭刻记忆 (Save)", self.card_settings)
        self.btn_save_conf.clicked.connect(self.save_current_settings)
        
        self.btn_reset_conf = PushButton("↩️ 时间回溯 (Reset)", self.card_settings)
        self.btn_reset_conf.clicked.connect(self.restore_defaults)
        
        h_btns.addWidget(self.btn_save_conf)
        h_btns.addWidget(self.btn_reset_conf)
        h_btns.addStretch(1)
        set_layout.addLayout(h_btns)

        self.main_layout.addWidget(self.card_settings)

        # --- 选项与操作卡片 ---
        self.card_action = CardWidget(self)
        act_layout = QVBoxLayout(self.card_action)
        
        # 开关组
        sw_layout = QHBoxLayout()
        self.sw_save_as = SwitchButton("开辟新世界 (Save As)", self.card_action)
        self.sw_save_as.setChecked(False)
        self.sw_save_as.checkedChanged.connect(self.toggle_export_ui)
        
        self.sw_shutdown = SwitchButton("仪式后强制休眠 (Shutdown)", self.card_action)
        
        sw_layout.addWidget(self.sw_save_as)
        sw_layout.addSpacing(20)
        sw_layout.addWidget(self.sw_shutdown)
        sw_layout.addStretch(1)
        act_layout.addLayout(sw_layout)

        # 导出路径 (当不覆盖时显示)
        self.export_container = QWidget()
        exp_layout = QHBoxLayout(self.export_container)
        exp_layout.setContentsMargins(0, 5, 0, 0)
        self.line_export = LineEdit(self.export_container)
        self.line_export.setPlaceholderText("新世界坐标...")
        self.btn_export = PushButton("选择", self.export_container)
        self.btn_export.clicked.connect(lambda: self.browse_folder(self.line_export))
        exp_layout.addWidget(self.line_export)
        exp_layout.addWidget(self.btn_export)
        act_layout.addWidget(self.export_container)
        self.toggle_export_ui() # 初始化状态

        # 按钮组
        btn_layout = QHBoxLayout()
        self.btn_start = PrimaryPushButton("✨ 缔结契约 (Start)", self.card_action)
        self.btn_start.clicked.connect(self.start_task)
        self.btn_start.setMinimumHeight(40)
        
        self.btn_pause = PushButton("⏳ 时空冻结 (Pause)", self.card_action)
        self.btn_pause.clicked.connect(self.pause_task)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setMinimumHeight(40)
        
        self.btn_stop = PushButton(" 契约破弃 (Stop)", self.card_action)
        self.btn_stop.clicked.connect(self.stop_task)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(40)
        # 设置停止按钮为红色样式 (自定义QSS)
        self.btn_stop.setStyleSheet("PushButton { color: #D93652; font-weight: bold; } PushButton:disabled { color: #CCCCCC; }")

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        act_layout.addLayout(btn_layout)

        self.main_layout.addWidget(self.card_action)

        # 3. 底部状态区
        self.main_layout.addStretch(1) # 弹簧

        # 进度条
        self.lbl_current = BodyLabel("当前咏唱:", self)
        self.pbar_current = ProgressBar(self)
        self.lbl_total = BodyLabel("总体构筑:", self)
        self.pbar_total = ProgressBar(self)
        
        self.main_layout.addWidget(self.lbl_current)
        self.main_layout.addWidget(self.pbar_current)
        self.main_layout.addWidget(self.lbl_total)
        self.main_layout.addWidget(self.pbar_total)

        # 日志
        self.text_log = TextEdit(self)
        self.text_log.setReadOnly(True)
        self.text_log.setFixedHeight(120)
        self.text_log.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 13px;")
        self.main_layout.addWidget(self.text_log)

        # 署名
        footer = BodyLabel("Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | Powered by Python, PyQt6, QFluentWidgets, FFmpeg, ab-av1, Gemini", self)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setTextColor(QColor("#AAAAAA"), QColor("#AAAAAA"))
        footer.setOpenExternalLinks(True)
        self.main_layout.addWidget(footer)

        # 将主布局设置给中心部件
        w = QWidget()
        w.setObjectName("homeInterface")
        w.setLayout(self.main_layout)
        self.addSubInterface(w, FluentIcon.VIDEO, "炼成祭坛")
        
        # 添加详细信息页
        self.info_interface = MediaInfoInterface(self)
        self.addSubInterface(self.info_interface, FluentIcon.INFO, "真理之眼")
        
        # 添加个人资料页
        self.profile_interface = ProfileInterface(self)
        self.addSubInterface(self.profile_interface, FluentIcon.PEOPLE, "观测者档案")

    def load_settings_to_ui(self):
        cfg_path = get_config_path()
        config = configparser.ConfigParser()
        
        data = DEFAULT_SETTINGS.copy()
        if os.path.exists(cfg_path):
            try:
                config.read(cfg_path, encoding='utf-8')
                if "Settings" in config:
                    sect = config["Settings"]
                    data["vmaf"] = sect.get("vmaf", DEFAULT_SETTINGS["vmaf"])
                    data["audio_bitrate"] = sect.get("audio_bitrate", DEFAULT_SETTINGS["audio_bitrate"])
                    data["preset"] = sect.get("preset", DEFAULT_SETTINGS["preset"])
                    data["loudnorm"] = sect.get("loudnorm", DEFAULT_SETTINGS["loudnorm"])
                    data["theme"] = sect.get("theme", DEFAULT_SETTINGS["theme"])
            except: pass
        else:
            self.save_settings_file(DEFAULT_SETTINGS)
        
        self.line_vmaf.setText(data["vmaf"])
        self.line_audio.setText(data["audio_bitrate"])
        self.line_loudnorm.setText(data["loudnorm"])
        
        # 设置 ComboBox
        idx = -1
        for i in range(self.combo_preset.count()):
            if self.combo_preset.itemText(i) == data["preset"]:
                idx = i
                break
        if idx >= 0: self.combo_preset.setCurrentIndex(idx)
        else: self.combo_preset.setCurrentIndex(3) # Default 4
        
        # 设置主题
        theme_map = {"Auto": 0, "Light": 1, "Dark": 2}
        self.combo_theme.setCurrentIndex(theme_map.get(data["theme"], 0))
        self.on_theme_changed(self.combo_theme.currentIndex()) # 确保应用

    def save_settings_file(self, settings_dict):
        config = configparser.ConfigParser()
        config["Settings"] = settings_dict
        with open(get_config_path(), 'w', encoding='utf-8') as f:
            config.write(f)

    def save_current_settings(self):
        settings = {
            "vmaf": self.line_vmaf.text(),
            "audio_bitrate": self.line_audio.text(),
            "preset": self.combo_preset.text(),
            "loudnorm": self.line_loudnorm.text(),
            "theme": ["Auto", "Light", "Dark"][self.combo_theme.currentIndex()]
        }
        self.save_settings_file(settings)
        InfoBar.success("记忆已铭刻", "当前术式参数已写入 config.ini", parent=self, position=InfoBarPosition.TOP)

    def restore_defaults(self):
        self.line_vmaf.setText(DEFAULT_SETTINGS["vmaf"])
        self.line_audio.setText(DEFAULT_SETTINGS["audio_bitrate"])
        self.line_loudnorm.setText(DEFAULT_SETTINGS["loudnorm"])
        
        idx = -1
        for i in range(self.combo_preset.count()):
            if self.combo_preset.itemText(i) == DEFAULT_SETTINGS["preset"]:
                idx = i
                break
        if idx >= 0: self.combo_preset.setCurrentIndex(idx)
        
        self.combo_theme.setCurrentIndex(0) # Auto
        
        self.save_current_settings()
        InfoBar.info("时间回溯成功", "参数已重置为初始形态", parent=self, position=InfoBarPosition.TOP)

    def on_theme_changed(self, index):
        if index == 0:
            setTheme(Theme.AUTO)
        elif index == 1:
            setTheme(Theme.LIGHT)
        elif index == 2:
            setTheme(Theme.DARK)
        setThemeColor('#FB7299') # 重新应用主题色

    def browse_folder(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            line_edit.setText(folder)

    def toggle_export_ui(self):
        is_save_as = self.sw_save_as.isChecked()
        self.export_container.setVisible(is_save_as)
        
        # 当关闭选项且窗口可见时，尝试收缩窗口高度以适应内容
        if not is_save_as and self.isVisible():
            QApplication.processEvents()
            self.resize(self.width(), 1)

    def log(self, msg, level="info"):
        timestamp = time.strftime('%H:%M:%S')
        # 简单的 HTML 颜色格式化
        is_dark = isDarkTheme()

        # 优化深色模式下的颜色对比度
        ts_color = "#AAAAAA" if is_dark else "#888888"
        color = "#FFFFFF" if is_dark else "#000000"
        if level == "error": color = "#FF4E6A" if is_dark else "#C00000"
        elif level == "success": color = "#55E555" if is_dark else "#008800"
        elif level == "info": color = ts_color if is_dark else "#444444"
        
        html = f'<span style="color:{ts_color}">[{timestamp}]</span> <span style="color:{color}">{msg}</span>'
        self.text_log.append(html)
        # 滚动到底部
        cursor = self.text_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_log.setTextCursor(cursor)

    def clear_cache_files(self):
        cache_path = self.line_cache.text()
        if not cache_path or not os.path.exists(cache_path):
             InfoBar.warning("目标丢失", "请先指定有效的魔力缓冲区域...", parent=self, position=InfoBarPosition.TOP)
             return
        
        try:
            count = 0
            for f in os.listdir(cache_path):
                # 仅删除看起来像临时文件的文件，避免误删
                if f.endswith(".temp.mkv"):
                    os.remove(os.path.join(cache_path, f))
                    count += 1
            InfoBar.success("净化完成", f"已清除 {count} 个魔力残渣！", parent=self, position=InfoBarPosition.TOP)
        except Exception as e:
            InfoBar.error("净化失败", str(e), parent=self, position=InfoBarPosition.TOP)

    def start_task(self):
        src = self.line_src.text()
        if not src:
            InfoBar.warning(title="提示", content="请先选择视频源文件夹！", orient=Qt.Orientation.Horizontal, isClosable=True, position=InfoBarPosition.TOP, parent=self)
            return

        # 参数校验
        try:
            vmaf_val = float(self.line_vmaf.text())
        except ValueError:
            InfoBar.error("参数错误", "VMAF 必须是数字 (例如 93.0)", parent=self, position=InfoBarPosition.TOP)
            return

        config = {
            'src_dir': src,
            'export_dir': self.line_export.text(),
            'cache_dir': self.line_cache.text(),
            'overwrite': not self.sw_save_as.isChecked(), # 如果未开启"另存为"，则默认为覆盖
            'preset': self.combo_preset.text(),
            'vmaf': vmaf_val,
            'audio_bitrate': self.line_audio.text(),
            'loudnorm': self.line_loudnorm.text(),
            'shutdown': self.sw_shutdown.isChecked()
        }

        self.worker = EncoderWorker(config)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_total_signal.connect(self.pbar_total.setValue)
        self.worker.progress_current_signal.connect(self.pbar_current.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.ask_error_decision.connect(self.on_worker_error)
        
        self.worker.start()
        
        self.btn_start.setEnabled(False)
        self.btn_start.setText("✨ 奇迹发生中...")
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("⏳ 时空冻结 (Pause)")
        self.btn_stop.setEnabled(True)
        self.pbar_total.setValue(0)
        self.pbar_current.setValue(0)

    def on_worker_error(self, title, content):
        """ 处理转码失败时的弹窗询问 """
        dialog = MessageDialog(title, content, self)
        dialog.yesButton.setText("跳过并继续 (Skip)")
        dialog.cancelButton.setText("停止任务 (Stop)")
        
        self.error_countdown = 30
        
        def update_timer():
            self.error_countdown -= 1
            dialog.titleLabel.setText(f"{title} ({self.error_countdown}s 后自动跳过)")
            if self.error_countdown <= 0:
                timer.stop()
                dialog.accept() # 默认接受（继续）
        
        timer = QTimer(self)
        timer.timeout.connect(update_timer)
        timer.start(1000)
        
        dialog.titleLabel.setText(f"{title} ({self.error_countdown}s 后自动跳过)")
        res = dialog.exec()
        timer.stop()
        
        decision = 'continue' if res else 'stop'
        if self.worker:
            self.worker.receive_decision(decision)

    def stop_task(self):
        if self.worker:
            self.log(">>> 正在请求中止...", "error")
            self.worker.stop()
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)

    def pause_task(self):
        if self.worker:
            if self.worker.is_paused:
                self.worker.set_paused(False)
                self.btn_pause.setText("⏳ 时空冻结 (Pause)")
                self.log(">>> 时空流动已恢复...", "info")
            else:
                self.worker.set_paused(True)
                self.btn_pause.setText("▶️ 时空流动 (Resume)")
                self.log(">>> 固有结界已冻结 (Paused)...", "info")

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("✨ 缔结契约 (Start)")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.worker = None

    def check_dependencies(self):
        """ 启动时检查依赖组件 (二次元风格) """
        missing = []
        # 检查列表：文件名 -> 描述
        dependencies = {
            "ffmpeg.exe": "核心术式构筑 (FFmpeg)",
            "ffprobe.exe": "真理之眼组件 (FFprobe)",
            "ab-av1.exe": "极限咏唱触媒 (ab-av1)"
        }

        for exe, desc in dependencies.items():
            if not os.path.exists(resource_path(exe)):
                missing.append(f"❌ {desc} [{exe}]")

        if missing:
            title = "⚠️ 结界破损警告 (Critical Error)"
            content = (
                "呜哇！大事不好了！(>_<)\n"
                "工坊的魔力回路检测到了严重的断裂！\n\n"
                "以下核心圣遗物似乎离家出走了：\n"
                f"{chr(10).join(missing)}\n\n"
                "没有它们，炼成仪式将无法进行！\n"
                "请尽快将它们召回至工坊目录！"
            )
            
            dialog = MessageDialog(title, content, self)
            dialog.yesButton.setText("GitHub (Search)")
            dialog.cancelButton.setText("我这就去修 (OK)")
            
            if dialog.exec():
                QDesktopServices.openUrl(QUrl("https://github.com/"))
            
            # 禁用开始按钮防止报错
            self.btn_start.setEnabled(False)
            self.btn_start.setText("🚫 缺少组件")
            self.log(">>> 致命错误：关键组件缺失，系统已停摆。", "error")
        else:
            # 组件存在，进一步检查硬件兼容性
            try:
                ffmpeg_path = resource_path("ffmpeg.exe")
                
                # 1. 检查 FFmpeg 软件层面是否包含 av1_qsv 编码器
                enc_output = subprocess.check_output(
                    [ffmpeg_path, "-encoders"], 
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
                )
                
                # 2. 检查硬件层面是否支持 AV1 编码 (解决旧款 Intel 核显误报问题)
                # 尝试编码 1 帧空白画面，如果硬件不支持 av1_qsv 会直接报错返回非 0
                check_cmd = [
                    ffmpeg_path, "-f", "lavfi", "-i", "color=s=128x128", 
                    "-c:v", "av1_qsv", "-frames:v", "1", "-f", "null", "-", "-v", "error"
                ]
                hw_proc = subprocess.Popen(
                    check_cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
                )
                _, _ = hw_proc.communicate()

                if b"av1_qsv" not in enc_output:
                    self.log(">>> 警告：当前术式核心 (FFmpeg) 缺失 av1_qsv 铭文支持。", "error")
                    InfoBar.warning("术式残缺", "FFmpeg 核心未刻录 av1_qsv 术式，请下载 Full 版本以补全魔导书。", parent=self, position=InfoBarPosition.TOP)
                elif hw_proc.returncode != 0:
                    self.log(">>> 警告：未侦测到 Intel QSV AV1 魔力源。非 Arc/Ultra 适格者可能无法驱动此结界。", "error")
                    InfoBar.warning(
                        "适格者认证失败", 
                        "当前魔导器 (显卡) 似乎无法承载 AV1 禁咒 (av1_qsv)。\n请确认您装备了 Intel Arc 或 Core Ultra 系列圣遗物。", 
                        parent=self, position=InfoBarPosition.TOP, duration=5000
                    )
                else:
                    self.log(">>> 适格者认证通过：Intel QSV 动力源同步率 100%！(Ready)", "success")
            except Exception as e:
                self.log(f">>> 环境自检异常: {e}", "error")

if __name__ == '__main__':
    # 设置 AppUserModelID，将程序与 Python 解释器区分开，确保任务栏图标清晰且独立
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Lemon404.MagicWorkshop.Encoder.v1")
    except:
        pass

    # 启用高分屏支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
