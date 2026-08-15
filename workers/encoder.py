import ctypes
import json
import os
import re
import shutil
import subprocess
import time

from PySide6.QtCore import Signal

from config import (
    AUDIO_CODEC,
    ENC_AMF,
    ENC_NVENC,
    LOUDNORM_MODE_ALWAYS,
    LOUDNORM_MODE_AUTO,
    PIX_FMT_10BIT,
    PIX_FMT_AB_AV1,
    SAMPLE_RATE,
    SAVE_MODE_OVERWRITE,
    SAVE_MODE_REMAIN,
    SUBTITLE_CODEC_SRT,
    VIDEO_EXTS,
)
from i18n.translator import tr
from utils import (
    get_default_cache_dir,
    get_subprocess_flags,
    safe_decode,
    time_str_to_seconds,
    to_long_path,
    tool_path,
)

from .ab_av1_result import AbAv1ResultParser, SearchResultMode
from .base import BaseWorker
from .batch_progress import map_encode_progress, map_probe_progress
from .ffmpeg_retry import (
    FailureKind,
    RetryState,
    build_hw_decode_args,
    is_hardware_resource_error,
    next_retry_state,
)
from .transcode_paths import TaskPaths, build_final_output


# --- 工作线程 (负责耗时的转码任务) ---
class EncoderWorker(BaseWorker):
    """
    编码器工作线程，负责执行所有与视频编码相关的耗时任务。
    包括使用 ab-av1 进行VMAF探测，以及使用 FFmpeg 进行最终转码。
    """

    # 定义信号，用于通知 UI 更新
    log_signal = Signal(str, str)  # msg, level (info/success/error)
    progress_total_signal = Signal(int)
    progress_current_signal = Signal(int)
    file_progress_signal = Signal(str, int)  # filepath, percent
    file_stats_signal = Signal(str, str, str)  # filepath, speed, eta
    file_status_signal = Signal(
        str, str
    )  # filepath, status (processing, success, error)
    finished_signal = Signal()
    ask_error_decision = Signal(str, str)
    stage_signal = Signal(str, str)
    encoding_speed_signal = Signal(str, float)
    resource_error_signal = Signal(str, str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_paused = False
        self.current_proc = None
        self.manage_system_awake = config.get("manage_system_awake", True)
        task_paths = config.get("task_paths")
        if isinstance(task_paths, dict):
            task_paths = TaskPaths(**task_paths)
        self.task_paths = task_paths
        self.waiting_decision = False
        self.decision = None

    def stop(self):
        """强制停止当前正在运行的子进程（ffmpeg 或 ab-av1）。"""
        if self.current_proc:
            try:
                # 使用 Popen 异步执行 taskkill，避免阻塞 UI 线程导致假死
                subprocess.Popen(
                    ["taskkill", "/F", "/T", "/PID", str(self.current_proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=get_subprocess_flags(),
                )
            except Exception:  # noqa: S110, BLE001
                pass
        super().stop()

    def set_paused(self, paused):
        """设置或取消暂停状态。"""
        self.is_paused = paused

    def set_system_awake(self, keep_awake=True):
        """防止或允许系统在编码期间进入休眠状态。"""
        try:
            if keep_awake:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:  # noqa: S110, BLE001
            pass

    def receive_decision(self, decision):
        """接收用户在错误对话框中做出的决定（跳过或停止）。"""
        self.decision = decision
        self.waiting_decision = False

    def _probe_metadata(self, filepath, std_filepath, ffprobe):
        """探测或补全媒体元数据：codec/duration/声道/色彩/HDR。"""
        meta = self.config.get("metadata", {}).get(filepath) or {}
        codec = meta.get("codec", "")
        duration_sec = meta.get("duration", 0.0)
        source_audio_channels = meta.get("channels")
        pix_fmt = meta.get("pix_fmt", "")
        color_space = meta.get("color_space", "")
        color_transfer = meta.get("color_transfer", "")
        color_primaries = meta.get("color_primaries", "")
        has_dovi = meta.get("has_dovi", False)

        if not codec or duration_sec <= 0:
            try:
                cmd_probe = [
                    ffprobe,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    std_filepath,
                ]
                raw_out = subprocess.check_output(
                    cmd_probe, creationflags=get_subprocess_flags()
                )
                probe_data = json.loads(raw_out)
                for s in probe_data.get("streams", []):
                    if s.get("codec_type") == "video":
                        if s.get("codec_name", "").lower() not in [
                            "mjpeg",
                            "png",
                            "bmp",
                        ]:
                            if not codec:
                                codec = s.get("codec_name", "").lower()
                            pix_fmt = s.get("pix_fmt", "")
                            color_space = s.get("color_space", "")
                            color_transfer = s.get("color_transfer", "")
                            color_primaries = s.get("color_primaries", "")

                            side_data_list = s.get("side_data_list", [])
                            for sd in side_data_list:
                                sd_type = sd.get("side_data_type", "")
                                if (
                                    "Dolby Vision" in sd_type
                                    or "dolby vision" in sd_type.lower()
                                ):
                                    has_dovi = True
                    elif (
                        s.get("codec_type") == "audio" and source_audio_channels is None
                    ):
                        source_audio_channels = int(s.get("channels", 2))
                if duration_sec <= 0:
                    duration_sec = float(
                        probe_data.get("format", {}).get("duration", 0)
                    )
            except Exception:  # noqa: S110, BLE001
                pass

        return (
            codec,
            duration_sec,
            source_audio_channels,
            pix_fmt,
            color_space,
            color_transfer,
            color_primaries,
            has_dovi,
        )

    def _skip_av1(self, filepath, codec, task_start_time):
        """若已是 AV1 则跳过并发出状态信号，返回是否跳过。"""
        try:
            if "av1" in codec:
                self.log_signal.emit(tr("log.encoder.skip_av1"), "success")
                total_duration = time.time() - task_start_time
                self.file_stats_signal.emit(
                    filepath,
                    tr("log.encoder.status_skipped"),
                    tr("log.encoder.status_duration", total_duration=total_duration),
                )
                self.file_progress_signal.emit(filepath, 100)
                self.file_status_signal.emit(filepath, "success")
                return True
        except Exception:  # noqa: S110, BLE001
            pass
        return False

    def _probe_vmaf(
        self,
        std_filepath,
        filepath,
        fname,
        enc_name,
        enc_preset,
        p_val,
        target_vmaf,
        enc_pix_fmt,
        cache_dir,
        ab_av1,
        file_paused_time,
    ):
        """ab-av1 VMAF 探测 (best_icq, search_success, final_strategy,
        search_duration, file_paused_time, stop_processing)"""
        search_strategies = []
        if enc_name != "av1_amf":
            search_strategies.append(
                {"encoder": enc_name, "preset": enc_preset, "desc": "硬件探测"}
            )
        svt_preset = str(min(12, p_val + 5))
        search_strategies.append(
            {"encoder": "libsvtav1", "preset": svt_preset, "desc": "CPU 探测 (SVT-AV1)"}
        )
        search_strategies.append(
            {"encoder": "libaom-av1", "preset": "6", "desc": "CPU 探测 (AOM-AV1)"}
        )

        best_icq = None
        search_success = False
        ab_av1_log = []
        final_strategy = None
        search_start_time = time.time()
        search_paused_time = 0.0
        self.stage_signal.emit(filepath, "probing")

        for strategy_index, strategy in enumerate(search_strategies):
            if not self.is_running:
                break
            self.file_progress_signal.emit(
                filepath,
                map_probe_progress(strategy_index, len(search_strategies)),
            )
            s_enc, s_preset, s_desc = (
                strategy["encoder"],
                strategy["preset"],
                strategy["desc"],
            )
            if strategy != search_strategies[0]:
                self.log_signal.emit(
                    tr("log.encoder.ab_av1_fallback", desc=s_desc), "warning"
                )
                self.file_stats_signal.emit(
                    filepath, "ab-av1", f"备用方案 ({s_desc}) 中..."
                )
            else:
                self.log_signal.emit(tr("log.encoder.ab_av1_start"), "info")
                self.file_stats_signal.emit(filepath, "ab-av1", "探知最强术式中...")

            search_max_crf = "63" if s_enc in ["libsvtav1", "libaom-av1"] else "51"
            cmd_search = [
                ab_av1,
                "crf-search",
                "-i",
                std_filepath,
                "--encoder",
                s_enc,
                "--pix-format",
                enc_pix_fmt,
                "--min-vmaf",
                str(target_vmaf),
                "--preset",
                s_preset,
                "--max-crf",
                search_max_crf,
            ]
            if cache_dir and os.path.isdir(cache_dir):
                cmd_search.extend(["--temp-dir", cache_dir])

            current_log = []
            parser = AbAv1ResultParser()

            try:
                with subprocess.Popen(
                    cmd_search,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=0,
                    creationflags=get_subprocess_flags(),
                ) as proc:
                    self.current_proc = proc
                    while True:
                        if not self.is_running:
                            try:
                                proc.kill()
                            except Exception:  # noqa: S110, BLE001
                                pass
                            break
                        if self.is_paused:
                            p_start = time.time()
                            while self.is_paused:
                                if not self.is_running:
                                    break
                                time.sleep(0.1)
                            p_dt = time.time() - p_start
                            search_paused_time += p_dt
                            file_paused_time += p_dt

                        line = proc.stdout.readline()
                        if not line and proc.poll() is not None:
                            break
                        if line:
                            decoded = safe_decode(line)
                            current_log.append(decoded)
                            candidate = parser.feed(decoded)
                            if candidate is not None:
                                self.log_signal.emit(
                                    tr(
                                        "log.encoder.ab_av1_probing",
                                        probe_crf=f"CRF {candidate.crf}",
                                        vmaf_val=f"{candidate.vmaf:.2f}",
                                    ),
                                    "info",
                                )
                                self.file_stats_signal.emit(
                                    filepath,
                                    "ab-av1 探测中",
                                    (
                                        f"CRF {candidate.crf} => "
                                        f"VMAF {candidate.vmaf:.2f} "
                                        f"({candidate.encoded_percent:.0f}%)"
                                    ),
                                )

                search_result = parser.finish(proc.returncode, float(target_vmaf))
            except Exception as e:  # noqa: BLE001
                self.log_signal.emit(f"⚠️ 探测执行异常: {e}", "warning")
                search_result = None
            finally:
                self.current_proc = None

            if search_result is not None:
                best_icq = search_result.crf
                search_success = True
                final_strategy = strategy
                if search_result.mode is SearchResultMode.QUALITY_FALLBACK:
                    self.log_signal.emit(
                        (
                            "⚠️ ab-av1 无法同时满足目标 VMAF 与默认 "
                            "80% 体积限制；已优先保证画质，采用 "
                            f"CRF {search_result.crf} "
                            f"(VMAF {search_result.vmaf:.2f}, "
                            f"预测体积 {search_result.encoded_percent:.0f}%)。"
                        ),
                        "warning",
                    )
                break
            else:
                ab_av1_log.extend(current_log)
                if current_log:
                    self.log_signal.emit(
                        f"    -> 探测失败: {current_log[-1].strip()}",
                        "error",
                    )

        search_duration = time.time() - search_start_time - search_paused_time
        if not self.is_running:
            return None, False, None, search_duration, file_paused_time, True

        if not search_success:
            self.log_signal.emit(tr("log.encoder.ab_av1_failed"), "error")
            if ab_av1_log:
                self.log_signal.emit(tr("log.encoder.ab_av1_error_log_header"), "error")
                for log_line in ab_av1_log[-5:]:
                    self.log_signal.emit(f"    {log_line}", "error")
            if is_hardware_resource_error(ab_av1_log):
                self.resource_error_signal.emit(filepath, ab_av1_log[-1].strip())
            self.file_status_signal.emit(filepath, "error")

            if self.is_running:
                self.waiting_decision = True
                self.decision = None
                self.ask_error_decision.emit(
                    tr("dialog.encoder.crash_title"),
                    tr("dialog.encoder.crash_content", fname=fname),
                )
                while self.waiting_decision and self.is_running:
                    time.sleep(0.1)
                if self.decision == "stop":
                    return None, False, None, search_duration, file_paused_time, True
            return None, False, None, search_duration, file_paused_time, False

        is_cpu_detect = final_strategy["encoder"] in ["libsvtav1", "libaom-av1"]
        is_hw_target = enc_name in ["av1_amf", "av1_nvenc", "av1_qsv"]
        assert best_icq is not None

        if is_cpu_detect and is_hw_target:
            offset = int(self.config.get("amf_offset", 0))
            cpu_crf = best_icq
            raw_icq = cpu_crf + offset
            best_icq = max(1, min(51, raw_icq))

            if best_icq != raw_icq:
                reason = "最小" if raw_icq < 1 else "最大"
                self.log_signal.emit(
                    tr(
                        "log.encoder.ab_av1_success_offset_corrected",
                        desc=final_strategy["desc"],
                        cpu_crf=cpu_crf,
                        offset=offset,
                        raw_icq=raw_icq,
                        reason=reason,
                        best_icq=best_icq,
                        search_duration=search_duration,
                    ),
                    "warning",
                )
            else:
                self.log_signal.emit(
                    tr(
                        "log.encoder.ab_av1_success_offset",
                        desc=final_strategy["desc"],
                        cpu_crf=cpu_crf,
                        offset=offset,
                        best_icq=best_icq,
                        search_duration=search_duration,
                    ),
                    "success",
                )
        else:
            self.log_signal.emit(
                tr(
                    "log.encoder.ab_av1_success",
                    best_icq=best_icq,
                    search_duration=search_duration,
                ),
                "success",
            )

        if best_icq > 51:
            self.log_signal.emit(
                tr("log.encoder.icq_corrected", icq=best_icq), "warning"
            )
            best_icq = 51

        return best_icq, True, final_strategy, search_duration, file_paused_time, False

    def _execute_ffmpeg(
        self,
        filepath,
        std_filepath,
        fname,
        ffmpeg,
        enc_name,
        enc_preset,
        best_icq,
        save_mode,
        color_transfer,
        color_space,
        color_primaries,
        has_dovi,
        duration_sec,
        source_audio_channels,
        task_start_time,
        file_paused_time,
        cache_dir,
        export_dir,
        audio_bitrate,
        loudnorm,
        loudnorm_mode,
        startupinfo,
    ):
        """FFmpeg 转码执行 + 暂停处理 (stop_processing, file_paused_time)"""
        # --- 3.4 FFmpeg 最终编码 ---
        base_name = os.path.splitext(fname)[0]
        if self.task_paths is not None:
            temp_file = self.task_paths.temp_output
            final_dest = self.task_paths.final_output
        else:
            temp_file = (
                os.path.join(
                    cache_dir,
                    f"{base_name}_{int(time.time())}.temp.mkv",
                )
                if cache_dir and os.path.isdir(cache_dir)
                else os.path.join(
                    os.path.dirname(std_filepath),
                    base_name + ".temp.mkv",
                )
            )
            if (
                save_mode
                not in (
                    SAVE_MODE_OVERWRITE,
                    SAVE_MODE_REMAIN,
                )
                and not export_dir
            ):
                export_dir = os.path.dirname(std_filepath)
            final_dest = build_final_output(
                std_filepath,
                save_mode,
                export_dir,
            )
        os.makedirs(os.path.dirname(final_dest), exist_ok=True)
        self.stage_signal.emit(filepath, "encoding")

        sub_codec = "copy"
        if fname.lower().endswith((".mp4", ".mov", ".m4v")):
            sub_codec = SUBTITLE_CODEC_SRT

        audio_args = ["-c:a", AUDIO_CODEC, "-b:a", audio_bitrate, "-ar", SAMPLE_RATE]
        if source_audio_channels and source_audio_channels > 2:
            self.log_signal.emit(
                tr("log.encoder.info_multichannel", channels=source_audio_channels),
                "success",
            )

        should_apply_loudnorm = (loudnorm_mode == LOUDNORM_MODE_ALWAYS) or (
            loudnorm_mode == LOUDNORM_MODE_AUTO
            and (source_audio_channels is None or source_audio_channels <= 2)
        )

        # 收集音频滤镜，解决 libopus 5.1/7.1 非标声道布局导致的转码失败错误
        audio_filters = []
        if should_apply_loudnorm and loudnorm:
            audio_filters.append(loudnorm)
            self.log_signal.emit(
                tr("log.encoder.info_loudnorm_enabled", mode=loudnorm_mode), "info"
            )
        else:
            self.log_signal.emit(
                tr("log.encoder.info_loudnorm_skipped", mode=loudnorm_mode), "info"
            )

        if source_audio_channels == 6:
            audio_filters.append("aformat=channel_layouts=5.1")
        elif source_audio_channels == 8:
            audio_filters.append("aformat=channel_layouts=7.1")

        if audio_filters:
            audio_args.extend(["-af", ",".join(audio_filters)])

        # 音频和字幕
        ffmpeg_success = False
        return_code = -1
        err_log = []
        retry_state = RetryState(
            use_hw_decode=self.config.get("hw_decoding", True),
            include_subtitles=True,
        )
        attempted_states = set()

        if retry_state.use_hw_decode and enc_name == "av1_nvenc":
            self.log_signal.emit(
                "💡 -> NVIDIA 硬件解码: CUDA (不依赖远程桌面图形会话)",
                "info",
            )

        err_log = []
        for attempt in range(3):
            if not self.is_running:
                return True, file_paused_time

            attempted_states.add(retry_state)
            cmd = [ffmpeg, "-y", "-hide_banner"]
            cmd.extend(build_hw_decode_args(enc_name, retry_state.use_hw_decode))

            cmd.extend(["-i", std_filepath])

            # 视频色彩控制参数
            color_mode = self.config.get("color_mode", "Auto")
            is_input_hdr = (
                color_transfer in ["smpte2084", "arib-std-b67"]
                or "bt2020" in color_space
                or "bt2020" in color_primaries
                or has_dovi
            )

            color_args = []
            if color_mode == "Auto" and is_input_hdr:
                if attempt == 0:
                    self.log_signal.emit(
                        "🌈 [色彩同调] 检测到 HDR/杜比视界 源视频，已自动激活色彩无损保留术式。",
                        "success",
                    )
                primaries = color_primaries if color_primaries else "bt2020"
                transfer = color_transfer if color_transfer else "smpte2084"
                space = color_space if color_space else "bt2020nc"
                color_args.extend(
                    [
                        "-color_primaries",
                        primaries,
                        "-color_trc",
                        transfer,
                        "-colorspace",
                        space,
                    ]
                )
            elif color_mode == "ToneMap" and is_input_hdr:
                if attempt == 0:
                    self.log_signal.emit(
                        "🔮 [色彩同调] 检测到 HDR/杜比视界 源视频，已施展高精度 32-bit 色调映射术式 (HDR to SDR)...",
                        "success",
                    )
                color_args.extend(
                    [
                        "-vf",
                        "zscale=t=linear:npl=100,format=gbrpf32,zscale=p=bt709:t=bt709:m=bt709:r=limited,format=yuv420p10le",
                    ]
                )
            elif color_mode == "ToneMap" and not is_input_hdr:
                if attempt == 0:
                    self.log_signal.emit(
                        "⚠️ [色彩同调] 虽启用了色调映射，但源视频并非 HDR/杜比视界，已跳过映射滤镜。",
                        "warning",
                    )

            # 视频编码参数
            cmd.extend(["-c:v", enc_name])
            if not (color_mode == "ToneMap" and is_input_hdr):
                cmd.extend(["-pix_fmt", PIX_FMT_10BIT])

            cmd.extend(color_args)

            if enc_name == "av1_qsv":
                cmd.extend(
                    [
                        "-global_quality:v",
                        str(best_icq),
                        "-preset",
                        enc_preset,
                        "-look_ahead",
                        "1",
                    ]
                )
            elif enc_name == "av1_nvenc":
                cmd.extend(["-cq", str(best_icq), "-preset", enc_preset, "-b:v", "0"])
                if self.config.get("nv_aq", True):
                    cmd.extend(["-spatial-aq", "1", "-temporal-aq", "1"])
            elif enc_name == "av1_amf":
                cmd.extend(
                    [
                        "-usage",
                        "transcoding",
                        "-quality",
                        enc_preset,
                        "-rc",
                        "vbr_latency",
                        "-qvbr_quality_level",
                        str(best_icq),
                    ]
                )
                if self.config.get(
                    "nv_aq", True
                ):  # 复用 nv_aq 开关作为 AMD PreAnalysis
                    cmd.extend(["-preanalysis", "true"])

            # 音频
            cmd.extend(audio_args)

            # 只有确认字幕流错误后才丢弃字幕
            if not retry_state.include_subtitles:
                cmd.extend(["-sn"])
                cmd.extend(["-map", "0:v:0", "-map", "0:a"])
            else:
                cmd.extend(["-c:s", sub_codec])
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
                with subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    startupinfo=startupinfo,
                    creationflags=get_subprocess_flags(),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                ) as proc:
                    self.current_proc = proc
                    max_percent = 0
                    while True:
                        if not self.is_running:
                            try:
                                proc.kill()
                            except Exception:  # noqa: S110, BLE001
                                pass
                            return True, file_paused_time
                        if self.is_paused:
                            p_start = time.time()
                            while self.is_paused:
                                if not self.is_running:
                                    break
                                time.sleep(0.1)
                            p_dt = time.time() - p_start
                            encode_paused_time += p_dt
                            file_paused_time += p_dt

                        line = proc.stdout.readline()
                        if not line and proc.poll() is not None:
                            break
                        if line:
                            d = line.strip()  # 已经是字符串，无需 safe_decode

                            # [Fix] 尝试从输出中补获时长 (防止元数据获取失败导致进度条不走)
                            if duration_sec <= 0 and "Duration:" in d:
                                dur_match = re.search(
                                    r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)", d
                                )
                                if dur_match:
                                    duration_sec = time_str_to_seconds(
                                        dur_match.group(1)
                                    )

                            if "time=" in d and duration_sec > 0:
                                t_match = re.search(
                                    r"time=\s*(\d+:\d+:\d+(?:\.\d+)?)", d
                                )
                                if t_match:
                                    current_sec = time_str_to_seconds(t_match.group(1))
                                    percent = min(
                                        100, int((current_sec / duration_sec) * 100)
                                    )
                                    if percent > max_percent:
                                        max_percent = percent
                                        mapped_percent = map_encode_progress(percent)
                                        self.progress_current_signal.emit(
                                            mapped_percent
                                        )
                                        self.file_progress_signal.emit(
                                            filepath,
                                            mapped_percent,
                                        )

                                    s_match = re.search(r"speed=\s*([\d.]+)x", d)
                                    if s_match:
                                        try:
                                            speed_val = float(s_match.group(1))
                                            if speed_val > 0:
                                                self.encoding_speed_signal.emit(
                                                    filepath,
                                                    speed_val,
                                                )
                                                remaining = (
                                                    duration_sec - current_sec
                                                ) / speed_val
                                                m, s = divmod(int(remaining), 60)
                                                h, m = divmod(m, 60)
                                                eta = f"ETA: {h:02d}:{m:02d}:{s:02d}"
                                                self.file_stats_signal.emit(
                                                    filepath, f"{speed_val:.2f}x", eta
                                                )
                                        except Exception:  # noqa: S110, BLE001
                                            pass

                            if "frame=" not in d:
                                err_log.append(d)
                                if len(err_log) > 200:
                                    err_log.pop(0)
                    return_code = proc.returncode
            except Exception as e:  # noqa: BLE001
                self.log_signal.emit(
                    tr("log.encoder.ffmpeg_exception", error=e), "error"
                )
                return_code = -999
                break
            finally:
                self.current_proc = None
                encode_duration = time.time() - encode_start_time - encode_paused_time

            if not self.is_running:
                return True, file_paused_time
            if return_code != 0:
                decision = next_retry_state(retry_state, err_log)
                can_retry = (
                    decision is not None
                    and decision.state not in attempted_states
                    and attempt < 2
                )
                if can_retry:
                    if decision.reason is FailureKind.HARDWARE_DEVICE:
                        self.log_signal.emit(
                            "⚠️ 检测到硬件解码设备初始化失败，"
                            "将仅对当前文件切换为 CPU 软件解码后重试；"
                            "NVENC 编码与画质参数保持不变。",
                            "warning",
                        )
                    elif decision.reason is FailureKind.SUBTITLE:
                        self.log_signal.emit(
                            "⚠️ 检测到字幕流损坏或不兼容，"
                            "将丢弃当前文件的字幕流后重试。",
                            "warning",
                        )

                    retry_state = decision.state
                    lp_temp = to_long_path(temp_file)
                    if os.path.exists(lp_temp):
                        try:
                            os.remove(lp_temp)
                        except Exception:  # noqa: S110, BLE001
                            pass
                    continue
            else:
                ffmpeg_success = True
                break

        if not self.is_running:
            lp_temp = to_long_path(temp_file)
            if os.path.exists(lp_temp):
                os.remove(lp_temp)
            return True, file_paused_time

        return self._handle_output(
            filepath,
            fname,
            temp_file,
            final_dest,
            save_mode,
            task_start_time,
            file_paused_time,
            encode_duration,
            ffmpeg_success,
            err_log,
        )

    def _handle_output(
        self,
        filepath,
        fname,
        temp_file,
        final_dest,
        save_mode,
        task_start_time,
        file_paused_time,
        encode_duration,
        ffmpeg_success,
        err_log,
    ):
        """处理转码输出：校验临时文件、移动最终结果、发出成功或失败状态信号。"""
        lp_temp = to_long_path(temp_file)
        if (
            ffmpeg_success
            and os.path.exists(lp_temp)
            and os.path.getsize(lp_temp) > 1024
        ):
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
                                # [Fix] 增强重试逻辑：仅当源文件存在时才执行重命名（防止重试时因源文件已更名而报错）
                                if os.path.exists(lp_src):
                                    if os.path.exists(bak_path):
                                        os.remove(bak_path)
                                    os.replace(lp_src, bak_path)

                                shutil.move(lp_temp, lp_dest)
                                if os.path.exists(bak_path):
                                    os.remove(bak_path)
                            else:
                                if os.path.exists(lp_dest):
                                    os.remove(lp_dest)
                                shutil.move(lp_temp, lp_dest)
                                if os.path.exists(lp_src):
                                    os.remove(lp_src)
                            success = True
                            break
                        except Exception:  # noqa: BLE001
                            time.sleep(1)

                    if success:
                        self.log_signal.emit(
                            tr(
                                "log.encoder.success_overwrite",
                                encode_duration=encode_duration,
                                total_duration=total_duration,
                            ),
                            "success",
                        )
                        self.file_stats_signal.emit(
                            filepath,
                            tr("log.encoder.status_done"),
                            tr(
                                "log.encoder.status_duration",
                                total_duration=total_duration,
                            ),
                        )
                        self.file_status_signal.emit(filepath, "success")
                    else:
                        raise OSError(tr("log.encoder.error_move_overwrite"))
                else:
                    for _ in range(3):
                        try:
                            if os.path.exists(lp_dest):
                                os.remove(lp_dest)
                            shutil.move(lp_temp, lp_dest)
                            break
                        except Exception:  # noqa: BLE001
                            time.sleep(1)

                    if save_mode == SAVE_MODE_REMAIN:
                        self.log_signal.emit(
                            tr(
                                "log.encoder.success_remain",
                                encode_duration=encode_duration,
                                total_duration=total_duration,
                            ),
                            "success",
                        )
                    else:
                        self.log_signal.emit(
                            tr(
                                "log.encoder.success_save_as",
                                encode_duration=encode_duration,
                                total_duration=total_duration,
                            ),
                            "success",
                        )
                    self.file_stats_signal.emit(
                        filepath,
                        tr("log.encoder.status_done"),
                        tr(
                            "log.encoder.status_duration", total_duration=total_duration
                        ),
                    )
                    self.file_status_signal.emit(filepath, "success")
            except Exception as e:  # noqa: BLE001
                self.log_signal.emit(tr("log.encoder.error_move", error=e), "error")
                self.file_status_signal.emit(filepath, "error")
            return False, file_paused_time
        else:
            self.log_signal.emit(tr("log.encoder.ffmpeg_crash"), "error")
            self.file_status_signal.emit(filepath, "error")
            for err_line in err_log:
                self.log_signal.emit(f"   {err_line}", "error")
            if is_hardware_resource_error(err_log):
                self.resource_error_signal.emit(
                    filepath,
                    err_log[-1] if err_log else "",
                )
            lp_temp = to_long_path(temp_file)
            if os.path.exists(lp_temp):
                os.remove(lp_temp)

            if self.is_running:
                self.waiting_decision = True
                self.decision = None
                self.ask_error_decision.emit(
                    tr("dialog.encoder.crash_title"),
                    tr("dialog.encoder.crash_content", fname=fname),
                )
                while self.waiting_decision and self.is_running:
                    time.sleep(0.1)
                if self.decision == "stop":
                    return True, file_paused_time
            return True, file_paused_time

    def _cleanup(self):
        """清理会话任务目录、恢复系统喚醒状态，并通知主线程结束。"""
        if self.task_paths is not None:
            shutil.rmtree(
                self.task_paths.task_dir,
                ignore_errors=True,
            )
        if self.manage_system_awake:
            self.set_system_awake(False)
        self.finished_signal.emit()

    def run(self):
        """线程的主执行体，包含完整的编码流程。"""
        # --- 1. 解包配置 ---
        selected_files = self.config.get("selected_files") or []
        encoder_type = self.config.get("encoder", "Intel QSV")
        export_dir = self.config.get("export_dir", "")
        cache_dir = (
            self.task_paths.ab_av1_dir
            if self.task_paths is not None
            else self.config.get("cache_dir") or get_default_cache_dir()
        )
        save_mode = self.config.get("save_mode", SAVE_MODE_OVERWRITE)
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception:  # noqa: BLE001
            cache_dir = ""
        preset = self.config["preset"]
        target_vmaf = self.config["vmaf"]
        audio_bitrate = self.config["audio_bitrate"]
        loudnorm = self.config["loudnorm"]
        loudnorm_mode = self.config.get("loudnorm_mode", LOUDNORM_MODE_AUTO)

        ffmpeg = tool_path("ffmpeg.exe")
        ffprobe = tool_path("ffprobe.exe")
        ab_av1 = tool_path("ab-av1.exe")

        os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            if self.manage_system_awake:
                self.set_system_awake(True)
            tasks = []

            for p in selected_files:
                if os.path.isfile(p) and p.lower().endswith(VIDEO_EXTS):
                    tasks.append(p)

            if self.task_paths is not None and len(tasks) > 1:
                raise ValueError("coordinated EncoderWorker accepts exactly one file")

            total_tasks = len(tasks)
            if total_tasks == 0:
                self.log_signal.emit(tr("log.encoder.no_files_found"), "error")
                self.finished_signal.emit()
                return

            self.log_signal.emit(
                tr("log.encoder.tasks_found", total_tasks=total_tasks), "info"
            )

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
                if p_val <= 2:
                    enc_preset = "quality"
                elif p_val <= 5:
                    enc_preset = "balanced"
                else:
                    enc_preset = "speed"
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
                self.log_signal.emit(
                    tr(
                        "log.encoder.task_start",
                        i=i + 1,
                        total_tasks=total_tasks,
                        fname=fname,
                    ),
                    "info",
                )
                self.file_status_signal.emit(filepath, "processing")

                self.progress_total_signal.emit(int((i / total_tasks) * 100))
                self.progress_current_signal.emit(0)

                # --- 3.1 获取或补测媒体元数据 ---
                (
                    codec,
                    duration_sec,
                    source_audio_channels,
                    _pix_fmt,
                    color_space,
                    color_transfer,
                    color_primaries,
                    has_dovi,
                ) = self._probe_metadata(filepath, std_filepath, ffprobe)
                # --- 3.2 如果已是AV1则跳过 ---
                if self._skip_av1(filepath, codec, task_start_time):
                    continue
                # --- 3.3 ab-av1 VMAF 探测 ---
                (
                    best_icq,
                    search_success,
                    _final_strategy,
                    _search_duration,
                    file_paused_time,
                    stop_processing,
                ) = self._probe_vmaf(
                    std_filepath,
                    filepath,
                    fname,
                    enc_name,
                    enc_preset,
                    p_val,
                    target_vmaf,
                    enc_pix_fmt,
                    cache_dir,
                    ab_av1,
                    file_paused_time,
                )
                if stop_processing:
                    break
                if not search_success:
                    continue

                # --- 3.4 FFmpeg 转码执行 ---
                stop_ffmpeg, file_paused_time = self._execute_ffmpeg(
                    filepath,
                    std_filepath,
                    fname,
                    ffmpeg,
                    enc_name,
                    enc_preset,
                    best_icq,
                    save_mode,
                    color_transfer,
                    color_space,
                    color_primaries,
                    has_dovi,
                    duration_sec,
                    source_audio_channels,
                    task_start_time,
                    file_paused_time,
                    cache_dir,
                    export_dir,
                    audio_bitrate,
                    loudnorm,
                    loudnorm_mode,
                    startupinfo,
                )
                if stop_ffmpeg:
                    break

                if self.is_running:
                    self.log_signal.emit(tr("log.encoder.cooling_down"), "info")
                    cooling_time = int(self.config.get("gpu_cooling_time", 3))
                    time.sleep(cooling_time)

            if self.is_running:
                self.log_signal.emit(tr("log.encoder.all_done"), "success")
                self.progress_total_signal.emit(100)
                self.progress_current_signal.emit(100)
            else:
                self.log_signal.emit(tr("log.encoder.stopped"), "error")

        except Exception as e:  # noqa: BLE001
            self.log_signal.emit(tr("log.encoder.fatal_error", error=e), "error")
        finally:
            self._cleanup()
