import inspect
import unittest

from workers.encoder import EncoderWorker
from workers.transcode_paths import TaskPaths


class EncoderCoordinationContractTests(unittest.TestCase):
    def test_worker_exposes_stage_speed_and_resource_signals(self):
        self.assertTrue(hasattr(EncoderWorker, "stage_signal"))
        self.assertTrue(hasattr(EncoderWorker, "encoding_speed_signal"))
        self.assertTrue(hasattr(EncoderWorker, "resource_error_signal"))

    def test_coordinated_worker_does_not_manage_system_awake(self):
        worker = EncoderWorker(
            {
                "selected_files": ["a.mp4"],
                "manage_system_awake": False,
            }
        )

        self.assertFalse(worker.manage_system_awake)

    def test_worker_accepts_precomputed_task_paths(self):
        paths = TaskPaths(
            task_dir="task",
            ab_av1_dir="task/ab-av1",
            temp_output="task/output.temp.mkv",
            final_output="out.mkv",
        )
        worker = EncoderWorker(
            {
                "selected_files": ["a.mp4"],
                "task_paths": paths,
            }
        )

        self.assertEqual(worker.task_paths, paths)

    def test_run_uses_isolated_paths_and_does_not_scan_cache_root(self):
        run_src = inspect.getsource(EncoderWorker.run)

        self.assertIn("self.task_paths", run_src)
        self.assertIn(
            "self.stage_signal.emit", inspect.getsource(EncoderWorker._execute_ffmpeg)
        )
        self.assertIn(
            "self.encoding_speed_signal.emit",
            inspect.getsource(EncoderWorker._execute_ffmpeg),
        )
        self.assertNotIn("os.listdir(cache_dir)", run_src)


if __name__ == "__main__":
    unittest.main()
