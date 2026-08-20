import subprocess
import unittest

from workers.dependency import _communicate_with_timeout


class TimeoutProcess:
    def __init__(self):
        self.killed = False
        self.communicate_calls = []

    def communicate(self, timeout=None):
        self.communicate_calls.append(timeout)
        if timeout is not None:
            raise subprocess.TimeoutExpired("ffmpeg", timeout)
        return b"", b"terminated"

    def kill(self):
        self.killed = True


class DependencyHelperTests(unittest.TestCase):
    def test_timeout_kills_and_reaps_process(self):
        process = TimeoutProcess()

        with self.assertRaises(subprocess.TimeoutExpired):
            _communicate_with_timeout(process, timeout=5)

        self.assertTrue(process.killed)
        self.assertEqual(process.communicate_calls, [5, None])


if __name__ == "__main__":
    unittest.main()
