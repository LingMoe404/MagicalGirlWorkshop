import unittest

from workers.system_metrics import WindowsResourceSampler


def sequence_reader(*values):
    remaining = iter(values)
    return lambda: next(remaining)


class WindowsResourceSamplerTests(unittest.TestCase):
    def test_cpu_usage_uses_idle_and_total_deltas(self):
        sampler = WindowsResourceSampler(
            times_reader=sequence_reader(
                (100, 1000, 500),
                (150, 1100, 600),
            ),
            memory_reader=lambda: (
                8 * 1024**3,
                16 * 1024**3,
            ),
        )

        first = sampler.sample()
        second = sampler.sample()

        self.assertEqual(first.cpu_percent, 0.0)
        self.assertEqual(second.cpu_percent, 75.0)
        self.assertEqual(second.available_memory, 8 * 1024**3)
        self.assertEqual(second.total_memory, 16 * 1024**3)

    def test_zero_total_delta_keeps_cpu_at_zero(self):
        sampler = WindowsResourceSampler(
            times_reader=sequence_reader(
                (100, 1000, 500),
                (100, 1000, 500),
            ),
            memory_reader=lambda: (1, 2),
        )

        sampler.sample()
        result = sampler.sample()

        self.assertEqual(result.cpu_percent, 0.0)

    def test_invalid_delta_is_clamped_to_valid_percentage(self):
        sampler = WindowsResourceSampler(
            times_reader=sequence_reader(
                (100, 1000, 500),
                (500, 1100, 600),
            ),
            memory_reader=lambda: (1, 2),
        )

        sampler.sample()
        result = sampler.sample()

        self.assertEqual(result.cpu_percent, 0.0)


if __name__ == "__main__":
    unittest.main()
