import json
import subprocess
import random
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QImage
from qfluentwidgets import isDarkTheme

from i18n.translator import tr
from utils import tool_path, get_subprocess_flags, safe_decode
from config import PIX_FMT_10BIT
from .base import BaseWorker

# --- 异步获取时长线程 ---
class DurationWorker(BaseWorker):
    """
    一个用于在后台异步获取视频时长的线程。
    它使用 ffprobe 来读取媒体文件的格式和流信息。
    """
    result = Signal(str, str, float, dict) # path, duration_str, duration_sec, metadata

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.proc = None

    def stop(self):
        """ 停止正在运行的 ffprobe 进程。 """
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:
                pass
        super().stop()

    def run(self):
        """ 线程的执行体，调用 ffprobe 并解析其输出。 """
        try:
            ffprobe = tool_path("ffprobe.exe")
            # 一次性获取时长、视频编码和音频声道
            cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", self.filepath]
            
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=get_subprocess_flags()) as proc:
                self.proc = proc
                output, _ = proc.communicate()
                if not self.is_running: return
                data = json.loads(safe_decode(output))

            duration_sec = float(data.get('format', {}).get('duration', 0))
            codec = ""
            channels = None
            for s in data.get('streams', []):
                if s.get('codec_type') == 'video' and not codec:
                    # 排除封面图等干扰流，确保识别到真正的视频编码
                    if s.get('codec_name', '').lower() not in ['mjpeg', 'png', 'bmp']:
                        codec = s.get('codec_name', '').lower()
                elif s.get('codec_type') == 'audio' and channels is None:
                    channels = int(s.get('channels', 2))
            if channels is None: channels = 2

            m, s = divmod(int(duration_sec), 60)
            h, m = divmod(m, 60)
            dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            # 发送完整元数据包
            self.result.emit(self.filepath, dur_str, duration_sec, {"codec": codec, "channels": channels})
        except Exception:
            self.result.emit(self.filepath, "N/A", 0.0, {})

# --- 异步获取缩略图线程 ---
class ThumbnailWorker(BaseWorker):
    """
    一个用于在后台异步生成视频缩略图的线程。
    它使用 ffmpeg 从视频的随机位置截取一帧。
    """
    result = Signal(str, QImage) # path, image

    def __init__(self, filepath, duration_sec):
        super().__init__()
        self.filepath = filepath
        self.duration_sec = duration_sec
        self.proc = None

    def stop(self):
        """ 停止正在运行的 ffmpeg 进程。 """
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:
                pass
        super().stop()

    def run(self):
        """ 线程的执行体，调用 ffmpeg 截取帧并将其作为 QImage 发送。 """
        try:
            ffmpeg = tool_path("ffmpeg.exe")
            # 随机截取 5% 到 90% 之间的一帧，避免片头片尾黑屏
            start_time = 0.0
            if self.duration_sec > 1:
                start_time = random.uniform(self.duration_sec * 0.05, self.duration_sec * 0.9)
            
            # 截取一帧并输出为图片流
            cmd = [
                ffmpeg, "-ss", str(start_time),
                "-i", self.filepath,
                "-vframes", "1",
                "-vf", "scale=64:64:force_original_aspect_ratio=increase,crop=64:64",
                "-f", "image2",
                "-v", "error",
                "pipe:1"
            ]
            
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=get_subprocess_flags()) as proc:
                self.proc = proc
                data, _ = proc.communicate()
                if not self.is_running: return
                if data:
                    image = QImage.fromData(data)
                    if not image.isNull():
                        self.result.emit(self.filepath, image)
                        return
            
            self.result.emit(self.filepath, QImage()) # 失败返回空图像
        except Exception:
            self.result.emit(self.filepath, QImage())

# --- 异步分析线程 (防止界面卡死) ---
class AnalysisWorker(BaseWorker):
    """
    一个用于在后台异步分析媒体文件并生成HTML报告的线程。
    它使用 ffprobe 获取详细的媒体信息。
    """
    report_signal = Signal(str, bool) # HTML string, should_hide_add_button

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.proc = None

    def stop(self):
        """ 停止正在运行的 ffprobe 进程。 """
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:
                pass
        super().stop()

    def run(self):
        """ 线程的执行体，调用 ffprobe，解析输出，并生成格式化的HTML报告。 """
        ffprobe = tool_path("ffprobe.exe")
        try:
            # 调用 ffprobe 获取 JSON 格式的详细信息
            cmd = [
                ffprobe, "-v", "quiet", "-print_format", "json", 
                "-show_format", "-show_streams", "-show_chapters",
                self.filepath
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, creationflags=get_subprocess_flags()) as proc:
                self.proc = proc
                output, stderr = proc.communicate()
                if not self.is_running: return
                if proc.returncode != 0: raise Exception(safe_decode(stderr))

            data = json.loads(output)
            
            # 格式化输出 (HTML)
            is_dark = isDarkTheme()
            title_color = "#FB7299"
            container_color = "#9B59B6" if not is_dark else "#C39BD3"
            video_color = "#2ECC71" if not is_dark else "#82E0AA"
            audio_color = "#E67E22" if not is_dark else "#F5CBA7"
            subtitle_color = "#3498DB" if not is_dark else "#85C1E9"
            key_color = "#7F8C8D" if not is_dark else "#BDC3C7"
            val_color = "#2C3E50" if not is_dark else "#ECF0F1"

            html = [f'<div style="font-family: \'Cascadia Code\', \'Consolas\', \'Microsoft YaHei UI\', monospace; font-size: 13px; line-height: 1.6;">']
            html.append(f'<div style="text-align: center; margin-bottom: 15px;">')
            html.append(f'<h2 style="color: {title_color}; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">{tr("info.report.title")}</h2>')
            html.append(f'<div style="color: {key_color}; font-size: 11px; margin-top: 4px;">{self.filepath}</div>')
            html.append(f'</div>')

            # 1. 容器信息
            fmt = data.get('format', {})
            is_mkv = "matroska" in fmt.get('format_name', '').lower()
            duration_sec = float(fmt.get('duration', 0))
            m, s = divmod(int(duration_sec), 60)
            h, m = divmod(m, 60)
            duration_hms = f"{h:02d}:{m:02d}:{s:02d}"

            html.append(f'<div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid {container_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">')
            html.append(f'<b style="color: {container_color}; font-size: 14px;">{tr("info.report.container_title")}</b><br/>')
            html.append(f'<span style="color: {key_color};">{tr("info.report.format")}</span> <span style="color: {val_color};">{fmt.get("format_long_name", "Unknown")}</span><br/>')
            html.append(f'<span style="color: {key_color};">{tr("info.report.size")}</span> <span style="color: {val_color};">{int(fmt.get("size", 0))/1024/1024:.2f} MB</span><br/>')
            html.append(f'<span style="color: {key_color};">{tr("info.report.duration")}</span> <span style="color: {val_color};">{duration_sec:.2f} s ({duration_hms})</span><br/>')
            html.append(f'<span style="color: {key_color};">{tr("info.report.total_bitrate")}</span> <span style="color: {val_color};">{int(fmt.get("bit_rate", 0))/1000:.0f} kbps</span><br/>')
            html.append(f'<span style="color: {key_color};">{tr("info.report.stream_count")}</span> <span style="color: {val_color};">{len(data.get("streams", []))}</span><br/>')
            html.append('</div>')

            # 2. 流信息
            is_av1 = False
            for stream in data.get('streams', []):
                idx = stream.get('index')
                st_type = stream.get('codec_type', 'unknown').upper()
                codec_name = stream.get('codec_name', '').lower()
                codec_display = stream.get('codec_long_name', stream.get('codec_name', 'Unknown'))
                
                if st_type == 'VIDEO':
                    if 'av1' in codec_name:
                        is_av1 = True
                    html.append(f'<div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid {video_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">')
                    html.append(f'<b style="color: {video_color}; font-size: 14px;">{tr("info.report.video_title", idx=idx)}</b><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.codec")}</span> <span style="color: {val_color};">{codec_display}</span><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.profile_level")}</span> <span style="color: {val_color};">{stream.get("profile", "N/A")} @ Level {stream.get("level", "N/A")}</span><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.resolution")}</span> <span style="color: {val_color};">{stream.get("width")} x {stream.get("height")} (DAR: {stream.get("display_aspect_ratio", "N/A")})</span><br/>')
                    
                    pix_fmt = stream.get("pix_fmt", "")
                    bit_depth = stream.get("bits_per_raw_sample")
                    
                    if not bit_depth or str(bit_depth) == "0":
                        if "16le" in pix_fmt or "16be" in pix_fmt:
                            bit_depth = "16"
                        elif "14le" in pix_fmt or "14be" in pix_fmt:
                            bit_depth = "14"
                        elif "12le" in pix_fmt or "12be" in pix_fmt:
                            bit_depth = "12"
                        elif "10le" in pix_fmt or "10be" in pix_fmt or "p010" in pix_fmt:
                            bit_depth = "10"
                        elif "9le" in pix_fmt or "9be" in pix_fmt:
                            bit_depth = "9"
                        else:
                            bit_depth = "8"
                    
                    html.append(f'<span style="color: {key_color};">{tr("info.report.pix_fmt")}</span> <span style="color: {val_color};">{pix_fmt} ({bit_depth} bit)</span><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.color_space")}</span> <span style="color: {val_color};">{stream.get("color_space", "N/A")} / {stream.get("color_range", "N/A")}</span><br/>')
                    if 'bit_rate' in stream:
                        html.append(f'<span style="color: {key_color};">{tr("info.report.bitrate")}</span> <span style="color: {val_color};">{int(stream.get("bit_rate"))/1000:.0f} kbps</span><br/>')
                    html.append('</div>')
                
                elif st_type == 'AUDIO':
                    html.append(f'<div style="background: rgba(230, 126, 34, 0.08); border-left: 4px solid {audio_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">')
                    html.append(f'<b style="color: {audio_color}; font-size: 14px;">{tr("info.report.audio_title", idx=idx)}</b><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.codec")}</span> <span style="color: {val_color};">{codec_display}</span><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.sample_rate")}</span> <span style="color: {val_color};">{stream.get("sample_rate")} Hz</span><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.sample_fmt")}</span> <span style="color: {val_color};">{stream.get("sample_fmt", "N/A")}</span><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.channel_layout")}</span> <span style="color: {val_color};">{stream.get("channels")} ch ({stream.get("channel_layout", "N/A")})</span><br/>')
                    if 'bit_rate' in stream:
                        html.append(f'<span style="color: {key_color};">{tr("info.report.bitrate")}</span> <span style="color: {val_color};">{int(stream.get("bit_rate"))/1000:.0f} kbps</span><br/>')
                    html.append('</div>')
                
                elif st_type == 'SUBTITLE':
                    html.append(f'<div style="background: rgba(52, 152, 219, 0.08); border-left: 4px solid {subtitle_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">')
                    html.append(f'<b style="color: {subtitle_color}; font-size: 14px;">{tr("info.report.subtitle_title", idx=idx)}</b><br/>')
                    html.append(f'<span style="color: {key_color};">{tr("info.report.codec")}</span> <span style="color: {val_color};">{codec_display}</span><br/>')
                    if 'tags' in stream and 'language' in stream['tags']:
                        html.append(f'<span style="color: {key_color};">{tr("info.report.language")}</span> <span style="color: {val_color};">{stream["tags"]["language"]}</span><br/>')
                    html.append('</div>')

            html.append('</div>')
            
            if is_mkv and is_av1:
                html.insert(1, f'<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F1C40F, stop:1 #F39C12); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; display: inline-block; font-size: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">{tr("info.report.perfect_form")}</div>')

            should_hide = is_mkv and is_av1
            self.report_signal.emit("".join(html), should_hide)

        except Exception as e:
            err_html = f'<div style="color: #FF4E6A; font-weight: bold;">{tr("info.report.parse_error")}</div><div style="color: #999999;">{str(e)}</div>'
            self.report_signal.emit(err_html, True)