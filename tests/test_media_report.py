"""Media report rendering tests for the Magical Girl Workshop.

build_media_report() 是纯渲染函数：输入 ffprobe JSON 字典 + 文件路径 +
主题状态，输出 (HTML, should_hide)。本测试不依赖 Qt / ffprobe / GPU。
"""

import unittest

from workers.media_report import build_media_report


def _make_data(
    duration=120.0,
    has_video=True,
    has_audio=True,
    has_subtitle=False,
    is_mkv=False,
    codec="h264",
    pix_fmt="yuv420p",
):
    streams = []
    if has_video:
        s = {
            "index": 0,
            "codec_type": "video",
            "codec_name": codec,
            "codec_long_name": "H.264 / AVC" if codec == "h264" else "AV1",
            "width": 1920,
            "height": 1080,
            "pix_fmt": pix_fmt,
            "display_aspect_ratio": "16:9",
            "color_space": "bt709",
            "color_range": "tv",
            "bits_per_raw_sample": "8",
            "bit_rate": "5000000",
        }
        if is_mkv:
            s["codec_name"] = "av1"
        streams.append(s)
    if has_audio:
        streams.append(
            {
                "index": 1 if has_video else 0,
                "codec_type": "audio",
                "codec_name": "aac",
                "codec_long_name": "AAC",
                "sample_rate": "48000",
                "sample_fmt": "fltp",
                "channels": 2,
                "channel_layout": "stereo",
                "bit_rate": "128000",
            }
        )
    if has_subtitle:
        sidx = 2 if has_video and has_audio else (1 if has_video or has_audio else 0)
        streams.append(
            {
                "index": sidx,
                "codec_type": "subtitle",
                "codec_name": "subrip",
                "codec_long_name": "SubRip subtitle",
                "tags": {"language": "chi"},
            }
        )
    return {
        "format": {
            "filename": "test.mkv" if is_mkv else "test.mp4",
            "format_name": "matroska,webm" if is_mkv else "mov,mp4,m4a,3gp,3g2,mj2",
            "format_long_name": "Matroska / WebM" if is_mkv else "QuickTime / MOV",
            "size": "10485760",
            "duration": str(duration),
            "bit_rate": "2000000",
        },
        "streams": streams,
    }


class BuildMediaReportTests(unittest.TestCase):
    def test_report_contains_title(self):
        html, should_hide = build_media_report(_make_data(), "test.mp4")
        self.assertIn("\U0001f4dc", html)  # 物质真理鉴定书标题 emoji
        self.assertFalse(should_hide)

    def test_report_contains_filepath(self):
        html, _ = build_media_report(_make_data(), "test.mp4")
        self.assertIn("test.mp4", html)

    def test_report_contains_video_codec(self):
        html, _ = build_media_report(_make_data(), "test.mp4")
        self.assertIn("H.264", html)

    def test_report_contains_resolution(self):
        html, _ = build_media_report(_make_data(), "test.mp4")
        self.assertIn("1920", html)
        self.assertIn("1080", html)

    def test_report_contains_pix_fmt(self):
        html, _ = build_media_report(_make_data(), "test.mp4")
        self.assertIn("yuv420p", html)

    def test_report_contains_audio_codec(self):
        html, _ = build_media_report(_make_data(), "test.mp4")
        self.assertIn("AAC", html)

    def test_report_contains_sample_rate(self):
        html, _ = build_media_report(_make_data(), "test.mp4")
        self.assertIn("48000 Hz", html)

    def test_report_contains_subtitle_info(self):
        html, _ = build_media_report(_make_data(has_subtitle=True), "test.mkv")
        self.assertIn("SubRip", html)
        self.assertIn("chi", html)

    def test_report_contains_container_size(self):
        html, _ = build_media_report(_make_data(duration=120.0), "test.mp4")
        self.assertIn("10.00 MB", html)

    def test_report_contains_duration(self):
        html, _ = build_media_report(_make_data(duration=120.0), "test.mp4")
        self.assertIn("120.00", html)

    def test_mkv_av1_returns_should_hide_and_marker(self):
        html, should_hide = build_media_report(
            _make_data(is_mkv=True, codec="av1"), "test.mkv"
        )
        self.assertIn("\u2728", html)  # 完美形态标记 emoji
        self.assertTrue(should_hide)

    def test_mp4_h264_no_marker(self):
        html, should_hide = build_media_report(
            _make_data(is_mkv=False, codec="h264"), "test.mp4"
        )
        self.assertNotIn("\u2728", html)
        self.assertFalse(should_hide)

    def test_dark_theme_uses_different_colors(self):
        light_html, _ = build_media_report(_make_data(), "test.mp4", is_dark=False)
        dark_html, _ = build_media_report(_make_data(), "test.mp4", is_dark=True)
        self.assertNotEqual(light_html, dark_html)
        # 暗色主题包含容器标题 emoji（同一翻译键），且颜色风格切换
        self.assertIn("\U0001f4e6", dark_html)

    def test_escapes_malicious_filepath_and_format_long_name(self):
        data = _make_data()
        data["format"]["format_long_name"] = "<script>alert(1)</script> & MOV"
        filepath = 'unsafe <script>alert("path")</script>.mp4'
        html, _ = build_media_report(data, filepath)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; &amp; MOV", html)
        self.assertIn(
            "unsafe &lt;script&gt;alert(&quot;path&quot;)&lt;/script&gt;.mp4",
            html,
        )


if __name__ == "__main__":
    unittest.main()
