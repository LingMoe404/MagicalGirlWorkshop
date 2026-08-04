"""Integration tests: create synthetic video, test pipeline."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class IntegrationTests(unittest.TestCase):
    """Tests that use real ffmpeg to create synthetic test videos."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp_dir.name)
        cls.ffmpeg = cls._find_tool("ffmpeg.exe")
        cls.ffprobe = cls._find_tool("ffprobe.exe")
        if not cls.ffmpeg or not cls.ffprobe:
            raise unittest.SkipTest("ffmpeg/ffprobe not found in tools/")

    @classmethod
    def _find_tool(cls, name):
        base = os.path.dirname(os.path.abspath(__file__))
        for root_dir in [os.path.join(base, ".."), os.path.join(base, "..", "tools")]:
            path = os.path.join(root_dir, name)
            if os.path.exists(path):
                return path
        return None

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _create_synthetic_video(self, duration=5, codec="libx264", pix_fmt="yuv420p",
                                 size="192x108", filename="test_synthetic.mp4"):
        """Use ffmpeg to create a synthetic test video."""
        output = self.root / filename
        cmd = [
            self.ffmpeg, "-y", "-f", "lavfi",
            "-i", f"testsrc=duration={duration}:size={size}:rate=30",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", codec,
            "-pix_fmt", pix_fmt,
            "-c:a", "aac",
            "-shortest",
            str(output),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
        self.assertEqual(
            result.returncode, 0,
            f"ffmpeg failed: {result.stderr[:200]}",
        )
        self.assertTrue(output.exists(), "Output file was not created")
        return output

    def test_create_synthetic_video(self):
        """ffmpeg can create a synthetic test video."""
        video = self._create_synthetic_video(duration=3)
        self.assertGreater(video.stat().st_size, 100, "Video file is too small")

    def test_ffprobe_reads_metadata(self):
        """ffprobe can read metadata from synthetic video."""
        video = self._create_synthetic_video(duration=5)
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        import json
        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        self.assertAlmostEqual(duration, 5.0, delta=1.0,
                                msg="Duration should be ~5 seconds")
        streams = data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        self.assertGreaterEqual(len(video_streams), 1,
                                 msg="Should have at least one video stream")

    def test_ffprobe_detects_codec(self):
        """ffprobe detects the correct video codec."""
        video = self._create_synthetic_video(duration=2, codec="libx264")
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_streams", str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        import json
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "video":
                self.assertIn("h264", s.get("codec_name", "").lower())
                break
        else:
            self.fail("No video stream found")

    def test_ffprobe_detects_resolution(self):
        """ffprobe detects the correct resolution."""
        video = self._create_synthetic_video(duration=2, size="320x240")
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_streams", str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        import json
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "video":
                self.assertEqual(s.get("width"), 320)
                self.assertEqual(s.get("height"), 240)
                break
        else:
            self.fail("No video stream found")

    def test_ffprobe_detects_audio(self):
        """ffprobe detects audio stream in synthetic video."""
        video = self._create_synthetic_video(duration=2)
        cmd = [
            self.ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_streams", str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        import json
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        self.assertGreaterEqual(len(audio_streams), 1,
                                 msg="Should have at least one audio stream")

    def test_thumbnail_can_be_extracted(self):
        """A thumbnail frame can be extracted from synthetic video."""
        video = self._create_synthetic_video(duration=5)
        thumb = self.root / "thumb.png"
        cmd = [
            self.ffmpeg, "-y", "-i", str(video),
            "-vframes", "1", "-vf", "scale=64:64",
            str(thumb),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(thumb.exists())
        self.assertGreater(thumb.stat().st_size, 50)


if __name__ == "__main__":
    unittest.main()
