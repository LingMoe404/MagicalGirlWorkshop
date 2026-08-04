# -*- coding: utf-8 -*-
"""EncoderWorker structural tests."""

import inspect
import unittest
from workers.encoder import EncoderWorker
from workers.ffmpeg_retry import (
    FailureKind, RetryDecision, RetryState,
    build_hw_decode_args, is_hardware_resource_error, next_retry_state,
)
from workers.transcode_paths import TaskPaths


class EncoderCoordinationContractTests(unittest.TestCase):
    def test_worker_exposes_signals(self):
        self.assertTrue(hasattr(EncoderWorker, "stage_signal"))
        self.assertTrue(hasattr(EncoderWorker, "encoding_speed_signal"))
        self.assertTrue(hasattr(EncoderWorker, "resource_error_signal"))

    def test_worker_accepts_config(self):
        w = EncoderWorker({"selected_files": ["a.mp4"], "manage_system_awake": False})
        self.assertFalse(w.manage_system_awake)

    def test_worker_accepts_task_paths(self):
        p = TaskPaths(task_dir="t", ab_av1_dir="t/ab", temp_output="t/o.mkv", final_output="o.mkv")
        w = EncoderWorker({"selected_files": ["a.mp4"], "task_paths": p})
        self.assertEqual(w.task_paths, p)

    def test_run_uses_isolated_paths(self):
        src = inspect.getsource(EncoderWorker.run)
        self.assertIn("self.task_paths", src)
        self.assertIn("self.stage_signal.emit", src)


class EncoderUsesRetryTests(unittest.TestCase):
    def test_uses_ab_av1_parser(self):
        src = inspect.getsource(EncoderWorker.run)
        self.assertIn("AbAv1ResultParser()", src)
        self.assertIn("parser.feed(decoded)", src)

    def test_uses_retry_policy(self):
        src = inspect.getsource(EncoderWorker.run)
        self.assertIn("for attempt in range(3):", src)
        self.assertIn("next_retry_state(retry_state, err_log)", src)

    def test_no_default_crf(self):
        src = inspect.getsource(EncoderWorker.run)
        self.assertIn("best_icq = None", src)
        self.assertNotIn("best_icq = 24", src)


class HwDecodeArgsTests(unittest.TestCase):
    def test_nvenc(self):
        self.assertEqual(build_hw_decode_args("av1_nvenc", True),
                         ["-hwaccel", "cuda", "-v", "verbose"])
    def test_disabled(self):
        self.assertEqual(build_hw_decode_args("av1_nvenc", False), ["-v", "verbose"])
    def test_qsv(self):
        self.assertEqual(build_hw_decode_args("av1_qsv", True),
                         ["-init_hw_device", "qsv=hw", "-filter_hw_device", "hw",
                          "-hwaccel", "qsv", "-v", "verbose"])
    def test_amf(self):
        self.assertEqual(build_hw_decode_args("av1_amf", True),
                         ["-hwaccel", "auto", "-v", "verbose"])


class RetryStateMachineTests(unittest.TestCase):
    def test_hw_fallback(self):
        r = next_retry_state(RetryState(True, True),
                             ["Device creation failed"])
        self.assertEqual(r, RetryDecision(RetryState(False, True), FailureKind.HARDWARE_DEVICE))
    def test_subtitle_fallback(self):
        r = next_retry_state(RetryState(True, True),
                             ["Error while decoding subtitle stream #0:2"])
        self.assertEqual(r, RetryDecision(RetryState(True, False), FailureKind.SUBTITLE))
    def test_unknown(self):
        self.assertIsNone(next_retry_state(RetryState(True, True),
                                           ["Permission denied"]))
    def test_exhausted(self):
        s = RetryState(False, False)
        self.assertIsNone(next_retry_state(s, ["Device creation failed"]))


class HwResourceErrorTests(unittest.TestCase):
    def test_oom(self):
        self.assertTrue(is_hardware_resource_error(["out of memory"]))
    def test_device_busy(self):
        self.assertTrue(is_hardware_resource_error(["MFX_ERR_DEVICE_BUSY"]))
    def test_decode_setup(self):
        self.assertFalse(is_hardware_resource_error(
            ["Device setup failed for decoder on input stream #0:0"]))


if __name__ == "__main__":
    unittest.main()
