"""媒体报告 HTML 渲染：将 ffprobe JSON 数据渲染为格式化报告。

本模块从 AnalysisWorker 中拆出，是纯渲染函数：不启动 ffprobe、
不访问 Qt 控件、不发送信号。所有动态字段均经 HTML 转义，防止
外部媒体元数据 / 文件路径注入 HTML。
"""

import html

from i18n.translator import tr


def _escape_html_value(value):
    return html.escape(str(value))


def _infer_bit_depth(bit_depth, pix_fmt):
    """从 bits_per_raw_sample 或 pix_fmt 推断位深。

    ffprobe 有时不提供 bits_per_raw_sample，此时按像素格式后缀
    （如 yuv420p10le / p010le）推断，与旧 AnalysisWorker 行为一致。
    """
    if not bit_depth or str(bit_depth) == "0":
        if "16le" in pix_fmt or "16be" in pix_fmt:
            return "16"
        if "14le" in pix_fmt or "14be" in pix_fmt:
            return "14"
        if "12le" in pix_fmt or "12be" in pix_fmt:
            return "12"
        if "10le" in pix_fmt or "10be" in pix_fmt or "p010" in pix_fmt:
            return "10"
        if "9le" in pix_fmt or "9be" in pix_fmt:
            return "9"
        return "8"
    return bit_depth


def build_media_report(
    data: dict, filepath: str, is_dark: bool = False
) -> tuple[str, bool]:
    """将 ffprobe JSON 字典渲染为 HTML 媒体报告。

    返回 (html, should_hide_add_button)。should_hide 规则：当容器为
    MKV 且视频流为 AV1 时返回 True（视为"完美形态"并隐藏添加按钮）。
    颜色按 is_dark 切换明暗主题，其余结构沿用原 AnalysisWorker 输出。
    """
    title_color = "#FB7299"
    container_color = "#9B59B6" if not is_dark else "#C39BD3"
    video_color = "#2ECC71" if not is_dark else "#82E0AA"
    audio_color = "#E67E22" if not is_dark else "#F5CBA7"
    subtitle_color = "#3498DB" if not is_dark else "#85C1E9"
    key_color = "#7F8C8D" if not is_dark else "#BDC3C7"
    val_color = "#2C3E50" if not is_dark else "#ECF0F1"

    html = [
        "<div style=\"font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace; font-size: 13px; line-height: 1.6;\">"
    ]
    html.append('<div style="text-align: center; margin-bottom: 15px;">')
    html.append(
        f'<h2 style="color: {title_color}; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">{tr("info.report.title")}</h2>'
    )
    html.append(
        f'<div style="color: {key_color}; font-size: 11px; margin-top: 4px;">{_escape_html_value(filepath)}</div>'
    )
    html.append("</div>")

    # 1. 容器信息
    fmt = data.get("format", {})
    is_mkv = "matroska" in fmt.get("format_name", "").lower()
    duration_sec = float(fmt.get("duration", 0))
    m, s = divmod(int(duration_sec), 60)
    h, m = divmod(m, 60)
    duration_hms = f"{h:02d}:{m:02d}:{s:02d}"

    html.append(
        f'<div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid {container_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">'
    )
    html.append(
        f'<b style="color: {container_color}; font-size: 14px;">{tr("info.report.container_title")}</b><br/>'
    )
    html.append(
        f'<span style="color: {key_color};">{tr("info.report.format")}</span> <span style="color: {val_color};">{_escape_html_value(fmt.get("format_long_name", "Unknown"))}</span><br/>'
    )
    html.append(
        f'<span style="color: {key_color};">{tr("info.report.size")}</span> <span style="color: {val_color};">{int(fmt.get("size", 0)) / 1024 / 1024:.2f} MB</span><br/>'
    )
    html.append(
        f'<span style="color: {key_color};">{tr("info.report.duration")}</span> <span style="color: {val_color};">{duration_sec:.2f} s ({duration_hms})</span><br/>'
    )
    html.append(
        f'<span style="color: {key_color};">{tr("info.report.total_bitrate")}</span> <span style="color: {val_color};">{int(fmt.get("bit_rate", 0)) / 1000:.0f} kbps</span><br/>'
    )
    html.append(
        f'<span style="color: {key_color};">{tr("info.report.stream_count")}</span> <span style="color: {val_color};">{len(data.get("streams", []))}</span><br/>'
    )
    html.append("</div>")

    # 2. 流信息
    is_av1 = False
    for stream in data.get("streams", []):
        idx = stream.get("index")
        st_type = stream.get("codec_type", "unknown").upper()
        codec_name = stream.get("codec_name", "").lower()
        codec_display = stream.get(
            "codec_long_name", stream.get("codec_name", "Unknown")
        )

        if st_type == "VIDEO":
            if "av1" in codec_name:
                is_av1 = True
            html.append(
                f'<div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid {video_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">'
            )
            html.append(
                f'<b style="color: {video_color}; font-size: 14px;">{tr("info.report.video_title", idx=idx)}</b><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.codec")}</span> <span style="color: {val_color};">{_escape_html_value(codec_display)}</span><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.profile_level")}</span> <span style="color: {val_color};">{_escape_html_value(stream.get("profile", "N/A"))} @ Level {_escape_html_value(stream.get("level", "N/A"))}</span><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.resolution")}</span> <span style="color: {val_color};">{_escape_html_value(stream.get("width"))} x {_escape_html_value(stream.get("height"))} (DAR: {_escape_html_value(stream.get("display_aspect_ratio", "N/A"))})</span><br/>'
            )

            pix_fmt = stream.get("pix_fmt", "")
            bit_depth = _infer_bit_depth(stream.get("bits_per_raw_sample"), pix_fmt)

            html.append(
                f'<span style="color: {key_color};">{tr("info.report.pix_fmt")}</span> <span style="color: {val_color};">{_escape_html_value(pix_fmt)} ({_escape_html_value(bit_depth)} bit)</span><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.color_space")}</span> <span style="color: {val_color};">{_escape_html_value(stream.get("color_space", "N/A"))} / {_escape_html_value(stream.get("color_range", "N/A"))}</span><br/>'
            )
            if "bit_rate" in stream:
                html.append(
                    f'<span style="color: {key_color};">{tr("info.report.bitrate")}</span> <span style="color: {val_color};">{int(stream.get("bit_rate")) / 1000:.0f} kbps</span><br/>'
                )
            html.append("</div>")

        elif st_type == "AUDIO":
            html.append(
                f'<div style="background: rgba(230, 126, 34, 0.08); border-left: 4px solid {audio_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">'
            )
            html.append(
                f'<b style="color: {audio_color}; font-size: 14px;">{tr("info.report.audio_title", idx=idx)}</b><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.codec")}</span> <span style="color: {val_color};">{_escape_html_value(codec_display)}</span><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.sample_rate")}</span> <span style="color: {val_color};">{_escape_html_value(stream.get("sample_rate"))} Hz</span><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.sample_fmt")}</span> <span style="color: {val_color};">{_escape_html_value(stream.get("sample_fmt", "N/A"))}</span><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.channel_layout")}</span> <span style="color: {val_color};">{_escape_html_value(stream.get("channels"))} ch ({_escape_html_value(stream.get("channel_layout", "N/A"))})</span><br/>'
            )
            if "bit_rate" in stream:
                html.append(
                    f'<span style="color: {key_color};">{tr("info.report.bitrate")}</span> <span style="color: {val_color};">{int(stream.get("bit_rate")) / 1000:.0f} kbps</span><br/>'
                )
            html.append("</div>")

        elif st_type == "SUBTITLE":
            html.append(
                f'<div style="background: rgba(52, 152, 219, 0.08); border-left: 4px solid {subtitle_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">'
            )
            html.append(
                f'<b style="color: {subtitle_color}; font-size: 14px;">{tr("info.report.subtitle_title", idx=idx)}</b><br/>'
            )
            html.append(
                f'<span style="color: {key_color};">{tr("info.report.codec")}</span> <span style="color: {val_color};">{_escape_html_value(codec_display)}</span><br/>'
            )
            if "tags" in stream and "language" in stream["tags"]:
                html.append(
                    f'<span style="color: {key_color};">{tr("info.report.language")}</span> <span style="color: {val_color};">{_escape_html_value(stream["tags"]["language"])}</span><br/>'
                )
            html.append("</div>")

    html.append("</div>")

    if is_mkv and is_av1:
        html.insert(
            1,
            f'<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F1C40F, stop:1 #F39C12); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; display: inline-block; font-size: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">{tr("info.report.perfect_form")}</div>',
        )

    should_hide = is_mkv and is_av1
    return "".join(html), should_hide
