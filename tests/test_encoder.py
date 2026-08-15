"""EncoderWorker tests using BytesIO-based subprocess mocking."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workers.encoder import EncoderWorker
from workers.transcode_paths import TaskPaths


class FakeProcess:
    """Simulates a subprocess.Popen.
    Supports text mode via the `text` flag (like real subprocess.Popen)."""

    def __init__(self, stdout_lines, returncode=0, text=False):
        self._lines = list(stdout_lines)
        self._index = 0
        self._returncode = returncode
        self._text = text
        self.pid = 12345
        self.stdout = self  # stdout is self; readline() handles text mode

    def readline(self):
        if self._index < len(self._lines):
            line = self._lines[self._index]
            self._index += 1
            if self._text:
                return line if isinstance(line, str) else line.decode("utf-8")
            return line.encode("utf-8") if isinstance(line, str) else line
        return "" if self._text else b""

    def poll(self):
        if self._index >= len(self._lines):
            return self._returncode
        return None

    @property
    def returncode(self):
        return self._returncode

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def communicate(self, input=None, timeout=None):
        data = (
            "".join(self._lines)
            if self._text
            else "".join(
                l.encode("utf-8")
                if isinstance(l, str)
                else l.decode("utf-8", errors="replace")
                for l in self._lines
            ).encode("utf-8")
        )
        return data, b""

    def kill(self):
        pass

    def wait(self, timeout=None):
        return self._returncode


class FakeSignal:
    def __init__(self):
        self._callbacks = []
        self.emissions = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        self.emissions.append(args)
        for cb in tuple(self._callbacks):
            cb(*args)


def make_ab_av1_process(crf_tuples):
    lines = []
    for crf, vmaf, pct in crf_tuples:
        lines.append(
            f"crf {crf} VMAF {vmaf} predicted video stream size "
            f"1.00 GiB ({pct}%) taking 10 minutes"
        )
    if crf_tuples:
        lines.append(f"crf {crf_tuples[-1][0]} successful")
    return FakeProcess(lines, returncode=0)


def make_ffmpeg_process(returncode=0, text=True):
    return FakeProcess(
        ["frame=  100 fps=30.0 speed=2.5x"], returncode=returncode, text=text
    )


class PopenReplacer:
    """Replaces subprocess.Popen with controlled FakeProcess instances."""

    def __init__(self):
        self._original = None
        self._processes = []
        self._call_count = 0

    def add_process(self, process):
        self._processes.append(process)
        return self

    def _handler(self, *args, **kwargs):
        idx = self._call_count
        self._call_count += 1
        if idx < len(self._processes):
            proc = self._processes[idx]
            # Set text mode on the FakeProcess based on kwargs
            if isinstance(proc, FakeProcess):
                proc._text = bool(kwargs.get("text"))
                proc.stdout = proc
            return proc
        return self._original(*args, **kwargs)

    def __enter__(self):
        import subprocess as sp_mod

        self._original = sp_mod.Popen
        sp_mod.Popen = self._handler
        return self

    def __exit__(self, *args):
        import subprocess as sp_mod

        sp_mod.Popen = self._original


class EncoderWorkerTests(unittest.TestCase):
    """Tests for EncoderWorker.run() with mocked subprocesses."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_dir = self.root / "source"
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.test_file = str(self.source_dir / "test_video.mp4")
        Path(self.test_file).write_bytes(b"fake video content")

        self.task_dir = self.root / "task-0"
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.ab_av1_dir = self.task_dir / "ab-av1"
        self.ab_av1_dir.mkdir(parents=True, exist_ok=True)
        self.task_paths = TaskPaths(
            task_dir=str(self.task_dir),
            ab_av1_dir=str(self.ab_av1_dir),
            temp_output=str(self.task_dir / "output.temp.mkv"),
            final_output=str(self.root / "output.mkv"),
        )
        # Pre-create temp output for output handling
        Path(self.task_paths.temp_output).write_bytes(b"x" * 2048)

        self.base_config = {
            "selected_files": [self.test_file],
            "encoder": "Intel QSV",
            "export_dir": str(self.root / "export"),
            "cache_dir": str(self.root / "cache"),
            "save_mode": "Save As",
            "preset": "4",
            "vmaf": "93.0",
            "audio_bitrate": "96k",
            "loudnorm": "",
            "loudnorm_mode": "Disable",
            "metadata": {
                self.test_file: {
                    "codec": "h264",
                    "duration": 5.0,
                    "channels": 2,
                    "pix_fmt": "yuv420p",
                    "color_space": "bt709",
                    "color_transfer": "bt709",
                    "color_primaries": "bt709",
                    "has_dovi": False,
                }
            },
            "task_paths": self.task_paths,
            "manage_system_awake": False,
            "gpu_cooling_time": 0,
            "hw_decoding": True,
            "nv_aq": True,
            "color_mode": "Auto",
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_worker(self, **overrides):
        config = {**self.base_config, **overrides}
        w = EncoderWorker(config)
        for attr in (
            "log_signal",
            "progress_total_signal",
            "progress_current_signal",
            "file_progress_signal",
            "file_stats_signal",
            "file_status_signal",
            "finished_signal",
            "ask_error_decision",
            "stage_signal",
            "encoding_speed_signal",
            "resource_error_signal",
        ):
            setattr(w, attr, FakeSignal())
        w.ask_error_decision.connect(lambda title, content: w.receive_decision("skip"))
        return w

    def run_worker(self, worker, *processes):
        # Create temp output file so encoder's output handling succeeds
        if worker.task_paths is not None:
            Path(worker.task_paths.temp_output).write_bytes(b"x" * 2048)
        # Patch os.path.exists/getsize so temp file is always "valid"
        orig_exists = os.path.exists
        orig_getsize = os.path.getsize

        def fake_exists(path):
            if "temp" in str(path) or "output.temp" in str(path):
                return True
            return orig_exists(path)

        def fake_getsize(path):
            if "temp" in str(path) or "output.temp" in str(path):
                return 2048
            return orig_getsize(path)

        with PopenReplacer() as replacer:
            for p in processes:
                replacer.add_process(p)
            with (
                patch("time.sleep"),
                patch("shutil.move"),
                patch("os.path.exists", side_effect=fake_exists),
                patch("os.path.getsize", side_effect=fake_getsize),
            ):
                worker.run()

    # ---- VMAF probe ----

    def test_probe_success_qsv(self):
        worker = self.make_worker()
        self.run_worker(
            worker,
            make_ab_av1_process([(30, 93.69, 84)]),
            make_ffmpeg_process(),
        )
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_probe_success_nvenc(self):
        worker = self.make_worker(encoder="NVIDIA NVENC")
        self.run_worker(
            worker,
            make_ab_av1_process([(30, 93.69, 84)]),
            make_ffmpeg_process(),
        )
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_probe_skips_hardware_for_amf(self):
        worker = self.make_worker(encoder="AMD AMF")
        self.run_worker(
            worker,
            make_ab_av1_process([(30, 93.69, 84)]),
            make_ffmpeg_process(),
        )
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_probe_fallback_to_next_strategy(self):
        fail_proc = FakeProcess(["Error: encoder not available"], returncode=1)
        worker = self.make_worker()
        self.run_worker(
            worker,
            fail_proc,
            make_ab_av1_process([(28, 93.50, 82)]),
            make_ffmpeg_process(),
        )
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_quality_fallback(self):
        lines = [
            "crf 23 VMAF 93.69 predicted video stream size 1.00 GiB (84%) taking 10 minutes",
            "crf 24 VMAF 92.76 predicted video stream size 0.90 GiB (79%) taking 9 minutes",
            "Error: Failed to find a suitable crf",
        ]
        worker = self.make_worker(vmaf="93.0")
        self.run_worker(
            worker,
            FakeProcess(lines, returncode=1),
            make_ffmpeg_process(),
        )
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_probe_all_strategies_fail(self):
        fail_proc = FakeProcess(["Error: encoder not available"], returncode=1)
        worker = self.make_worker()
        self.run_worker(worker, fail_proc, fail_proc, fail_proc)
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "error"),
        )

    # ---- Encoding ----

    def test_encode_success_save_as(self):
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(make_ffmpeg_process())
            with patch("time.sleep"), patch("shutil.move") as mock_move:
                worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )
        mock_move.assert_called()

    def test_encode_success_overwrite(self):
        worker = self.make_worker(save_mode="Overwrite")
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(make_ffmpeg_process())
            with patch("time.sleep"), patch("shutil.move"), patch("os.replace"):
                worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_encode_success_remain(self):
        worker = self.make_worker(save_mode="Remain")
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(make_ffmpeg_process())
            with patch("time.sleep"), patch("shutil.move"):
                worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    # ---- Skip AV1 ----

    def test_skip_already_av1(self):
        worker = self.make_worker(
            metadata={self.test_file: {"codec": "av1", "duration": 5.0}}
        )
        worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    # ---- Error retry ----

    def test_retry_hardware_decode_failure(self):
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(
                FakeProcess(
                    ["Device setup failed for decoder on input stream #0:0"],
                    returncode=1,
                )
            )
            replacer.add_process(make_ffmpeg_process())
            with (
                patch("time.sleep"),
                patch("shutil.move"),
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=2048),
            ):
                worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_retry_subtitle_error(self):
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(
                FakeProcess(
                    ["Error while decoding subtitle stream #0:2"],
                    returncode=1,
                )
            )
            replacer.add_process(make_ffmpeg_process())
            with (
                patch("time.sleep"),
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=2048),
            ):
                worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "success"),
        )

    def test_retry_exhausted(self):
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(
                FakeProcess(
                    ["Device setup failed for decoder on input stream #0:0"],
                    returncode=1,
                )
            )
            replacer.add_process(
                FakeProcess(
                    ["Error while decoding subtitle stream #0:2"],
                    returncode=1,
                )
            )
            replacer.add_process(
                FakeProcess(
                    ["Error while decoding subtitle stream #0:2"],
                    returncode=1,
                )
            )
            with patch("time.sleep"):
                worker.run()
        self.assertEqual(
            worker.file_status_signal.emissions[-1],
            (self.test_file, "error"),
        )

    def test_resource_error_signal_on_oom(self):
        worker = self.make_worker()
        oom_proc = FakeProcess(
            ["OpenEncodeSessionEx failed: out of memory (10)"],
            returncode=1,
        )
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(oom_proc)
            replacer.add_process(oom_proc)
            replacer.add_process(oom_proc)
            with (
                patch("time.sleep"),
                patch("os.path.exists", return_value=True),
                patch("os.path.getsize", return_value=2048),
            ):
                worker.run()
        self.assertGreaterEqual(len(worker.resource_error_signal.emissions), 1)

    def test_ab_av1_resource_error(self):
        fail_proc = FakeProcess(
            ["OpenEncodeSessionEx failed: out of memory (10)"],
            returncode=1,
        )
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(fail_proc)
            replacer.add_process(fail_proc)
            replacer.add_process(fail_proc)
            with patch("time.sleep"):
                worker.run()
        self.assertGreaterEqual(len(worker.resource_error_signal.emissions), 1)

    # ---- Signal order ----

    def test_signal_emission_order(self):
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(make_ffmpeg_process())
            with patch("time.sleep"), patch("shutil.move"):
                worker.run()
        status_values = [e[1] for e in worker.file_status_signal.emissions]
        self.assertEqual(status_values[0], "processing")
        self.assertEqual(status_values[-1], "success")
        stage_values = [e[1] for e in worker.stage_signal.emissions]
        self.assertIn("probing", stage_values)
        self.assertIn("encoding", stage_values)
        self.assertGreaterEqual(len(worker.finished_signal.emissions), 1)

    # ---- Multi-file ----

    def test_multiple_files_sequentially(self):
        f2 = str(self.source_dir / "test_video2.mp4")
        Path(f2).write_bytes(b"fake video 2")
        worker = self.make_worker(
            selected_files=[self.test_file, f2],
            metadata={
                self.test_file: {"codec": "h264", "duration": 5.0, "channels": 2},
                f2: {"codec": "h264", "duration": 5.0, "channels": 2},
            },
            task_paths=None,
        )
        # Create temp files in cache dir for non-task-paths mode
        cache_dir = Path(self.root / "cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        # Patch time.time so temp file names are predictable
        with patch("time.time", return_value=1234567890):
            for name in ["test_video", "test_video2"]:
                (cache_dir / f"{name}_1234567890.temp.mkv").write_bytes(b"x" * 2048)
            with PopenReplacer() as replacer:
                # Fresh processes for each file
                replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
                replacer.add_process(make_ffmpeg_process())
                replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
                replacer.add_process(make_ffmpeg_process())
                with patch("time.sleep"), patch("shutil.move"):
                    worker.run()
        success_count = sum(
            1 for e in worker.file_status_signal.emissions if e[1] == "success"
        )
        self.assertEqual(success_count, 2)

    # ---- Cleanup ----

    def test_cleanup_task_dir_on_success(self):
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(make_ab_av1_process([(30, 93.69, 84)]))
            replacer.add_process(make_ffmpeg_process())
            with (
                patch("time.sleep"),
                patch("shutil.move"),
                patch("shutil.rmtree") as mock_rmtree,
            ):
                worker.run()
        mock_rmtree.assert_called_once_with(
            self.task_paths.task_dir, ignore_errors=True
        )

    def test_cleanup_task_dir_on_error(self):
        fail_proc = FakeProcess(["Error: encoder not available"], returncode=1)
        worker = self.make_worker()
        with PopenReplacer() as replacer:
            replacer.add_process(fail_proc)
            replacer.add_process(fail_proc)
            replacer.add_process(fail_proc)
            with patch("time.sleep"), patch("shutil.rmtree") as mock_rmtree:
                worker.run()
        mock_rmtree.assert_called_once_with(
            self.task_paths.task_dir, ignore_errors=True
        )


if __name__ == "__main__":
    unittest.main()
