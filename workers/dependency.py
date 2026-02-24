import os
import subprocess
from PySide6.QtCore import Signal

from i18n.translator import tr
from utils import tool_path, get_subprocess_flags, safe_decode
from config import PIX_FMT_10BIT, PIX_FMT_8BIT
from .base import BaseWorker

# --- 依赖检查线程 (启动优化) ---
class DependencyWorker(BaseWorker):
    """
    一个用于在后台异步检查所有外部依赖的线程。
    它会检查所需的.exe文件是否存在，并尝试探测可用的硬件编码器。
    """
    log_signal = Signal(str, str)
    result_signal = Signal(bool, bool, bool) # has_qsv, has_nvenc, has_amf
    missing_signal = Signal(list)

    def run(self):
        """ 线程的执行体，依次检查文件依赖和硬件编码器。 """
        missing = []
        dependencies = {
            "ffmpeg.exe": tr("dependency.ffmpeg_desc"),
            "ffprobe.exe": tr("dependency.ffprobe_desc"),
            "ab-av1.exe": tr("dependency.ab_av1_desc")
        }

        # 1. 检查可执行文件是否存在
        for exe, desc in dependencies.items():
            if not os.path.exists(tool_path(exe)):
                missing.append(f"❌ {desc} [{exe}]")

        if missing:
            self.missing_signal.emit(missing)
            return

        if not self.is_running: return

        try:
            ffmpeg_path = tool_path("ffmpeg.exe")
            
            # 2. 检查 FFmpeg 软件层面是否包含 av1_qsv, av1_nvenc, av1_amf 编码器
            enc_output = subprocess.check_output(
                [ffmpeg_path, "-v", "quiet", "-encoders"], 
                creationflags=get_subprocess_flags(),
                timeout=10
            )
            enc_str = safe_decode(enc_output)
            
            if not self.is_running: return

            has_qsv = False
            has_nvenc = False
            has_amf = False

            # 3. 探测 Intel QSV (尝试硬件编码一帧)
            if "av1_qsv" in enc_str:
                try:
                    with subprocess.Popen(
                        [ffmpeg_path, "-v", "error", "-init_hw_device", "qsv=hw", 
                         "-f", "lavfi", "-i", "color=black:s=1280x720", 
                         "-pix_fmt", PIX_FMT_10BIT,
                         "-c:v", "av1_qsv", "-frames:v", "1", "-f", "null", "-"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=get_subprocess_flags()
                    ) as proc:
                        _, stderr = proc.communicate(timeout=5)
                        if proc.returncode == 0: has_qsv = True
                        else:
                            err_msg = safe_decode(stderr)
                            if err_msg:
                                self.log_signal.emit(tr("log.dependency.qsv_failed", error=err_msg.splitlines()[0]), "error")
                except Exception as e:
                    self.log_signal.emit(tr("log.dependency.qsv_exception", error=e), "error")

            if not self.is_running: return

            # 4. 探测 NVIDIA NVENC (尝试硬件编码一帧)
            if "av1_nvenc" in enc_str:
                try:
                    with subprocess.Popen(
                        [ffmpeg_path, "-v", "error", 
                         "-f", "lavfi", "-i", "color=black:s=1280x720", 
                         "-pix_fmt", PIX_FMT_10BIT,
                         "-c:v", "av1_nvenc", "-frames:v", "1", "-f", "null", "-"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=get_subprocess_flags()
                    ) as proc:
                        _, stderr = proc.communicate(timeout=5)
                        if proc.returncode == 0: has_nvenc = True
                        else:
                            err_msg = safe_decode(stderr)
                            if "CUDA_ERROR_NO_DEVICE" in err_msg:
                                pass
                            else:
                                # 如果 av1_nvenc 失败，尝试 hevc_nvenc 以判断是否为不支持 AV1 的旧款N卡
                                with subprocess.Popen(
                                    [ffmpeg_path, "-v", "error", 
                                     "-f", "lavfi", "-i", "color=black:s=1280x720", 
                                     "-pix_fmt", "yuv420p",
                                     "-c:v", "hevc_nvenc", "-frames:v", "1", "-f", "null", "-"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=get_subprocess_flags()
                                ) as proc_hevc:
                                    proc_hevc.communicate(timeout=5)
                                    if proc_hevc.returncode == 0:
                                        self.log_signal.emit(tr("log.dependency.nvenc_unsupported_gpu"), "warning")
                                    else:
                                        short_err = err_msg.split('\n')[0] if err_msg else tr("common.unknown_error")
                                        self.log_signal.emit(tr("log.dependency.nvenc_failed", error=short_err), "error")
                except Exception as e:
                    self.log_signal.emit(tr("log.dependency.nvenc_exception", error=e), "error")

            if not self.is_running: return

            # 5. 探测 AMD AMF (尝试硬件编码一帧)
            if "av1_amf" in enc_str:
                try:
                    with subprocess.Popen(
                        [ffmpeg_path, "-v", "error",
                         "-f", "lavfi", "-i", "color=black:s=1280x720",
                         "-pix_fmt", PIX_FMT_10BIT,
                         "-c:v", "av1_amf", "-usage", "transcoding",
                         "-quality", "balanced",
                         "-rc", "cqp",
                         "-qp_i", "30", "-qp_p", "30", "-qp_b", "30",
                         "-frames:v", "1", "-f", "null", "-"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=get_subprocess_flags()
                    ) as proc:
                        _, stderr = proc.communicate(timeout=5)
                        if proc.returncode == 0: has_amf = True
                        else:
                            err_msg = safe_decode(stderr)
                            if err_msg:
                                short_err = err_msg.split('\n')[0]
                                self.log_signal.emit(tr("log.dependency.amf_failed", error=short_err), "error")
                except Exception as e:
                    self.log_signal.emit(tr("log.dependency.amf_exception", error=e), "error")
            
            # 6. 发送最终探测结果
            self.result_signal.emit(has_qsv, has_nvenc, has_amf)
                
        except Exception as e:
            self.log_signal.emit(tr("log.dependency.check_exception", error=e), "error")