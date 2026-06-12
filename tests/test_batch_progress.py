import unittest

from workers.batch_progress import (
    calculate_batch_progress,
    map_encode_progress,
    map_probe_progress,
)


class BatchProgressTests(unittest.TestCase):
    def test_progress_is_weighted_by_duration(self):
        result = calculate_batch_progress(
            progresses={"a": 100, "b": 50},
            durations={"a": 100, "b": 300},
            terminal_files=set(),
        )

        self.assertEqual(result, 62)

    def test_terminal_failures_count_as_finished(self):
        result = calculate_batch_progress(
            progresses={"a": 20, "b": 0},
            durations={"a": 100, "b": 100},
            terminal_files={"a", "b"},
        )

        self.assertEqual(result, 100)

    def test_unknown_duration_uses_median_known_duration(self):
        result = calculate_batch_progress(
            progresses={"a": 100, "b": 0, "c": 50},
            durations={"a": 100, "b": 300, "c": 0},
            terminal_files=set(),
        )

        self.assertEqual(result, 33)

    def test_all_unknown_durations_use_arithmetic_average(self):
        result = calculate_batch_progress(
            progresses={"a": 100, "b": 20},
            durations={"a": 0, "b": 0},
            terminal_files=set(),
        )

        self.assertEqual(result, 60)

    def test_probe_progress_stays_within_first_fifteen_percent(self):
        self.assertEqual(map_probe_progress(0, 3), 5)
        self.assertEqual(map_probe_progress(2, 3), 15)

    def test_encode_progress_maps_to_remaining_range(self):
        self.assertEqual(map_encode_progress(0), 15)
        self.assertEqual(map_encode_progress(50), 58)
        self.assertEqual(map_encode_progress(100), 100)

    def test_empty_batch_is_complete(self):
        self.assertEqual(
            calculate_batch_progress({}, {}, set()),
            100,
        )


if __name__ == "__main__":
    unittest.main()
