import os
import subprocess
import time
import re
import ctypes
import json
import shutil
from PySide6.QtCore import Signal

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
    # 定义信号，用于通知 UI 更新
    log_signal = Signal(str, str) # msg, level (info/success/error)
    progress_total_signal = Signal(int)
    progress_current_signal = Signal(int)
    file_progress_signal = Signal(str, int) # filepath, percent
    file_stats_signal = Signal(str, str, str) # filepath, speed, eta [Add]
    file_status_signal = Signal(str, str)   # filepath, status (processing, success, error)
    finished_signal = Signal()
    ask_error_decision = Signal(str, str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_paused = False
        self.current_proc = None

    def stop(self):
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
        self.is_paused = paused

    def set_system_awake(self, keep_awake=True):
        try:
            if keep_awake:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass

    def receive_decision(self, decision):
        self.decision = decision
        self.waiting_decision = False

    def run(self):
        # 解包配置
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
            
            # 统一使用已选择素材列表
            for p in selected_files:
                if os.path.isfile(p) and p.lower().endswith(VIDEO_EXTS):
                    tasks.append(p)
            
            total_tasks = len(tasks)
            if total_tasks == 0:
                self.log_signal.emit("侦测不到任何魔力残留... (｡•ˇ‸ˇ•｡)", "error")
                self.finished_signal.emit()
                return

            self.log_signal.emit(f"捕捉到 {total_tasks} 个待净化异变体！( •̀ ω •́ )y", "info")

            # [Opt] 预计算编码器参数 (移出循环，避免重复计算)
            # 统一解析 preset 为整数，并限制在 1-7 范围内
            try:
                p_val = int(preset)
                p_val = max(1, min(7, p_val))
            except (ValueError, TypeError):
                p_val = 4

            # 统一设置 ab-av1 像素格式
            enc_pix_fmt = PIX_FMT_AB_AV1

            if ENC_NVENC in encoder_type:
                enc_name = "av1_nvenc"
                # [Fix] NVENC 预设逻辑与 QSV 相反：
                # QSV: 1=慢(质量好/体积小), 7=快
                # NVENC: p1=快, p7=慢(质量好/体积小)
                # 因此需要反转映射，让 UI 的 1 对应 NVENC 的 p7
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

            for i, filepath in enumerate(tasks):
                if not self.is_running:
                    break

                task_start_time = time.time() # [Add] 记录任务开始时间
                file_paused_time = 0.0 # [Add] 累计暂停时间

                # 确保传递给命令行的是标准绝对路径，而非带有 \\?\ 的长路径
                std_filepath = os.path.abspath(filepath)
                fname = os.path.basename(filepath)
                self.log_signal.emit(f"[{i+1}/{total_tasks}] 正在对 {fname} 展开固有结界...", "info")
                self.file_status_signal.emit(filepath, "processing")
                
                self.progress_total_signal.emit(int((i / total_tasks) * 100))
                self.progress_current_signal.emit(0)

                # [Opt] 优先使用 UI 预存的元数据，避免重复调用 ffprobe
                meta = self.config.get('metadata', {}).get(filepath) or {}
                codec = meta.get('codec', '')
                duration_sec = meta.get('duration', 0.0)
                source_audio_channels = meta.get('channels')

                # [Fallback] 如果元数据缺失（例如导入太快），现场补测一次
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

                try:
                    
                    if "av1" in codec:
                        self.log_signal.emit(" -> 此物质已是纯净形态 (AV1)，跳过~ (Pass)", "success")
                        total_duration = time.time() - task_start_time
                        self.file_stats_signal.emit(filepath, "✨ 跳过", f"耗时: {total_duration:.2f}s")
                        self.file_status_signal.emit(filepath, "success")
                        continue
                except Exception:
                    pass

                # 3. ab-av1 搜索
                # [Refactor] 构建探测策略队列，支持失败回退
                search_strategies = []
                
                # 策略 A: 硬件探测 (如果可用且非 AMD)
                # AMD AMF 硬件探测不可用 (ab-av1 不支持)，直接跳过
                if enc_name != "av1_amf":
                    search_strategies.append({
                        "encoder": enc_name,
                        "preset": enc_preset,
                        "desc": "硬件探测" if "av1_" in enc_name else "探测"
                    })

                # 策略 B: CPU 探测 (SVT-AV1) - 速度优先
                # 映射 UI 1-7 到 SVT-AV1 预设 (6-12)
                svt_preset = str(min(12, p_val + 5))
                search_strategies.append({
                    "encoder": "libsvtav1",
                    "preset": svt_preset,
                    "desc": "CPU 探测 (SVT-AV1)"
                })

                # 策略 C: CPU 探测 (AOM-AV1) - 兼容性优先 (终极兜底)
                # 使用 cpu-used 6，速度尚可且兼容性最好，绝不会出现参数错误
                search_strategies.append({
                    "encoder": "libaom-av1",
                    "preset": "6",
                    "desc": "CPU 探测 (AOM-AV1)"
                })
                
                best_icq = 24
                search_success = False
                ab_av1_log = []
                final_strategy = None
                search_start_time = time.time() # [Add] 记录探测开始时间
                search_paused_time = 0.0 # [Add] 探测阶段暂停时间

                for strategy in search_strategies:
                    if not self.is_running: break
                    
                    s_enc = strategy["encoder"]
                    s_preset = strategy["preset"]
                    s_desc = strategy["desc"]
                    
                    if strategy != search_strategies[0]:
                         self.log_signal.emit(f" -> 尝试备用方案: {s_desc}...", "warning")
                    else:
                         self.log_signal.emit(f" -> 正在推演最强术式 (ab-av1)...", "info")

                    # [Fix] CPU 编码器 (SVT/AOM) 支持 CRF 63，允许探测更大范围，结果再截断
                    search_max_crf = "63" if s_enc in ["libsvtav1", "libaom-av1"] else "51"

                    cmd_search = [
                        ab_av1, "crf-search", "-i", std_filepath,
                        "--encoder", s_enc, 
                        "--pix-format", enc_pix_fmt, 
                        "--min-vmaf", str(target_vmaf),
                        "--preset", s_preset,
                        "--max-crf", search_max_crf,
                    ]
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
                                            self.log_signal.emit(f"    -> 探测中: {match.group(0).upper()} => VMAF: {vmaf_val}", "info")
                                            last_vmaf_log = vmaf_val
                                        best_icq = int(match.group(1))
                                        attempt_success = True
                            
                            if proc.returncode != 0:
                                attempt_success = False
                    except Exception:
                        attempt_success = False
                    finally:
                        self.current_proc = None
                    
                    if attempt_success:
                        search_success = True
                        final_strategy = strategy
                        break
                    else:
                        ab_av1_log.extend(current_log)

                search_duration = time.time() - search_start_time - search_paused_time # [Fix] 扣除暂停时间

                if not self.is_running:
                    break

                if search_success:
                    # 检查是否使用了 CPU 探测来代理硬件 (AMF 默认代理，NVENC 失败回退)
                    is_cpu_detect = (final_strategy["encoder"] in ["libsvtav1", "libaom-av1"])
                    is_hw_target = (enc_name in ["av1_amf", "av1_nvenc", "av1_qsv"])
                    
                    if is_cpu_detect and is_hw_target:
                        # 换算逻辑：CPU CRF 转换为 硬件 QP
                        offset = int(self.config.get('amf_offset', 0)) # 读取当前编码器的独立偏移值
                        cpu_crf = best_icq
                        raw_icq = cpu_crf + offset
                        # [Fix] 统一限制 QP 范围 [1, 51]
                        best_icq = max(1, min(51, raw_icq))

                        if best_icq != raw_icq:
                            reason = "最小" if raw_icq < 1 else "最大"
                            self.log_signal.emit(f" -> 术式解析完毕 ({final_strategy['desc']}): 原始CRF {cpu_crf} + 偏移 {offset} = {raw_icq} (已修正为{reason}限制 {best_icq}) [耗时: {search_duration:.1f}s]", "warning")
                        else:
                            self.log_signal.emit(f" -> 术式解析完毕 ({final_strategy['desc']}): 原始CRF {cpu_crf} + 偏移 {offset} => 最终参数 {best_icq} [耗时: {search_duration:.1f}s]", "success")
                    else:
                        self.log_signal.emit(f" -> 术式解析完毕 (ICQ): {best_icq} [耗时: {search_duration:.1f}s] (๑•̀ㅂ•́)و✧", "success")
                else:
                    self.log_signal.emit(f" -> 解析失败，强制使用基础术式 ICQ: {best_icq} (T_T)", "error")
                    # [Fix] 输出 ab-av1 的最后几行日志以便排查
                    if ab_av1_log:
                        self.log_signal.emit("    [ab-av1 错误回溯]:", "error")
                        for log_line in ab_av1_log[-5:]:
                            self.log_signal.emit(f"    {log_line}", "error")

                # [Fix] 双重保险：确保 QP/CQ 不超过 51
                if best_icq > 51:
                    self.log_signal.emit(f" -> 修正: 硬件编码器参数限制 ({best_icq} -> 51)", "warning")
                    best_icq = 51

                # 4. FFmpeg 转码
                base_name = os.path.splitext(fname)[0]
                if cache_dir and os.path.isdir(cache_dir):
                    temp_file = os.path.join(cache_dir, f"{base_name}_{int(time.time())}.temp.mkv")
                else:
                    temp_file = os.path.join(os.path.dirname(std_filepath), base_name + ".temp.mkv")
                
                if save_mode == SAVE_MODE_OVERWRITE:
                    final_dest = os.path.join(os.path.dirname(std_filepath), base_name + ".mkv")
                elif save_mode == SAVE_MODE_REMAIN:
                    final_dest = os.path.join(os.path.dirname(std_filepath), base_name + "_opt.mkv")
                else:
                    if not export_dir:
                        export_dir = os.path.dirname(std_filepath)
                    if not os.path.exists(export_dir):
                        os.makedirs(export_dir, exist_ok=True)
                    final_dest = os.path.join(export_dir, base_name + ".mkv")

                # [Fix] MP4/MOV 容器中的 mov_text 字幕无法直接 copy 到 MKV，需转为 srt/subrip
                sub_codec = "copy"
                if fname.lower().endswith(('.mp4', '.mov', '.m4v')):
                    sub_codec = SUBTITLE_CODEC_SRT

                audio_args = ["-c:a", AUDIO_CODEC, "-b:a", audio_bitrate, "-ar", SAMPLE_RATE]
                if source_audio_channels:
                    audio_args.extend(["-ac", str(source_audio_channels)])
                    if source_audio_channels > 2:
                        self.log_signal.emit(f" -> 检测到多声道 ({source_audio_channels}ch)，已保持原样。", "success")
                
                # [Fix] 响度标准化逻辑升级 (三种模式)
                should_apply_loudnorm = False
                if loudnorm_mode == LOUDNORM_MODE_ALWAYS:
                    should_apply_loudnorm = True
                elif loudnorm_mode == LOUDNORM_MODE_AUTO:
                    # 仅当声道数 <= 2 (单声道/立体声) 或 未知时启用
                    if source_audio_channels is None or source_audio_channels <= 2:
                        should_apply_loudnorm = True
                
                if should_apply_loudnorm and loudnorm:
                    audio_args.extend(["-af", loudnorm])
                    self.log_signal.emit(f" -> 音量均一化 (Loudnorm): 启用 ({loudnorm_mode})", "info")
                else:
                    self.log_signal.emit(f" -> 音量均一化 (Loudnorm): 跳过 ({loudnorm_mode})", "info")

                # 构建 FFmpeg 命令
                cmd = []
                if "NVIDIA" in encoder_type:
                    # NVIDIA NVENC 参数
                    cmd = [
                        ffmpeg, "-y", "-hide_banner",
                        "-i", std_filepath,
                        "-c:v", "av1_nvenc", 
                        "-preset", enc_preset,
                        "-rc:v", "vbr",       # [Fix] 显式指定 VBR 模式
                        "-cq", str(best_icq), # NVENC 使用 -cq 控制质量
                        "-b:v", "0",          # [Fix] 关键：解除码率上限，防止画质被默认码率限制
                    ]
                    # [Opt] 如果是高质量预设 (p5-p7)，启用多重处理以进一步压缩体积
                    if int(enc_preset[1]) >= 5:
                        cmd.extend(["-multipass", "1"])

                    if self.config.get('nv_aq', True):
                        cmd.extend(["-spatial-aq", "1", "-temporal-aq", "1"]) # 感知增强 (AQ)
                    
                    cmd.extend([
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-pix_fmt", PIX_FMT_10BIT,

                        *audio_args,
                        "-c:s", sub_codec,

                        "-map", "0:v:0", 
                        "-map", "0:a:0?", 
                        "-map", "0:s?",
                        "-progress", "pipe:1",
                        temp_file
                    ])
                elif "AMD" in encoder_type:
                    # AMD AMF 参数
                    cmd = [
                        ffmpeg, "-y", "-hide_banner",
                        "-i", std_filepath,
                        "-c:v", "av1_amf",
                        "-usage", "transcoding",
                        "-quality", enc_preset,
                        "-rc", "qvbr",
                        "-qvbr_quality_level", str(best_icq),
                        "-lowlatency", "0",    # 0 表示高吞吐量模式，适合转码
                        "-filler_data", "0",   # 禁用填充数据，节省不必要的码率
                    ]
                    
                    # [Add] AMD 专用优化参数 (Pre-Analysis & VBAQ)
                    if self.config.get('nv_aq', True):
                        cmd.extend(["-preanalysis", "1", "-vbaq", "1"])

                    cmd.extend([
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                        "-pix_fmt", PIX_FMT_8BIT,

                        *audio_args,
                        "-c:s", sub_codec,

                        "-map", "0:v:0",
                        "-map", "0:a:0?",
                        "-map", "0:s?",
                        "-progress", "pipe:1",
                        temp_file
                    ])
                else:
                    # Intel QSV 参数 (默认)
                    cmd = [
                        ffmpeg, "-y", "-hide_banner",
                        "-init_hw_device", "qsv=hw",
                        "-i", std_filepath,
                        "-c:v", "av1_qsv", "-preset", preset,
                        "-global_quality:v", str(best_icq),
                    ]

                    # [Add] Intel QSV 优化参数 (Lookahead)
                    if self.config.get('nv_aq', True):
                        cmd.extend(["-look_ahead", "1"])

                    cmd.extend([
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", # 确保分辨率为偶数，防止 QSV 报错
                        "-pix_fmt", PIX_FMT_10BIT,
                        "-async_depth", "1", # 修复显存溢出/Invalid FrameType

                        *audio_args,
                        "-c:s", sub_codec,

                        "-map", "0:v:0", 
                        "-map", "0:a:0?", 
                        "-map", "0:s?",
                        "-progress", "pipe:1",
                        temp_file
                    ])

                encode_start_time = time.time() # [Add] 记录压制开始时间
                encode_paused_time = 0.0 # [Add] 压制阶段暂停时间
                try:
                    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=startupinfo, bufsize=0, creationflags=get_subprocess_flags()) as proc:
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
                                d = safe_decode(line)
                                if "time=" in d and duration_sec > 0:
                                    t_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d+)", d)
                                    if t_match:
                                        current_sec = time_str_to_seconds(t_match.group(1))
                                        percent = min(100, int((current_sec / duration_sec) * 100)) # [Opt] 限制最大 100%，防止短视频溢出
                                        if percent > max_percent:
                                            max_percent = percent
                                            self.progress_current_signal.emit(percent)
                                            self.file_progress_signal.emit(filepath, percent)
                                        
                                        # [Add] 解析速度并计算 ETA
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
                    self.log_signal.emit(f" -> 魔力逆流: {e} (×_×)", "error")
                    self.file_status_signal.emit(filepath, "error")
                    continue
                finally:
                    self.current_proc = None
                    encode_duration = time.time() - encode_start_time - encode_paused_time # [Fix] 扣除暂停时间

                if not self.is_running:
                    lp_temp = to_long_path(temp_file)
                    if os.path.exists(lp_temp):
                        os.remove(lp_temp)
                    break

                lp_temp = to_long_path(temp_file)
                if return_code == 0 and os.path.exists(lp_temp) and os.path.getsize(lp_temp) > 1024:
                    try:
                        lp_dest = to_long_path(final_dest)
                        abs_src = os.path.normcase(os.path.abspath(filepath))
                        abs_dest = os.path.normcase(os.path.abspath(final_dest))
                        lp_src = to_long_path(filepath)
                        
                        total_duration = time.time() - task_start_time - file_paused_time # [Fix] 扣除暂停时间

                        if save_mode == SAVE_MODE_OVERWRITE:
                            # [优化] 增加重试逻辑，防止 PermissionError
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
                                self.log_signal.emit(f" -> 净化完成！旧世界已被重写 (Overwrite) (ﾉ>ω<)ﾉ [压制: {encode_duration:.1f}s | 总耗时: {total_duration:.1f}s]", "success")
                                self.file_stats_signal.emit(filepath, "✅ 完成", f"耗时: {total_duration:.1f}s")
                                self.file_status_signal.emit(filepath, "success")
                            else:
                                raise Exception("无法替换源文件，可能被其他程序占用。")
                        else:
                            for _ in range(3):
                                try:
                                    if os.path.exists(lp_dest): os.remove(lp_dest)
                                    shutil.move(lp_temp, lp_dest)
                                    break
                                except Exception: time.sleep(1)

                            if save_mode == SAVE_MODE_REMAIN:
                                self.log_signal.emit(f" -> 净化完成！元素已保留，优化体已生成 (Remain) (ﾉ>ω<)ﾉ [压制: {encode_duration:.1f}s | 总耗时: {total_duration:.1f}s]", "success")
                            else:
                                self.log_signal.emit(f" -> 净化完成！新世界已确立 (Save As) (ﾉ>ω<)ﾉ [压制: {encode_duration:.1f}s | 总耗时: {total_duration:.1f}s]", "success")
                            self.file_stats_signal.emit(filepath, "✅ 完成", f"耗时: {total_duration:.1f}s")
                            self.file_status_signal.emit(filepath, "success")
                    except Exception as e:
                        self.log_signal.emit(f" -> 封印仪式失败: {e} (T_T)", "error")
                        self.file_status_signal.emit(filepath, "error")
                else:
                    self.log_signal.emit(" -> 术式失控 (Crash)... (T_T)", "error")
                    self.file_status_signal.emit(filepath, "error")
                    for err_line in err_log:
                        self.log_signal.emit(f"   {err_line}", "error")
                    lp_temp = to_long_path(temp_file)
                    if os.path.exists(lp_temp):
                        os.remove(lp_temp)
                    
                    # 遇到错误时询问用户
                    if self.is_running:
                        self.waiting_decision = True
                        self.decision = None
                        self.ask_error_decision.emit("术式崩坏警告", f"任务 {fname} 遭遇未知错误。\n是否跳过此任务并继续？")
                        while self.waiting_decision and self.is_running:
                            time.sleep(0.1)
                        if self.decision == 'stop':
                            break
                
                # [Fix] 冷却机制：强制休眠 3 秒，让 Intel 显卡驱动释放显存和句柄
                if self.is_running:
                    self.log_signal.emit(" -> 正在冷却魔术回路 (Cooling down GPU)...", "info")
                    time.sleep(GPU_COOLING_TIME)

            if self.is_running:
                self.log_signal.emit(">>> 奇迹达成！(๑•̀ㅂ•́)و✧", "success")
                self.progress_total_signal.emit(100)
                self.progress_current_signal.emit(100)
            else:
                self.log_signal.emit(">>> 契约被强制切断。", "error")

        except Exception as e:
            self.log_signal.emit(f"世界线变动率异常 (Fatal): {e}", "error")
        finally:
            self.set_system_awake(False)
            self.finished_signal.emit()
