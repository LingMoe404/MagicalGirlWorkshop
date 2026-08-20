import json
import random
import subprocess

from PySide6.QtCore import Signal
from PySide6.QtGui import QImage
from qfluentwidgets import isDarkTheme

from i18n.translator import tr
from utils import get_subprocess_flags, safe_decode, tool_path

from .base import BaseWorker
from .media_report import build_media_report


# --- 异步获取时长线程 ---
class DurationWorker(BaseWorker):
    """
    一个用于在后台异步获取视频时长的线程。
    它使用 ffprobe 来读取媒体文件的格式和流信息。
    """

    result = Signal(str, str, float, dict)  # path, duration_str, duration_sec, metadata

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.proc = None

    def stop(self):
        """停止正在运行的 ffprobe 进程。"""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:  # noqa: S110, BLE001
                pass
        super().stop()

    def run(self):
        """线程的执行体，调用 ffprobe 并解析其输出。"""
        try:
            ffprobe = tool_path("ffprobe.exe")
            # 一次性获取时长、视频编码和音频声道
            cmd = [
                ffprobe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                self.filepath,
            ]

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=get_subprocess_flags(),
            ) as proc:
                self.proc = proc
                output, _ = proc.communicate()
                if not self.is_running:
                    return
                data = json.loads(safe_decode(output))

            duration_sec = float(data.get("format", {}).get("duration", 0))
            codec = ""
            channels = None
            pix_fmt = ""
            color_space = ""
            color_transfer = ""
            color_primaries = ""
            has_dovi = False

            for s in data.get("streams", []):
                if s.get("codec_type") == "video":
                    if s.get("codec_name", "").lower() not in ["mjpeg", "png", "bmp"]:
                        if not codec:
                            codec = s.get("codec_name", "").lower()
                        pix_fmt = s.get("pix_fmt", "")
                        color_space = s.get("color_space", "")
                        color_transfer = s.get("color_transfer", "")
                        color_primaries = s.get("color_primaries", "")

                        # 检测杜比视界元数据
                        side_data_list = s.get("side_data_list", [])
                        for sd in side_data_list:
                            sd_type = sd.get("side_data_type", "")
                            if (
                                "Dolby Vision" in sd_type
                                or "dolby vision" in sd_type.lower()
                            ):
                                has_dovi = True
                elif s.get("codec_type") == "audio" and channels is None:
                    channels = int(s.get("channels", 2))
            if channels is None:
                channels = 2

            m, s = divmod(int(duration_sec), 60)
            h, m = divmod(m, 60)
            dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            # 发送完整元数据包
            self.result.emit(
                self.filepath,
                dur_str,
                duration_sec,
                {
                    "codec": codec,
                    "channels": channels,
                    "pix_fmt": pix_fmt,
                    "color_space": color_space,
                    "color_transfer": color_transfer,
                    "color_primaries": color_primaries,
                    "has_dovi": has_dovi,
                },
            )
        except Exception:  # noqa: BLE001
            self.result.emit(self.filepath, "N/A", 0.0, {})


# --- 异步获取缩略图线程 ---
class ThumbnailWorker(BaseWorker):
    """
    一个用于在后台异步生成视频缩略图的线程。
    它使用 ffmpeg 从视频的随机位置截取一帧。
    """

    result = Signal(str, QImage)  # path, image

    def __init__(self, filepath, duration_sec):
        super().__init__()
        self.filepath = filepath
        self.duration_sec = duration_sec
        self.proc = None

    def stop(self):
        """停止正在运行的 ffmpeg 进程。"""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:  # noqa: S110, BLE001
                pass
        super().stop()

    def run(self):
        """线程的执行体，调用 ffmpeg 截取帧并将其作为 QImage 发送。"""
        try:
            ffmpeg = tool_path("ffmpeg.exe")
            # 随机截取 5% 到 90% 之间的一帧，避免片头片尾黑屏
            start_time = 0.0
            if self.duration_sec > 1:
                start_time = random.uniform(
                    self.duration_sec * 0.05, self.duration_sec * 0.9
                )

            # 截取一帧并输出为图片流
            cmd = [
                ffmpeg,
                "-ss",
                str(start_time),
                "-i",
                self.filepath,
                "-vframes",
                "1",
                "-vf",
                "scale=64:64:force_original_aspect_ratio=increase,crop=64:64",
                "-f",
                "image2",
                "-v",
                "error",
                "pipe:1",
            ]

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=get_subprocess_flags(),
            ) as proc:
                self.proc = proc
                data, _ = proc.communicate()
                if not self.is_running:
                    return
                if data:
                    image = QImage.fromData(data)
                    if not image.isNull():
                        self.result.emit(self.filepath, image)
                        return

            self.result.emit(self.filepath, QImage())  # 失败返回空图像
        except Exception:  # noqa: BLE001
            self.result.emit(self.filepath, QImage())


# --- 异步分析线程 (防止界面卡死) ---
class AnalysisWorker(BaseWorker):
    """
    一个用于在后台异步分析媒体文件并生成HTML报告的线程。
    它使用 ffprobe 获取详细的媒体信息。
    """

    report_signal = Signal(str, bool)  # HTML string, should_hide_add_button

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.proc = None

    def stop(self):
        """停止正在运行的 ffprobe 进程。"""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.kill()
            except Exception:  # noqa: S110, BLE001
                pass
        super().stop()

    def run(self):
        """线程的执行体，调用 ffprobe，解析输出，并生成格式化的HTML报告。"""
        ffprobe = tool_path("ffprobe.exe")
        try:
            # 调用 ffprobe 获取 JSON 格式的详细信息
            cmd = [
                ffprobe,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                self.filepath,
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=get_subprocess_flags(),
            ) as proc:
                self.proc = proc
                output, stderr = proc.communicate()
                if not self.is_running:
                    return
                if proc.returncode != 0:
                    raise RuntimeError(safe_decode(stderr))

            data = json.loads(output)

            # 渲染 HTML 报告（纯函数，负责颜色/转义/区块/完美形态标记）
            html, should_hide = build_media_report(data, self.filepath, isDarkTheme())
            self.report_signal.emit(html, should_hide)

        except Exception as e:  # noqa: BLE001
            err_html = f'<div style="color: #FF4E6A; font-weight: bold;">{tr("info.report.parse_error")}</div><div style="color: #999999;">{e!s}</div>'
            self.report_signal.emit(err_html, True)
