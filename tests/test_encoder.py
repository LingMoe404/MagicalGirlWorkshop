"""EncoderWorker tests using BytesIO-based subprocess mocking."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import (
    SAVE_MODE_OVERWRITE,
    SAVE_MODE_REMAIN,
    SAVE_MODE_SAVE_AS,
)
from workers.encoder import EncoderWorker
from workers.output_strategy import move_with_retries
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


class CaptureProcess(FakeProcess):
    """FakeProcess that additionally records the argv handed to subprocess.Popen."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.argv = None
        self.spawn_kwargs = {}


class PopenReplacerWithCapture(PopenReplacer):
    """PopenReplacer that snapshots the argv/kwargs for every spawned process."""

    def _handler(self, *args, **kwargs):
        proc = super()._handler(*args, **kwargs)
        if isinstance(proc, CaptureProcess):
            proc.argv = list(args[0]) if args else None
            proc.spawn_kwargs = dict(kwargs)
        return proc


def make_capture_ab_av1_process(crf_tuples):
    return CaptureProcess(
        [
            f"crf {crf} VMAF {vmaf} predicted video stream size "
            f"1.00 GiB ({pct}%) taking 10 minutes"
            for crf, vmaf, pct in crf_tuples
        ]
        + [f"crf {crf_tuples[-1][0]} successful"],
        returncode=0,
    )


def make_capture_ffmpeg_process():
    return CaptureProcess(["frame=  100 fps=30.0 speed=2.5x"], returncode=0, text=True)


class RecordingFakeSignal(FakeSignal):
    """FakeSignal that also records raw *args (including callback re-emit)."""

    def __init__(self):
        super().__init__()
        self.raw_emissions = []

    def emit(self, *args):
        self.raw_emissions.append(args)
        super().emit(*args)


def launch_worker(worker, processes, launcher=None, mocks=None):
    """Run a worker while capturing the argv of every spawned subprocess.

    Captured argv lists are returned in spawn order, with one entry per
    subprocess (per ffmpeg retry attempt, when applicable). When ``mocks`` is
    provided, the patched ``shutil.move`` mock is stored under ``mocks["move"]``.
    """
    captured = []
    with PopenReplacerWithCapture() as replacer:
        for proc in processes:
            replacer.add_process(proc)
        with (
            patch("time.sleep"),
            patch("shutil.move") as mock_move,
            patch("os.replace"),
            patch("os.path.exists", side_effect=_temp_only_exists),
            patch("os.path.getsize", side_effect=_temp_only_getsize),
        ):
            worker.run()
            for proc in replacer._processes:
                if isinstance(proc, CaptureProcess) and proc.argv is not None:
                    captured.append(proc.argv)
    if launcher is not None:
        launcher(captured)
    if mocks is not None:
        mocks["move"] = mock_move
    return captured


def _temp_only_exists(path):
    """os.path.exists that only "sees" the temp output file (plus real dirs)."""
    return ".temp.mkv" in str(path) or os.path.isdir(str(path))


def _temp_only_getsize(path):
    """os.path.getsize that returns a plausible size for the temp output file."""
    if ".temp.mkv" in str(path):
        return 2048
    return os.path.getsize(path)


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
            setattr(w, attr, RecordingFakeSignal())
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

        with PopenReplacerWithCapture() as replacer:
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

    def test_move_with_retries_falls_back_across_devices(self):
        with (
            patch(
                "workers.output_strategy.os.replace",
                side_effect=OSError(18, "cross-device"),
            ),
            patch("workers.output_strategy.shutil.move") as mock_move,
        ):
            self.assertTrue(
                move_with_retries(
                    "source.tmp",
                    "destination.mkv",
                    replace_existing=True,
                    retries=1,
                )
            )

        mock_move.assert_called_once_with("source.tmp", "destination.mkv")

        worker = self.make_worker()
        destination = Path(self.task_paths.final_output)
        destination.write_bytes(b"existing output")
        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=2048),
            patch("shutil.move", side_effect=OSError("move failed")),
            patch("time.sleep"),
        ):
            result = worker._handle_output(
                self.test_file,
                "test_video.mp4",
                self.task_paths.temp_output,
                self.task_paths.final_output,
                "Save As",
                0.0,
                0.0,
                1.0,
                True,
                [],
            )

        self.assertEqual(result, (False, 0.0))
        self.assertEqual(
            worker.file_status_signal.emissions[-1], (self.test_file, "error")
        )
        self.assertNotIn(
            (self.test_file, "success"),
            worker.file_status_signal.emissions,
        )
        self.assertEqual(destination.read_bytes(), b"existing output")

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
                patch("shutil.move"),
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


class EncoderCommandCaptureTests(unittest.TestCase):
    """Snapshot tests: capture the exact ab-av1 / ffmpeg argv produced by
    EncoderWorker for representative branches. No real binaries, GPU, or Qt
    event loop required; subprocess.Popen is replaced by CaptureProcess."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source_dir = self.root / "source"
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.test_file = str(self.source_dir / "test_video.mkv")
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

        self.base_config = {
            "selected_files": [self.test_file],
            "encoder": "Intel QSV",
            "export_dir": str(self.root / "export"),
            "cache_dir": str(self.root / "cache"),
            "save_mode": SAVE_MODE_SAVE_AS,
            "preset": "4",
            "vmaf": "93.0",
            "audio_bitrate": "96k",
            "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11",
            "loudnorm_mode": "Stereo/Mono Only",
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
            setattr(w, attr, RecordingFakeSignal())
        w.ask_error_decision.connect(lambda title, content: w.receive_decision("skip"))
        return w

    def capture(self, worker, processes, mocks=None):
        return launch_worker(worker, processes, mocks=mocks)

    def assert_is_ffmpeg_cmd(self, argv):
        self.assertTrue(argv[0].endswith("ffmpeg.exe"), f"expected ffmpeg, got {argv}")

    def assert_exe(self, argv, exe_suffix):
        self.assertTrue(
            argv[0].endswith(exe_suffix), f"expected {exe_suffix}, got {argv[0]}"
        )

    def assert_ab_av1_flags(self, argv, exp_encoder, exp_preset, exp_max_crf):
        """Assert the ab-av1 crf-search option/value pairs in order, allowing
        a wildcard (-1) for the path-ish args that vary by run."""
        opts = ["--encoder", "--pix-format", "--min-vmaf", "--preset", "--max-crf"]
        seq = [
            ("--encoder", exp_encoder),
            ("--pix-format", "yuv420p10le"),
            ("--min-vmaf", "93.0"),
            ("--preset", exp_preset),
            ("--max-crf", exp_max_crf),
        ]
        for opt in opts:
            self.assertIn(opt, argv, f"missing {opt} in ab-av1 cmd: {argv}")
        positions = [argv.index(opt) for opt in opts]
        self.assertEqual(
            positions, sorted(positions), f"ab-av1 options out of order: {argv}"
        )
        for opt, exp in seq:
            idx = argv.index(opt)
            self.assertEqual(argv[idx + 1], exp, f"{opt} value mismatch in {argv}")
        # crf-search subcommand comes immediately after the exe path
        self.assertEqual(argv[1], "crf-search", argv)
        # input file present with a value after -i
        self.assertIn("-i", argv)
        self.assertEqual(argv[argv.index("-i") + 1], os.path.abspath(self.test_file))
        # --temp-dir must point at the session ab-av1 dir when it exists
        self.assertIn("--temp-dir", argv)
        self.assertEqual(argv[argv.index("--temp-dir") + 1], str(self.ab_av1_dir))

    def assert_ffmpeg_layout(self, argv, exp_hw, exp_cv, exp_preset, exp_video_tail):
        """Assert the ffmpeg argv layout in order:
        exe, -y, -hide_banner, hw-decode block, -i <input>, -c:v <encoder>,
        <video-tail (pix/color/encoder params)>, audio args, subtitle args,
        output path. Path-ish values are validated by pattern/position rather
        than exact equality so runs are deterministic."""
        self.assert_exe(argv, "ffmpeg.exe")
        self.assertEqual(argv[1], "-y")
        self.assertEqual(argv[2], "-hide_banner")
        idx = 3
        for hw_arg in exp_hw:
            self.assertEqual(argv[idx], hw_arg, f"hw arg {hw_arg} at {idx}: {argv}")
            idx += 1
        # build_hw_decode_args always appends -v verbose to the hw block
        self.assertEqual(argv[idx], "-v")
        self.assertEqual(argv[idx + 1], "verbose")
        idx += 2
        self.assertEqual(argv[idx], "-i")
        input_idx = idx + 1
        self.assertTrue(
            argv[input_idx].endswith("test_video.mkv"),
            f"unexpected input at {input_idx}: {argv}",
        )
        idx = input_idx + 1
        self.assertEqual(argv[idx], "-c:v")
        self.assertEqual(argv[idx + 1], exp_cv)
        idx += 2
        # video-tail: expected option/value sequence (exact order)
        for vid_arg in exp_video_tail:
            self.assertEqual(
                argv[idx], vid_arg, f"video tail {vid_arg} at {idx}: {argv}"
            )
            idx += 1
        # audio block (exact order + values)
        self.assertEqual(argv[idx], "-c:a")
        self.assertEqual(argv[idx + 1], "libopus")
        self.assertEqual(argv[idx + 2], "-b:a")
        self.assertEqual(argv[idx + 3], "96k")
        self.assertEqual(argv[idx + 4], "-ar")
        self.assertEqual(argv[idx + 5], "48000")
        idx += 6
        self.assertEqual(argv[idx], "-af")
        loudnorm_val = argv[idx + 1]
        self.assertTrue(
            loudnorm_val.startswith("loudnorm=I="), f"unexpected -af value: {argv}"
        )
        idx += 2
        # subtitle block
        self.assertEqual(argv[idx], "-c:s")
        self.assertEqual(argv[idx + 1], "copy")
        idx += 2
        for map_arg in ("-map", "0:v:0", "-map", "0:a", "-map", "0:s?"):
            self.assertEqual(argv[idx], map_arg, f"map {map_arg} at {idx}: {argv}")
            idx += 1
        # trailing output path (the only remaining positional)
        self.assertEqual(idx, len(argv) - 1)
        self.assertTrue(
            argv[idx].endswith("output.temp.mkv"),
            f"unexpected output path: {argv}",
        )

    # ---- QSV / NVENC / AMF video-encoder branches ----

    def test_qsv_argv(self):
        worker = self.make_worker()
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        self.assertEqual(len(cmds), 2, cmds)
        ab_cmd, ff_cmd = cmds
        self.assert_ab_av1_flags(
            ab_cmd, exp_encoder="av1_qsv", exp_preset="4", exp_max_crf="51"
        )
        self.assert_ffmpeg_layout(
            ff_cmd,
            exp_hw=[
                "-init_hw_device",
                "qsv=hw",
                "-filter_hw_device",
                "hw",
                "-hwaccel",
                "qsv",
            ],
            exp_cv="av1_qsv",
            exp_preset="4",
            exp_video_tail=[
                "-pix_fmt",
                "p010le",
                "-global_quality:v",
                "30",
                "-preset",
                "4",
                "-look_ahead",
                "1",
            ],
        )
        self.assertEqual(
            worker.file_status_signal.emissions[-1], (self.test_file, "success")
        )

    def test_nvenc_argv(self):
        worker = self.make_worker(encoder="NVIDIA NVENC", preset="4")
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        self.assertEqual(len(cmds), 2, cmds)
        ab_cmd, ff_cmd = cmds
        self.assert_ab_av1_flags(
            ab_cmd, exp_encoder="av1_nvenc", exp_preset="p4", exp_max_crf="51"
        )
        self.assert_ffmpeg_layout(
            ff_cmd,
            exp_hw=["-hwaccel", "cuda"],
            exp_cv="av1_nvenc",
            exp_preset="p4",
            exp_video_tail=[
                "-pix_fmt",
                "p010le",
                "-cq",
                "30",
                "-preset",
                "p4",
                "-b:v",
                "0",
                "-spatial-aq",
                "1",
                "-temporal-aq",
                "1",
            ],
        )

    def test_nvenc_nv_aq_disabled(self):
        worker = self.make_worker(encoder="NVIDIA NVENC", nv_aq=False)
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        self.assertEqual(len(cmds), 2, cmds)
        ff_cmd = cmds[1]
        self.assertNotIn("-spatial-aq", ff_cmd)
        self.assertNotIn("-temporal-aq", ff_cmd)
        # Preset mapping must hold without the AQ flags
        self.assertEqual(ff_cmd[ff_cmd.index("-preset") + 1], "p4")
        self.assertEqual(ff_cmd[ff_cmd.index("-cq") + 1], "30")
        self.assertEqual(ff_cmd[ff_cmd.index("-b:v") + 1], "0")

    def test_amf_argv(self):
        worker = self.make_worker(encoder="AMD AMF", preset="4")
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        self.assertEqual(len(cmds), 2, cmds)
        ab_cmd, ff_cmd = cmds
        # AMF: hardware search strategy is skipped -> first strategy is CPU SVT-AV1
        self.assert_ab_av1_flags(
            ab_cmd, exp_encoder="libsvtav1", exp_preset="9", exp_max_crf="63"
        )
        self.assert_ffmpeg_layout(
            ff_cmd,
            exp_hw=["-hwaccel", "auto"],
            exp_cv="av1_amf",
            exp_preset="balanced",
            exp_video_tail=[
                "-pix_fmt",
                "p010le",
                "-usage",
                "transcoding",
                "-quality",
                "balanced",
                "-rc",
                "vbr_latency",
                "-qvbr_quality_level",
                "30",
                "-preanalysis",
                "true",
            ],
        )

    # ---- HDR Auto / HDR ToneMap / SDR color branches ----

    def _hdr_metadata(self):
        return {
            self.test_file: {
                "codec": "h264",
                "duration": 5.0,
                "channels": 2,
                "pix_fmt": "yuv420p10le",
                "color_space": "bt2020nc",
                "color_transfer": "smpte2084",
                "color_primaries": "bt2020",
                "has_dovi": False,
            }
        }

    def test_hdr_auto_color_args(self):
        worker = self.make_worker(
            color_mode="Auto",
            metadata=self._hdr_metadata(),
        )
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertIn("-color_primaries", ff_cmd)
        self.assertIn("-color_trc", ff_cmd)
        self.assertIn("-colorspace", ff_cmd)
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-color_primaries") + 1])
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-color_trc") + 1])
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-colorspace") + 1])

    def test_hdr_tonemap_filter_args(self):
        worker = self.make_worker(
            color_mode="ToneMap",
            metadata=self._hdr_metadata(),
        )
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertIn("-vf", ff_cmd)
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-vf") + 1])
        self.assertNotIn("-color_primaries", ff_cmd)
        self.assertNotIn("-color_trc", ff_cmd)
        self.assertNotIn("-colorspace", ff_cmd)

    def test_sdr_no_color_args(self):
        worker = self.make_worker(
            color_mode="Auto",
            metadata={
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
        )
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertNotIn("-vf", ff_cmd)
        self.assertNotIn("-color_primaries", ff_cmd)
        self.assertNotIn("-color_trc", ff_cmd)
        self.assertNotIn("-colorspace", ff_cmd)
        self.assertIn("-pix_fmt", ff_cmd)
        self.assertEqual(ff_cmd[ff_cmd.index("-pix_fmt") + 1], "p010le")

    # ---- Subtitle included / excluded ----

    def test_subtitles_included(self):
        worker = self.make_worker()
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertIn("-c:s", ff_cmd)
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-c:s") + 1])
        self.assertIn("-map", ff_cmd)
        self.assertIn("0:s?", ff_cmd)
        self.assertNotIn("-sn", ff_cmd)

    def test_subtitles_excluded(self):
        worker = self.make_worker()
        fail_proc = CaptureProcess(
            ["Error while decoding subtitle stream #0:2"], returncode=1
        )
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                fail_proc,
                make_capture_ffmpeg_process(),
            ],
        )
        # First ffmpeg attempt (subs included) fails, second (subs dropped) succeeds
        self.assertEqual(len(cmds), 3, cmds)
        self.assertIn("-c:s", cmds[1])
        self.assertNotIn("-sn", cmds[1])
        self.assertIn("-sn", cmds[2])
        self.assertNotIn("-c:s", cmds[2])
        self.assertIn("0:v:0", cmds[2])
        self.assertIn("0:a", cmds[2])
        self.assertNotIn("0:s?", cmds[2])

    # ---- Audio: loudnorm + channel layout ----

    def test_audio_loudnorm_and_channel_layout(self):
        worker = self.make_worker(
            loudnorm="loudnorm=I=-16:TP=-1.5:LRA=11",
            loudnorm_mode="Always",
            metadata={
                self.test_file: {
                    "codec": "h264",
                    "duration": 5.0,
                    "channels": 6,
                    "pix_fmt": "yuv420p",
                    "color_space": "bt709",
                    "color_transfer": "bt709",
                    "color_primaries": "bt709",
                    "has_dovi": False,
                }
            },
        )
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertEqual(ff_cmd[ff_cmd.index("-c:a") + 1], "libopus")
        self.assertEqual(ff_cmd[ff_cmd.index("-b:a") + 1], "96k")
        self.assertEqual(ff_cmd[ff_cmd.index("-ar") + 1], "48000")
        self.assertIn("-af", ff_cmd)
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-af") + 1])

    def test_audio_no_filters_when_disabled(self):
        worker = self.make_worker(loudnorm_mode="Disable")
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertIn("-c:a", ff_cmd)
        self.assertNotIn("-af", ff_cmd)

    def test_audio_8ch_loudnorm(self):
        worker = self.make_worker(
            loudnorm="loudnorm=I=-16:TP=-1.5:LRA=11",
            loudnorm_mode="Always",
            metadata={
                self.test_file: {
                    "codec": "h264",
                    "duration": 5.0,
                    "channels": 8,
                    "pix_fmt": "yuv420p",
                    "color_space": "bt709",
                    "color_transfer": "bt709",
                    "color_primaries": "bt709",
                    "has_dovi": False,
                }
            },
        )
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        ff_cmd = cmds[1]
        self.assertIn("-af", ff_cmd)
        self.assertIsNotNone(ff_cmd[ff_cmd.index("-af") + 1])

    # ---- Save-mode related mapping smoke tests ----

    def test_save_mode_remain_smoke(self):
        worker = self.make_worker(save_mode=SAVE_MODE_REMAIN)
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        self.assertEqual(len(cmds), 2, cmds)
        # Must reach success status (probe + encode both completed)
        self.assertEqual(
            worker.file_status_signal.emissions[-1], (self.test_file, "success")
        )
        # Coordinated path: destination always comes from task_paths.final_output
        self.assertEqual(
            worker.task_paths.final_output,
            os.path.abspath(str(self.root / "output.mkv")),
        )

    def test_save_mode_overwrite_smoke(self):
        worker = self.make_worker(save_mode=SAVE_MODE_OVERWRITE)
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
        )
        self.assertEqual(len(cmds), 2, cmds)
        # Must reach success status
        self.assertEqual(
            worker.file_status_signal.emissions[-1], (self.test_file, "success")
        )
        self.assertEqual(
            worker.task_paths.final_output,
            os.path.abspath(str(self.root / "output.mkv")),
        )

    def test_save_as_standalone_outputs_to_export_dir(self):
        """Standalone path (task_paths=None): save mode drives the destination."""
        export_dir = str(self.root / "export")
        worker = self.make_worker(
            save_mode=SAVE_MODE_SAVE_AS,
            task_paths=None,
            export_dir=export_dir,
        )
        mocks = {}
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
            mocks=mocks,
        )
        self.assertEqual(len(cmds), 2, cmds)
        self.assertEqual(
            worker.file_status_signal.emissions[-1], (self.test_file, "success")
        )
        # Save As standalone: shutil.move receives the export-dir output path
        # (wrapped via to_long_path on Windows -> strip the \\?\ prefix)
        expected_dest = os.path.abspath(str(self.root / "export" / "test_video.mkv"))
        actual_dest = mocks["move"].call_args.args[1].removeprefix("\\\\?\\")
        self.assertEqual(
            os.path.abspath(os.path.normpath(actual_dest)),
            os.path.normpath(expected_dest),
        )

    def test_save_mode_remain_standalone_outputs_opt_suffix(self):
        """Standalone path (task_paths=None): Remain maps to <name>_opt.mkv."""
        worker = self.make_worker(
            save_mode=SAVE_MODE_REMAIN,
            task_paths=None,
        )
        mocks = {}
        cmds = self.capture(
            worker,
            [
                make_capture_ab_av1_process([(30, 93.69, 84)]),
                make_capture_ffmpeg_process(),
            ],
            mocks=mocks,
        )
        self.assertEqual(len(cmds), 2, cmds)
        self.assertEqual(
            worker.file_status_signal.emissions[-1], (self.test_file, "success")
        )
        expected_dest = os.path.abspath(
            str(self.root / "source" / "test_video_opt.mkv")
        )
        actual_dest = mocks["move"].call_args.args[1].removeprefix("\\\\?\\")
        self.assertEqual(
            os.path.abspath(os.path.normpath(actual_dest)),
            os.path.normpath(expected_dest),
        )


if __name__ == "__main__":
    unittest.main()
