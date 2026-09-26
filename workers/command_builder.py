"""FFmpeg / ab-av1 命令构造：纯函数模块。

本模块从 EncoderWorker 中拆出，只负责按既有参数顺序拼装命令行参数，
不导入 Qt、不发送信号、不打印日志。所有字符串值与拆分前逐字保持一致，
由 tests/test_command_builder.py 与 tests/test_encoder.py 的 argv 快照测试锁定。

Qt-free 传递性约束：本模块**只依赖标准库**（import os），不导入 config.py，
避免经 config -> PySide6 传递性地引入 Qt。音频编码器/采样率与各模式协议
常量由调用方（EncoderWorker 从 config 透传）以显式参数传入；未传时使用
与 config 一致的字面量默认值，保证单独调用/测试行为与拆分前逐字相同。
"""

import os


def should_apply_loudnorm(
    loudnorm_mode,
    source_audio_channels,
    loudnorm_mode_always="Always",
    loudnorm_mode_auto="Stereo/Mono Only",
):
    """判断是否满足 loudnorm 启用条件（Always 或 Auto + 立体声/单声道）。

    模式常量由调用方显式传入（EncoderWorker 从 config 透传），本模块不导入
    config，因此可独立于 Qt 环境导入与单测。
    """
    return (loudnorm_mode == loudnorm_mode_always) or (
        loudnorm_mode == loudnorm_mode_auto
        and (source_audio_channels is None or source_audio_channels <= 2)
    )


def build_ab_av1_search_cmd(
    ab_av1,
    std_filepath,
    encoder,
    pix_fmt,
    target_vmaf,
    preset,
    max_crf,
    cache_dir=None,
):
    """构造 ab-av1 crf-search 探测命令。

    max_crf 由调用方按编码器区分（硬件 51 / CPU 63）；cache_dir 真实存在时
    追加 --temp-dir，行为与拆分前一致。
    """
    cmd = [
        ab_av1,
        "crf-search",
        "-i",
        std_filepath,
        "--encoder",
        encoder,
        "--pix-format",
        pix_fmt,
        "--min-vmaf",
        str(target_vmaf),
        "--preset",
        preset,
        "--max-crf",
        max_crf,
    ]
    if cache_dir and os.path.isdir(cache_dir):
        cmd.extend(["--temp-dir", cache_dir])
    return cmd


def build_audio_args(
    audio_bitrate,
    loudnorm,
    loudnorm_mode,
    source_audio_channels,
    audio_codec="libopus",
    sample_rate="48000",
    loudnorm_mode_always="Always",
    loudnorm_mode_auto="Stereo/Mono Only",
):
    """构造音频参数：libopus 码率/采样率 + 可选的 loudnorm/声道布局滤镜。

    保留 loudnorm 启用判定与 6/8 声道 aformat 行为；不在此记录日志，
    日志由 EncoderWorker 依据 should_apply_loudnorm() 发射。音频编码器与
    采样率默认值对应 config.AUDIO_CODEC / config.SAMPLE_RATE，由调用方
    （EncoderWorker 从 config 透传）覆盖，避免本模块导入 config。
    """
    args = ["-c:a", audio_codec, "-b:a", audio_bitrate, "-ar", sample_rate]
    audio_filters = []
    if (
        should_apply_loudnorm(
            loudnorm_mode,
            source_audio_channels,
            loudnorm_mode_always,
            loudnorm_mode_auto,
        )
        and loudnorm
    ):
        audio_filters.append(loudnorm)
    if source_audio_channels == 6:
        audio_filters.append("aformat=channel_layouts=5.1")
    elif source_audio_channels == 8:
        audio_filters.append("aformat=channel_layouts=7.1")
    if audio_filters:
        args.extend(["-af", ",".join(audio_filters)])
    return args


def build_color_args(
    color_mode,
    color_transfer,
    color_space,
    color_primaries,
    has_dovi,
    color_mode_auto="Auto",
    color_mode_tonemap="ToneMap",
):
    """构造色彩参数，并返回 is_input_hdr 供调用方决定 pix_fmt。

    is_input_hdr 为真时：Auto 模式输出 -color_primaries/-color_trc/-colorspace，
    ToneMap 模式输出 zscale 色调映射 -vf 滤镜；SDR（Force SDR）与其他模式
    一样落入 fallthrough，返回空列表（不做映射也不写色彩标签）。
    色彩模式协议常量由调用方（EncoderWorker 从 config 透传）显式传入，
    本模块不导入 config，可独立于 Qt 环境导入与单测。
    """
    is_input_hdr = (
        color_transfer in ["smpte2084", "arib-std-b67"]
        or "bt2020" in color_space
        or "bt2020" in color_primaries
        or has_dovi
    )

    color_args = []
    if color_mode == color_mode_auto and is_input_hdr:
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
    elif color_mode == color_mode_tonemap and is_input_hdr:
        color_args.extend(
            [
                "-vf",
                (
                    "zscale=t=linear:npl=100,format=gbrpf32,"
                    "zscale=p=bt709:t=bt709:m=bt709:r=limited,"
                    "format=yuv420p10le"
                ),
            ]
        )
    return color_args, is_input_hdr


def build_video_encoder_args(enc_name, best_icq, enc_preset, nv_aq=True):
    """按编码器构造视频参数（不含 -c:v / -pix_fmt，由调用方拼装）。

    QSV 用 -global_quality:v，NVENC 用 -cq（nv_aq 时追加 AQ），
    AMF 用 -qvbr_quality_level（nv_aq 复用作 PreAnalysis 开关）。
    """
    args = []
    if enc_name == "av1_qsv":
        args.extend(
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
        args.extend(["-cq", str(best_icq), "-preset", enc_preset, "-b:v", "0"])
        if nv_aq:
            args.extend(["-spatial-aq", "1", "-temporal-aq", "1"])
    elif enc_name == "av1_amf":
        args.extend(
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
        if nv_aq:
            # 复用 nv_aq 开关作为 AMD PreAnalysis
            args.extend(["-preanalysis", "true"])
    return args


def build_subtitle_args(include_subtitles, sub_codec):
    """构造字幕参数：包含字幕时用 -c:s + -map 0:s?，否则 -sn + 仅音视频 map。"""
    if include_subtitles:
        return [
            "-c:s",
            sub_codec,
            "-map",
            "0:v:0",
            "-map",
            "0:a",
            "-map",
            "0:s?",
        ]
    return ["-sn", "-map", "0:v:0", "-map", "0:a"]
