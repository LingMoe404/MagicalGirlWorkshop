"""AnalysisWorker tests for the Magical Girl Workshop."""

import json
import unittest
from unittest.mock import patch

from workers.analyzer import AnalysisWorker, DurationWorker, ThumbnailWorker


class FakeSignal:
    def __init__(self):
        self._callbacks = []
        self.emissions = []
    def connect(self, cb):
        self._callbacks.append(cb)
    def emit(self, *a):
        self.emissions.append(a)
        for cb in tuple(self._callbacks):
            cb(*a)


class FakeProcess:
    def __init__(self, stdout_data, returncode=0, stderr_data=b""):
        self._stdout = stdout_data if isinstance(stdout_data, bytes) else stdout_data.encode("utf-8")
        self._stderr = stderr_data if isinstance(stderr_data, bytes) else stderr_data.encode("utf-8")
        self._returncode = returncode
        self.pid = 42
        self.stdout = None
        self.stderr = None
    def communicate(self, input=None, timeout=None):
        return self._stdout, self._stderr
    @property
    def returncode(self):
        return self._returncode
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass
    def kill(self):
        pass
    def terminate(self):
        pass


def _make_ffprobe_output(duration=120.0, has_video=True, has_audio=True, has_subtitle=False,
                          is_mkv=False, codec="h264", pix_fmt="yuv420p"):
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
        streams.append({
            "index": 1 if has_video else 0,
            "codec_type": "audio",
            "codec_name": "aac",
            "codec_long_name": "AAC",
            "sample_rate": "48000",
            "sample_fmt": "fltp",
            "channels": 2,
            "channel_layout": "stereo",
            "bit_rate": "128000",
        })
    if has_subtitle:
        sidx = 2 if has_video and has_audio else (1 if has_video or has_audio else 0)
        streams.append({
            "index": sidx,
            "codec_type": "subtitle",
            "codec_name": "subrip",
            "codec_long_name": "SubRip subtitle",
            "tags": {"language": "chi"},
        })
    data = {
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
    return json.dumps(data).encode("utf-8")


class FakeQImage:
    @classmethod
    def fromData(cls, data):
        return cls()
    def isNull(self):
        return False


class AnalysisWorkerTests(unittest.TestCase):
    def _run_analysis(self, ffprobe_data, filepath="test.mp4", is_dark=False):
        worker = AnalysisWorker(filepath)
        worker.report_signal = FakeSignal()
        with patch("subprocess.Popen") as mock_popen, patch("qfluentwidgets.isDarkTheme", return_value=is_dark), patch("workers.analyzer.tool_path", return_value="ffprobe.exe"):
            proc = FakeProcess(ffprobe_data)
            mock_popen.return_value = proc
            worker.run()
        return worker

    def test_report_contains_title_emoji(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("\U0001f4dc", html)

    def test_report_contains_filepath(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("test.mp4", html)

    def test_report_contains_video_codec(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("H.264", html)

    def test_report_contains_resolution(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("1920", html)
        self.assertIn("1080", html)

    def test_report_contains_pix_fmt(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("yuv420p", html)

    def test_report_contains_audio_codec(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("AAC", html)

    def test_report_contains_sample_rate(self):
        worker = self._run_analysis(_make_ffprobe_output())
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("48000 Hz", html)

    def test_report_contains_subtitle_info(self):
        worker = self._run_analysis(_make_ffprobe_output(has_subtitle=True))
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("SubRip", html)
        self.assertIn("chi", html)

    def test_report_contains_container_size(self):
        worker = self._run_analysis(_make_ffprobe_output(duration=120.0))
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("10.00 MB", html)

    def test_report_contains_duration(self):
        worker = self._run_analysis(_make_ffprobe_output(duration=120.0))
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("120.00", html)

    def test_mkv_av1_shows_perfect_form_badge(self):
        worker = self._run_analysis(_make_ffprobe_output(is_mkv=True, codec="av1"), filepath="test.mkv")
        html, should_hide = worker.report_signal.emissions[0]
        self.assertIn("\u2728", html)
        self.assertTrue(should_hide)

    def test_mp4_h264_does_not_show_perfect_form(self):
        worker = self._run_analysis(_make_ffprobe_output(is_mkv=False, codec="h264"), filepath="test.mp4")
        _html, should_hide = worker.report_signal.emissions[0]
        self.assertFalse(should_hide)

    def test_dark_theme_uses_different_colors(self):
        worker = self._run_analysis(_make_ffprobe_output(), is_dark=True)
        html, _ = worker.report_signal.emissions[0]
        self.assertIn("\U0001f4e6", html)

    def test_ffprobe_failure_emits_error_html(self):
        worker = AnalysisWorker("nonexistent.mp4")
        worker.report_signal = FakeSignal()
        with patch("subprocess.Popen") as mock_popen, patch("qfluentwidgets.isDarkTheme", return_value=False), patch("workers.analyzer.tool_path", return_value="ffprobe.exe"):
            proc = FakeProcess(b"", returncode=1, stderr_data=b"ffprobe error")
            mock_popen.return_value = proc
            worker.run()
        html, should_hide = worker.report_signal.emissions[0]
        self.assertIn("\U0001f4a5", html)
        self.assertTrue(should_hide)


class DurationWorkerTests(unittest.TestCase):
    def test_parses_duration_and_metadata(self):
        worker = DurationWorker("test.mp4")
        worker.result = FakeSignal()
        data = _make_ffprobe_output(duration=65.0)
        with patch("subprocess.Popen") as mock_popen, patch("workers.analyzer.tool_path", return_value="ffprobe.exe"):
            proc = FakeProcess(data)
            mock_popen.return_value = proc
            worker.run()
        path, dur_str, dur_sec, meta = worker.result.emissions[0]
        self.assertEqual(path, "test.mp4")
        self.assertEqual(dur_str, "01:05")
        self.assertAlmostEqual(dur_sec, 65.0)
        self.assertEqual(meta["codec"], "h264")
        self.assertEqual(meta["channels"], 2)

    def test_error_returns_empty_metadata(self):
        worker = DurationWorker("test.mp4")
        worker.result = FakeSignal()
        with patch("subprocess.Popen") as mock_popen, patch("workers.analyzer.tool_path", return_value="ffprobe.exe"):
            proc = FakeProcess(b"", returncode=1)
            mock_popen.return_value = proc
            worker.run()
        _path, dur_str, dur_sec, meta = worker.result.emissions[0]
        self.assertEqual(dur_str, "N/A")
        self.assertEqual(dur_sec, 0.0)
        self.assertEqual(meta, {})


class ThumbnailWorkerTests(unittest.TestCase):
    @patch("workers.analyzer.QImage.fromData", return_value=FakeQImage())
    def test_thumbnail_generated(self, mock_from_data):
        with patch("random.uniform", return_value=30.0), patch("subprocess.Popen") as mock_popen, patch("workers.analyzer.tool_path", return_value="ffmpeg.exe"):
            proc = FakeProcess(b"fake_image_data")
            mock_popen.return_value = proc
            worker = ThumbnailWorker("test.mp4", 100.0)
            worker.result = FakeSignal()
            worker.run()
            self.assertEqual(len(worker.result.emissions), 1)
            self.assertEqual(worker.result.emissions[0][0], "test.mp4")

    def test_thumbnail_ffmpeg_failure(self):
        with patch("subprocess.Popen") as mock_popen, patch("workers.analyzer.tool_path", return_value="ffmpeg.exe"):
            proc = FakeProcess(b"", returncode=1)
            mock_popen.return_value = proc
            worker = ThumbnailWorker("test.mp4", 100.0)
            worker.result = FakeSignal()
            worker.run()
            self.assertEqual(len(worker.result.emissions), 1)


if __name__ == "__main__":
    unittest.main()
