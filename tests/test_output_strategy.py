"""Output strategy tests for workers.output_strategy (pure file/move logic)."""

import errno
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workers.output_strategy import (
    move_with_retries,
    save_non_overwrite_output,
    save_overwrite_output,
)


class MoveWithRetriesTests(unittest.TestCase):
    """Tests for the shared move_with_retries() helper."""

    def test_non_overwrite_success_moves_file(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "source.tmp"
            destination = root_path / "movie.mkv"
            source.write_bytes(b"content")

            self.assertTrue(move_with_retries(str(source), str(destination)))

            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), b"content")

    def test_non_overwrite_fails_after_three_attempts_and_keeps_destination(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "source.tmp"
            destination = root_path / "movie.mkv"
            source.write_bytes(b"new content")
            destination.write_bytes(b"existing output")

            with (
                patch("shutil.move", side_effect=OSError("move failed")),
                patch("time.sleep") as mock_sleep,
            ):
                result = move_with_retries(
                    str(source), str(destination), replace_existing=False
                )

            self.assertFalse(result)
            self.assertEqual(mock_sleep.call_count, 2)  # 3 attempts -> 2 sleeps
            # Destination must not be deleted by the failed strategy.
            self.assertEqual(destination.read_bytes(), b"existing output")

    def test_non_overwrite_retries_then_succeeds(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "source.tmp"
            destination = root_path / "movie.mkv"
            source.write_bytes(b"content")

            real_move = shutil.move
            calls = {"n": 0}

            def flaky_move(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise OSError("transient")
                return real_move(*args, **kwargs)

            with patch("shutil.move", side_effect=flaky_move), patch("time.sleep"):
                result = move_with_retries(str(source), str(destination))

            self.assertTrue(result)
            self.assertEqual(calls["n"], 2)
            self.assertEqual(destination.read_bytes(), b"content")

    def test_replace_existing_same_drive_uses_os_replace(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "source.tmp"
            destination = root_path / "movie.mkv"
            source.write_bytes(b"new")
            destination.write_bytes(b"old")

            real_replace = os.replace
            with patch("os.replace") as mock_replace:
                mock_replace.side_effect = real_replace
                result = move_with_retries(
                    str(source),
                    str(destination),
                    replace_existing=True,
                    retries=1,
                )

            self.assertTrue(result)
            mock_replace.assert_called_once_with(str(source), str(destination))
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), b"new")

    def test_cross_device_exdev_falls_back_to_shutil_move(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "source.tmp"
            destination = root_path / "movie.mkv"
            source.write_bytes(b"content")

            real_move = shutil.move

            with (
                patch("os.replace", side_effect=OSError(errno.EXDEV, "cross-device")),
                patch("shutil.move") as mock_move,
            ):
                mock_move.side_effect = real_move
                result = move_with_retries(
                    str(source),
                    str(destination),
                    replace_existing=True,
                    retries=1,
                )

            self.assertTrue(result)
            mock_move.assert_called_once_with(str(source), str(destination))
            self.assertEqual(destination.read_bytes(), b"content")


class SaveNonOverwriteTests(unittest.TestCase):
    """Tests for save_non_overwrite_output()."""

    def test_success_moves_temp_to_final(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "movie.mkv"
            temp_output.write_bytes(b"encoded")

            save_non_overwrite_output(str(temp_output), str(final_output))

            self.assertFalse(temp_output.exists())
            self.assertEqual(final_output.read_bytes(), b"encoded")

    def test_failure_raises_oserror_and_keeps_destination(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "movie.mkv"
            temp_output.write_bytes(b"new")
            final_output.write_bytes(b"existing output")

            with (
                patch("shutil.move", side_effect=OSError("move failed")),
                patch("time.sleep"),
                self.assertRaises(OSError) as caught,
            ):
                save_non_overwrite_output(str(temp_output), str(final_output))

            # The strategy must not leak a user-facing English message.
            self.assertEqual(str(caught.exception), "")

            # Destination must not be removed by a failed non-overwrite save.
            self.assertEqual(final_output.read_bytes(), b"existing output")


class SaveOverwriteTests(unittest.TestCase):
    """Tests for save_overwrite_output()."""

    def test_same_path_success_replaces_source_and_removes_bak(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "movie.mp4"
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "movie.mp4"  # same as source
            source.write_bytes(b"original source")
            temp_output.write_bytes(b"new encoded")

            save_overwrite_output(str(source), str(temp_output), str(final_output))

            self.assertFalse(temp_output.exists())
            self.assertEqual(source.read_bytes(), b"new encoded")
            self.assertFalse(Path(str(source) + ".bak").exists())

    def test_same_path_failure_restores_source_from_bak(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "movie.mp4"
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "movie.mp4"
            source.write_bytes(b"original source")
            temp_output.write_bytes(b"new encoded")

            # Force the temp->final move to fail after the source has been
            # backed up, so the strategy must restore the .bak over the source.
            with (
                patch("workers.output_strategy.move_with_retries", return_value=False),
                patch("time.sleep"),
                self.assertRaises(OSError) as caught,
            ):
                save_overwrite_output(str(source), str(temp_output), str(final_output))

            # The strategy must not leak a user-facing English message.
            self.assertEqual(str(caught.exception), "")

            # Source must be restored from the backup after a failed overwrite.
            self.assertEqual(source.read_bytes(), b"original source")
            self.assertFalse(Path(str(source) + ".bak").exists())

    def test_same_path_success_uses_three_retries(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "movie.mp4"
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "movie.mp4"
            source.write_bytes(b"original source")
            temp_output.write_bytes(b"new encoded")

            real_replace = os.replace
            calls = {"n": 0}

            def flaky_replace(src, dst):
                # 仅让 temp->final 的移动瞬时失败；备份改名直接透传
                if "temp.mkv" in str(src):
                    calls["n"] += 1
                    if calls["n"] < 3:
                        raise OSError("transient")
                return real_replace(src, dst)

            with (
                patch("os.replace", side_effect=flaky_replace),
                patch("time.sleep"),
            ):
                save_overwrite_output(str(source), str(temp_output), str(final_output))

            # The same-path branch retries os.replace up to 3 times before success.
            self.assertEqual(calls["n"], 3)
            self.assertEqual(source.read_bytes(), b"new encoded")
            self.assertFalse(Path(str(source) + ".bak").exists())

    def test_different_path_success_replaces_target_and_removes_source(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "movie.mp4"
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "output.mkv"  # different from source
            source.write_bytes(b"original source")
            temp_output.write_bytes(b"new encoded")

            save_overwrite_output(str(source), str(temp_output), str(final_output))

            self.assertFalse(temp_output.exists())
            self.assertFalse(source.exists())
            self.assertEqual(final_output.read_bytes(), b"new encoded")

    def test_different_path_failure_keeps_source(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            source = root_path / "movie.mp4"
            temp_output = root_path / "output.temp.mkv"
            final_output = root_path / "output.mkv"
            source.write_bytes(b"original source")
            temp_output.write_bytes(b"new encoded")

            with (
                patch("workers.output_strategy.move_with_retries", return_value=False),
                patch("time.sleep"),
                self.assertRaises(OSError) as caught,
            ):
                save_overwrite_output(str(source), str(temp_output), str(final_output))

            # The strategy must not leak a user-facing English message.
            self.assertEqual(str(caught.exception), "")

            # The source must not be removed when the overwrite fails.
            self.assertEqual(source.read_bytes(), b"original source")


if __name__ == "__main__":
    unittest.main()
