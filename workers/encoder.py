import os
import subprocess
import time
import re
import ctypes
import json
import shutil
from PySide6.QtCore import Signal

from i18n.translator import tr
from utils import (
    get_subprocess_flags, tool_path, safe_decode,
    time_str_to_seconds, to_long_path, get_default_cache_dir
)
from config import (
    VIDEO_EXTS, SAVE_MODE_OVERWRITE, SAVE_MODE_REMAIN,
    SUBTITLE_CODEC_SRT, AUDIO_CODEC, SAMPLE_RATE,
    LOUDNORM_MODE_ALWAYS, LOUDNORM_MODE_AUTO,
    ENC_NVENC, ENC_AMF, PIX_FMT_AB_AV1, PIX_FMT_10BIT, PIX_FMT_8BIT,
    GPU_COOLING_TIME
)
from .base import BaseWorker

# --- 工作线程 (负责耗时的转码任务) ---
class EncoderWorker(BaseWorker):
    """
    编码器工作线程，负责执行所有与视频编码相关的耗时任务。
    包括使用 ab-av1 进行VMAF探测，以及使用 FFmpeg 进行最终转码。
    """
    # 定义信号，用于通知 UI 更新
    log_signal = Signal(str, str) # msg, level (info/success/error)
    progress_total_signal = Signal(int)
    progress_current_signal = Signal(int)
    file_progress_signal = Signal(str, int) # filepath, percent
    file_stats_signal = Signal(str, str, str) # filepath, speed, eta
    file_status_signal = Signal(str, str)   # filepath, status (processing, success, error)
    finished_signal = Signal()
    ask_error_decision = Signal(str, str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_paused = False
        self.current_proc = None

    def stop(self):
        """ 强制停止当前正在运行的子进程（ffmpeg 或 ab-av1）。 """
        if self.current_proc:
            try:
                # 使用 Popen 异步执行 taskkill，避免阻塞 UI 线程导致假死
                subprocess.Popen(["taskkill", "/F", "/T", "/PID", str(self.current_proc.pid)], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=get_subprocess_flags())
            except Exception:
                pass
        super().stop()

    def set_paused(self, paused):
        """ 设置或取消暂停状态。 """
        self.is_paused = paused

    def set_system_awake(self, keep_awake=True):
        """ 防止或允许系统在编码期间进入休眠状态。 """
        try:
            if keep_awake:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass

    def receive_decision(self, decision):
        """ 接收用户在错误对话框中做出的决定（跳过或停止）。 """
        self.decision = decision
        self.waiting_decision = False

    def run(self):
        """ 线程的主执行体，包含完整的编码流程。 """
        # --- 1. 解包配置 ---
        selected_files = self.config.get('selected_files') or []
        encoder_type = self.config.get('encoder', 'Intel QSV')
        export_dir = self.config['export_dir']
        cache_dir = self.config.get('cache_dir') or get_default_cache_dir()
        save_mode = self.config.get('save_mode', SAVE_MODE_OVERWRITE)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:
            cache_dir = ""
        preset = self.config['preset']
        target_vmaf = self.config['vmaf']
        audio_bitrate = self.config['audio_bitrate']
        loudnorm = self.config['loudnorm']
        loudnorm_mode = self.config.get('loudnorm_mode', LOUDNORM_MODE_AUTO)

        ffmpeg = tool_path("ffmpeg.exe")
        ffprobe = tool_path("ffprobe.exe")
        ab_av1 = tool_path("ab-av1.exe")
        
        os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            self.set_system_awake(True)
            tasks = []
            
            for p in selected_files:
                if os.path.isfile(p) and p.lower().endswith(VIDEO_EXTS):
                    tasks.append(p)
            
            total_tasks = len(tasks)
            if total_tasks == 0:
                self.log_signal.emit(tr("log.encoder.no_files_found"), "error")
                self.finished_signal.emit()
                return

            self.log_signal.emit(tr("log.encoder.tasks_found", total_tasks=total_tasks), "info")

            # --- 2. 预计算通用编码器参数 ---
            try:
                p_val = int(preset)
                p_val = max(1, min(7, p_val))
            except (ValueError, TypeError):
                p_val = 4

            enc_pix_fmt = PIX_FMT_AB_AV1

            if ENC_NVENC in encoder_type:
                enc_name = "av1_nvenc"
                nv_p = 8 - p_val
                enc_preset = f"p{nv_p}"
            elif ENC_AMF in encoder_type:
                enc_name = "av1_amf"
                if p_val <= 2: enc_preset = "quality"
                elif p_val <= 5: enc_preset = "balanced" 
                else: enc_preset = "speed"
            else:
                enc_name = "av1_qsv"
                enc_preset = str(p_val)

            # --- 3. 循环处理每个文件 ---
            for i, filepath in enumerate(tasks):
                if not self.is_running:
                    break

                task_start_time = time.time()
                file_paused_time = 0.0

                std_filepath = os.path.abspath(filepath)
                fname = os.path.basename(filepath)
                self.log_signal.emit(tr("log.encoder.task_start", i=i+1, total_tasks=total_tasks, fname=fname), "info")
                self.file_status_signal.emit(filepath, "processing")
                
                self.progress_total_signal.emit(int((i / total_tasks) * 100))
                self.progress_current_signal.emit(0)

                # --- 3.1 获取或补测媒体元数据 ---
                meta = self.config.get('metadata', {}).get(filepath) or {}
                codec = meta.get('codec', '')
                duration_sec = meta.get('duration', 0.0)
                source_audio_channels = meta.get('channels')

                if not codec or duration_sec <= 0:
                    try:
                        cmd_probe = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", std_filepath]
                        raw_out = subprocess.check_output(cmd_probe, creationflags=get_subprocess_flags())
                        probe_data = json.loads(raw_out)
                        for s in probe_data.get('streams', []):
                            if s.get('codec_type') == 'video' and not codec:
                                if s.get('codec_name', '').lower() not in ['mjpeg', 'png', 'bmp']:
                                    codec = s.get('codec_name', '').lower()
                            elif s.get('codec_type') == 'audio' and source_audio_channels is None:
                                source_audio_channels = int(s.get('channels', 2))
                        if duration_sec <= 0:
                            duration_sec = float(probe_data.get('format', {}).get('duration', 0))
                    except Exception:
                        pass
                
                # --- 3.2 如果已是AV1则跳过 ---
                try:
                    if "av1" in codec:
                        self.log_signal.emit(tr("log.encoder.skip_av1"), "success")
                        total_duration = time.time() - task_start_time
                        self.file_stats_signal.emit(filepath, tr("log.encoder.status_skipped"), tr("log.encoder.status_duration", total_duration=total_duration))
                        self.file_status_signal.emit(filepath, "success")
                        continue
                except Exception:
                    pass

                # --- 3.3 ab-av1 VMAF 探测 ---
                search_strategies = []
                if enc_name != "av1_amf":
                    search_strategies.append({"encoder": enc_name, "preset": enc_preset, "desc": "硬件探测"})
                svt_preset = str(min(12, p_val + 5))
                search_strategies.append({"encoder": "libsvtav1", "preset": svt_preset, "desc": "CPU 探测 (SVT-AV1)"})
                search_strategies.append({"encoder": "libaom-av1", "preset": "6", "desc": "CPU 探测 (AOM-AV1)"})
                
                best_icq = 24
                search_success = False
                ab_av1_log = []
                final_strategy = None
                search_start_time = time.time()
                search_paused_time = 0.0

                for strategy in search_strategies:
                    if not self.is_running: break
                    s_enc, s_preset, s_desc = strategy["encoder"], strategy["preset"], strategy["desc"]
                    if strategy != search_strategies[0]:
                         self.log_signal.emit(tr("log.encoder.ab_av1_fallback", desc=s_desc), "warning")
                    else:
                         self.log_signal.emit(tr("log.encoder.ab_av1_start"), "info")

                    search_max_crf = "63" if s_enc in ["libsvtav1", "libaom-av1"] else "51"
                    cmd_search = [ab_av1, "crf-search", "-i", std_filepath, "--encoder", s_enc, "--pix-format", enc_pix_fmt, "--min-vmaf", str(target_vmaf), "--preset", s_preset, "--max-crf", search_max_crf]
                    if cache_dir and os.path.isdir(cache_dir):
                        cmd_search.extend(["--temp-dir", cache_dir])
                    
                    current_log = []
                    last_vmaf_log = None
                    attempt_success = False
                    
                    try:
                        with subprocess.Popen(cmd_search, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, creationflags=get_subprocess_flags()) as proc:
                            self.current_proc = proc
                            while True:
                                if not self.is_running:
                                    try: proc.kill()
                                    except: pass
                                    break
                                if self.is_paused:
                                    p_start = time.time()
                                    while self.is_paused:
                                        if not self.is_running: break
                                        time.sleep(0.1)
                                    p_dt = time.time() - p_start
                                    search_paused_time += p_dt
                                    file_paused_time += p_dt

                                line = proc.stdout.readline()
                                if not line and proc.poll() is not None: break
                                if line:
                                    decoded = safe_decode(line)
                                    current_log.append(decoded)
                                    match = re.search(r"(?:crf|cq|qp)\s+(\d+)", decoded, re.IGNORECASE)
                                    vmaf_match = re.search(r"VMAF\s+([\d.]+)", decoded, re.IGNORECASE)
                                    if match and vmaf_match:
                                        vmaf_val = vmaf_match.group(1)
                                        if vmaf_val != last_vmaf_log:
                                            self.log_signal.emit(tr("log.encoder.ab_av1_probing", probe_crf=match.group(0).upper(), vmaf_val=vmaf_val), "info")
                                            last_vmaf_log = vmaf_val
                                        best_icq = int(match.group(1))
                                        attempt_success = True
                            
                            if proc.returncode != 0:
                                if attempt_success:
                                    # [Fix] 如果已经成功探测到 VMAF 数据，即使进程异常退出（如驱动不稳定），也优先使用已获取的参数，避免回退到慢速 CPU 探测
                                    self.log_signal.emit(f"⚠️ 探测术式异常中止 (Code {proc.returncode})，但已截获有效魔力参数 ({best_icq})，将强行采用。", "warning")
                                else:
                                    if current_log:
                                        self.log_signal.emit(f"    -> 探测失败: {current_log[-1].strip()}", "error")
                                    attempt_success = False
                    except Exception as e:
                        self.log_signal.emit(f"⚠️ 探测执行异常: {e}", "warning")
                        attempt_success = False
                    finally:
                        self.current_proc = None
                    
                    if attempt_success:
                        search_success = True
                        final_strategy = strategy
                        break
                    else:
                        ab_av1_log.extend(current_log)

                search_duration = time.time() - search_start_time - search_paused_time
                if not self.is_running: break

                if search_success:
                    is_cpu_detect = (final_strategy["encoder"] in ["libsvtav1", "libaom-av1"])
                    is_hw_target = (enc_name in ["av1_amf", "av1_nvenc", "av1_qsv"])
                    
                    if is_cpu_detect and is_hw_target:
                        offset = int(self.config.get('amf_offset', 0))
                        cpu_crf = best_icq
                        raw_icq = cpu_crf + offset
                        best_icq = max(1, min(51, raw_icq))

                        if best_icq != raw_icq:
                            reason = "最小" if raw_icq < 1 else "最大"
                            self.log_signal.emit(tr("log.encoder.ab_av1_success_offset_corrected", desc=final_strategy['desc'], cpu_crf=cpu_crf, offset=offset, raw_icq=raw_icq, reason=reason, best_icq=best_icq, search_duration=search_duration), "warning")
                        else:
                            self.log_signal.emit(tr("log.encoder.ab_av1_success_offset", desc=final_strategy['desc'], cpu_crf=cpu_crf, offset=offset, best_icq=best_icq, search_duration=search_duration), "success")
                    else:
                        self.log_signal.emit(tr("log.encoder.ab_av1_success", best_icq=best_icq, search_duration=search_duration), "success")
                else:
                    self.log_signal.emit(tr("log.encoder.ab_av1_failed", best_icq=best_icq), "error")
                    if ab_av1_log:
                        self.log_signal.emit(tr("log.encoder.ab_av1_error_log_header"), "error")
                        for log_line in ab_av1_log[-5:]:
                            self.log_signal.emit(f"    {log_line}", "error")

                if best_icq > 51:
                    self.log_signal.emit(tr("log.encoder.icq_corrected", icq=best_icq), "warning")
                    best_icq = 51

                # --- 3.4 FFmpeg 最终编码 ---
                base_name = os.path.splitext(fname)[0]
                temp_file = os.path.join(cache_dir, f"{base_name}_{int(time.time())}.temp.mkv") if cache_dir and os.path.isdir(cache_dir) else os.path.join(os.path.dirname(std_filepath), base_name + ".temp.mkv")
                if save_mode == SAVE_MODE_OVERWRITE:
                    final_dest = os.path.join(os.path.dirname(std_filepath), base_name + ".mkv")
                elif save_mode == SAVE_MODE_REMAIN:
                    final_dest = os.path.join(os.path.dirname(std_filepath), base_name + "_opt.mkv")
                else:
                    if not export_dir: export_dir = os.path.dirname(std_filepath)
                    os.makedirs(export_dir, exist_ok=True)
                    final_dest = os.path.join(export_dir, base_name + ".mkv")

                sub_codec = "copy"
                if fname.lower().endswith(('.mp4', '.mov', '.m4v')):
                    sub_codec = SUBTITLE_CODEC_SRT

                audio_args = ["-c:a", AUDIO_CODEC, "-b:a", audio_bitrate, "-ar", SAMPLE_RATE]
                if source_audio_channels:
                    audio_args.extend(["-ac", str(source_audio_channels)])
                    if source_audio_channels > 2:
                        self.log_signal.emit(tr("log.encoder.info_multichannel", channels=source_audio_channels), "success")
                
                should_apply_loudnorm = (loudnorm_mode == LOUDNORM_MODE_ALWAYS) or (loudnorm_mode == LOUDNORM_MODE_AUTO and (source_audio_channels is None or source_audio_channels <= 2))
                if should_apply_loudnorm and loudnorm:
                    audio_args.extend(["-af", loudnorm])
                    self.log_signal.emit(tr("log.encoder.info_loudnorm_enabled", mode=loudnorm_mode), "info")
                else:
                    self.log_signal.emit(tr("log.encoder.info_loudnorm_skipped", mode=loudnorm_mode), "info")

                cmd = []
                # 构建 FFmpeg 命令行
                cmd = [ffmpeg, "-y", "-hide_banner"]
                
                # 硬件解码加速 (如果适用)
                if enc_name == "av1_qsv":
                    cmd.extend(["-init_hw_device", "qsv=hw", "-filter_hw_device", "hw", "-v", "verbose"])
                elif enc_name == "av1_nvenc":
                    cmd.extend(["-v", "verbose"])
                elif enc_name == "av1_amf":
                    cmd.extend(["-v", "verbose"])

                cmd.extend(["-i", std_filepath])
                
                # 视频编码参数
                cmd.extend(["-c:v", enc_name, "-pix_fmt", PIX_FMT_10BIT])
                
                if enc_name == "av1_qsv":
                    cmd.extend(["-global_quality:v", str(best_icq), "-preset", enc_preset, "-look_ahead", "1"])
                elif enc_name == "av1_nvenc":
                    cmd.extend(["-cq", str(best_icq), "-preset", enc_preset, "-b:v", "0"])
                    if self.config.get('nv_aq', True):
                        cmd.extend(["-spatial-aq", "1", "-temporal-aq", "1"])
                elif enc_name == "av1_amf":
                    cmd.extend(["-usage", "transcoding", "-quality", enc_preset, "-rc", "vbr_latency", "-qvbr_quality_level", str(best_icq)])
                    if self.config.get('nv_aq', True): # 复用 nv_aq 开关作为 AMD PreAnalysis
                        cmd.extend(["-preanalysis", "true"])

                # 音频和字幕
                cmd.extend(audio_args)
                cmd.extend(["-c:s", sub_codec])
                
                # 映射所有流
                cmd.extend(["-map", "0:v:0", "-map", "0:a", "-map", "0:s?"])
                
                # 输出文件
                cmd.append(temp_file)

                # [Fix] WinError 87 修复：过滤掉 cmd 中的空字符串和非字符串对象
                cmd = [str(arg) for arg in cmd if str(arg).strip()]

                encode_start_time = time.time()
                encode_paused_time = 0.0
                try:
                    # [Fix] 使用 text=True (universal_newlines) 让 Python 处理 \r 换行符，解决进度条不更新问题
                    # 同时指定 encoding='utf-8' errors='replace' 防止编码报错
                    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                          startupinfo=startupinfo, creationflags=get_subprocess_flags(),
                                          text=True, encoding='utf-8', errors='replace') as proc:
                        self.current_proc = proc
                        err_log = []
                        max_percent = 0
                        while True:
                            if not self.is_running:
                                try: proc.kill()
                                except: pass
                                break
                            if self.is_paused:
                                p_start = time.time()
                                while self.is_paused:
                                    if not self.is_running: break
                                    time.sleep(0.1)
                                p_dt = time.time() - p_start
                                encode_paused_time += p_dt
                                file_paused_time += p_dt

                            line = proc.stdout.readline()
                            if not line and proc.poll() is not None: break
                            if line:
                                d = line.strip() # 已经是字符串，无需 safe_decode
                                
                                # [Fix] 尝试从输出中补获时长 (防止元数据获取失败导致进度条不走)
                                if duration_sec <= 0 and "Duration:" in d:
                                    dur_match = re.search(r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)", d)
                                    if dur_match:
                                        duration_sec = time_str_to_seconds(dur_match.group(1))

                                if "time=" in d and duration_sec > 0:
                                    t_match = re.search(r"time=\s*(\d+:\d+:\d+(?:\.\d+)?)", d)
                                    if t_match:
                                        current_sec = time_str_to_seconds(t_match.group(1))
                                        percent = min(100, int((current_sec / duration_sec) * 100))
                                        if percent > max_percent:
                                            max_percent = percent
                                            self.progress_current_signal.emit(percent)
                                            self.file_progress_signal.emit(filepath, percent)
                                        
                                        s_match = re.search(r"speed=\s*([\d.]+)x", d)
                                        if s_match:
                                            try:
                                                speed_val = float(s_match.group(1))
                                                if speed_val > 0:
                                                    remaining = (duration_sec - current_sec) / speed_val
                                                    m, s = divmod(int(remaining), 60)
                                                    h, m = divmod(m, 60)
                                                    eta = f"ETA: {h:02d}:{m:02d}:{s:02d}"
                                                    self.file_stats_signal.emit(filepath, f"{speed_val:.2f}x", eta)
                                            except Exception: pass

                                if "frame=" not in d:
                                    err_log.append(d)
                                    if len(err_log) > 20: err_log.pop(0)
                        return_code = proc.returncode
                except Exception as e:
                    self.log_signal.emit(tr("log.encoder.ffmpeg_exception", error=e), "error")
                    self.file_status_signal.emit(filepath, "error")
                    continue
                finally:
                    self.current_proc = None
                    encode_duration = time.time() - encode_start_time - encode_paused_time

                if not self.is_running:
                    lp_temp = to_long_path(temp_file)
                    if os.path.exists(lp_temp): os.remove(lp_temp)
                    break

                lp_temp = to_long_path(temp_file)
                if return_code == 0 and os.path.exists(lp_temp) and os.path.getsize(lp_temp) > 1024:
                    try:
                        lp_dest = to_long_path(final_dest)
                        abs_src = os.path.normcase(os.path.abspath(filepath))
                        abs_dest = os.path.normcase(os.path.abspath(final_dest))
                        lp_src = to_long_path(filepath)
                        
                        total_duration = time.time() - task_start_time - file_paused_time

                        if save_mode == SAVE_MODE_OVERWRITE:
                            success = False
                            for _ in range(3):
                                try:
                                    if abs_src == abs_dest:
                                        bak_path = lp_src + ".bak"
                                        if os.path.exists(bak_path): os.remove(bak_path)
                                        os.replace(lp_src, bak_path)
                                        shutil.move(lp_temp, lp_dest)
                                        if os.path.exists(bak_path): os.remove(bak_path)
                                    else:
                                        if os.path.exists(lp_dest): os.remove(lp_dest)
                                        shutil.move(lp_temp, lp_dest)
                                        if os.path.exists(lp_src): os.remove(lp_src)
                                    success = True
                                    break
                                except Exception:
                                    time.sleep(1)
                            
                            if success:
                                self.log_signal.emit(tr("log.encoder.success_overwrite", encode_duration=encode_duration, total_duration=total_duration), "success")
                                self.file_stats_signal.emit(filepath, tr("log.encoder.status_done"), tr("log.encoder.status_duration", total_duration=total_duration))
                                self.file_status_signal.emit(filepath, "success")
                            else:
                                raise Exception(tr("log.encoder.error_move_overwrite"))
                        else:
                            for _ in range(3):
                                try:
                                    if os.path.exists(lp_dest): os.remove(lp_dest)
                                    shutil.move(lp_temp, lp_dest)
                                    break
                                except Exception: time.sleep(1)

                            if save_mode == SAVE_MODE_REMAIN:
                                self.log_signal.emit(tr("log.encoder.success_remain", encode_duration=encode_duration, total_duration=total_duration), "success")
                            else:
                                self.log_signal.emit(tr("log.encoder.success_save_as", encode_duration=encode_duration, total_duration=total_duration), "success")
                            self.file_stats_signal.emit(filepath, tr("log.encoder.status_done"), tr("log.encoder.status_duration", total_duration=total_duration))
                            self.file_status_signal.emit(filepath, "success")
                    except Exception as e:
                        self.log_signal.emit(tr("log.encoder.error_move", error=e), "error")
                        self.file_status_signal.emit(filepath, "error")
                else:
                    self.log_signal.emit(tr("log.encoder.ffmpeg_crash"), "error")
                    self.file_status_signal.emit(filepath, "error")
                    for err_line in err_log:
                        self.log_signal.emit(f"   {err_line}", "error")
                    lp_temp = to_long_path(temp_file)
                    if os.path.exists(lp_temp): os.remove(lp_temp)
                    
                    if self.is_running:
                        self.waiting_decision = True
                        self.decision = None
                        self.ask_error_decision.emit(tr("dialog.encoder.crash_title"), tr("dialog.encoder.crash_content", fname=fname))
                        while self.waiting_decision and self.is_running:
                            time.sleep(0.1)
                        if self.decision == 'stop':
                            break
                
                if self.is_running:
                    self.log_signal.emit(tr("log.encoder.cooling_down"), "info")
                    time.sleep(GPU_COOLING_TIME)

            if self.is_running:
                self.log_signal.emit(tr("log.encoder.all_done"), "success")
                self.progress_total_signal.emit(100)
                self.progress_current_signal.emit(100)
            else:
                self.log_signal.emit(tr("log.encoder.stopped"), "error")

        except Exception as e:
            self.log_signal.emit(tr("log.encoder.fatal_error", error=e), "error")
        finally:
            self.set_system_awake(False)
            self.finished_signal.emit()