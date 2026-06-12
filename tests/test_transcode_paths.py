import os
import tempfile
import time
import unittest
from pathlib import Path

from config import (
    SAVE_MODE_OVERWRITE,
    SAVE_MODE_REMAIN,
    SAVE_MODE_SAVE_AS,
)
from workers.transcode_paths import (
    build_final_output,
    cleanup_stale_sessions,
    create_session_root,
    create_task_paths,
    find_output_conflicts,
)


class TranscodePathTests(unittest.TestCase):
    def test_build_final_output_for_each_save_mode(self):
        source = os.path.join("D:\\videos", "movie.mp4")

        self.assertEqual(
            build_final_output(source, SAVE_MODE_OVERWRITE, ""),
            os.path.abspath(os.path.join("D:\\videos", "movie.mkv")),
        )
        self.assertEqual(
            build_final_output(source, SAVE_MODE_REMAIN, ""),
            os.path.abspath(os.path.join("D:\\videos", "movie_opt.mkv")),
        )
        self.assertEqual(
            build_final_output(
                source,
                SAVE_MODE_SAVE_AS,
                "E:\\encoded",
            ),
            os.path.abspath(os.path.join("E:\\encoded", "movie.mkv")),
        )

    def test_same_basename_in_save_as_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            inputs = [
                root_path / "one" / "movie.mp4",
                root_path / "two" / "movie.mkv",
            ]

            conflicts = find_output_conflicts(
                inputs,
                save_mode=SAVE_MODE_SAVE_AS,
                export_dir=root_path / "out",
            )

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(len(conflicts[0].input_paths), 2)
        self.assertTrue(
            conflicts[0].output_path.lower().endswith("movie.mkv")
        )

    def test_overwrite_detects_output_crossing_another_input(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            inputs = [
                root_path / "movie.mp4",
                root_path / "movie.mkv",
            ]

            conflicts = find_output_conflicts(
                inputs,
                save_mode=SAVE_MODE_OVERWRITE,
                export_dir="",
            )

        self.assertEqual(len(conflicts), 1)
        self.assertIn(
            os.path.abspath(str(inputs[1])),
            conflicts[0].input_paths,
        )

    def test_task_paths_are_isolated_inside_session(self):
        with tempfile.TemporaryDirectory() as root:
            session_root = create_session_root(root, "batch-1")
            first = create_task_paths(
                session_root,
                "task-1",
                os.path.join(root, "one.mkv"),
            )
            second = create_task_paths(
                session_root,
                "task-2",
                os.path.join(root, "two.mkv"),
            )

            self.assertNotEqual(first.task_dir, second.task_dir)
            self.assertTrue(os.path.isdir(first.ab_av1_dir))
            self.assertTrue(os.path.isdir(second.ab_av1_dir))
            self.assertTrue(first.temp_output.endswith("output.temp.mkv"))

    def test_cleanup_removes_only_old_inactive_sessions(self):
        with tempfile.TemporaryDirectory() as root:
            active = Path(create_session_root(root, "active"))
            recent = Path(create_session_root(root, "recent"))
            old = Path(create_session_root(root, "old"))
            unrelated = Path(root) / "other-cache"
            unrelated.mkdir()
            old_time = time.time() - 7200
            os.utime(old, (old_time, old_time))

            removed = cleanup_stale_sessions(
                root,
                active_session_ids={"active"},
                min_age_seconds=3600,
                now=time.time(),
            )

            self.assertEqual(removed, (str(old),))
            self.assertTrue(active.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(unrelated.exists())
            self.assertFalse(old.exists())


if __name__ == "__main__":
    unittest.main()
