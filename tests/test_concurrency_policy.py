import unittest

from workers.concurrency_policy import (
    ConcurrencyMode,
    DynamicConcurrencyPolicy,
    ResourceSnapshot,
)


GIB = 1024**3
HEALTHY = ResourceSnapshot(
    cpu_percent=35.0,
    available_memory=8 * GIB,
    total_memory=16 * GIB,
)


def auto_policy():
    return DynamicConcurrencyPolicy(
        mode=ConcurrencyMode.AUTO,
        warmup_seconds=10,
        window_seconds=10,
        cooldown_seconds=10,
    )


def enter_two_way_trial():
    policy = auto_policy()
    policy.observe(0, {"a": 1.0}, HEALTHY)
    decision = policy.observe(20, {"a": 1.0}, HEALTHY)
    if decision.target_concurrency != 2:
        raise AssertionError("policy did not enter the two-way trial")
    return policy


def accept_two_way_trial():
    policy = enter_two_way_trial()
    policy.observe(30, {"a": 0.65, "b": 0.65}, HEALTHY)
    decision = policy.observe(
        50,
        {"a": 0.65, "b": 0.65},
        HEALTHY,
    )
    if not decision.accepted:
        raise AssertionError("policy did not accept the two-way trial")
    return policy


class DynamicConcurrencyPolicyTests(unittest.TestCase):
    def test_manual_mode_uses_requested_limit(self):
        policy = DynamicConcurrencyPolicy(
            mode=ConcurrencyMode.MANUAL,
            manual_limit=4,
        )

        self.assertEqual(policy.target_concurrency, 4)

    def test_manual_limit_is_clamped_to_supported_range(self):
        low = DynamicConcurrencyPolicy(
            mode=ConcurrencyMode.MANUAL,
            manual_limit=0,
        )
        high = DynamicConcurrencyPolicy(
            mode=ConcurrencyMode.MANUAL,
            manual_limit=9,
        )

        self.assertEqual(low.target_concurrency, 1)
        self.assertEqual(high.target_concurrency, 4)

    def test_auto_mode_starts_at_one_and_caps_at_three(self):
        policy = DynamicConcurrencyPolicy(mode=ConcurrencyMode.AUTO)

        self.assertEqual(policy.target_concurrency, 1)
        self.assertEqual(policy.auto_max, 3)

    def test_auto_mode_trials_next_level_after_stable_baseline(self):
        policy = auto_policy()

        policy.observe(0, {"a": 1.0}, HEALTHY)
        decision = policy.observe(20, {"a": 1.0}, HEALTHY)

        self.assertEqual(decision.target_concurrency, 2)
        self.assertTrue(decision.changed)
        self.assertIn("trial", decision.reason)

    def test_trial_is_accepted_when_throughput_improves_15_percent(self):
        policy = enter_two_way_trial()

        policy.observe(30, {"a": 0.65, "b": 0.65}, HEALTHY)
        decision = policy.observe(
            50,
            {"a": 0.65, "b": 0.65},
            HEALTHY,
        )

        self.assertEqual(decision.target_concurrency, 2)
        self.assertTrue(decision.accepted)
        self.assertFalse(decision.changed)
        self.assertAlmostEqual(policy.baseline_for(2), 1.3)

    def test_trial_is_rejected_and_blacklisted_when_gain_is_too_small(self):
        policy = enter_two_way_trial()

        policy.observe(30, {"a": 0.52, "b": 0.52}, HEALTHY)
        decision = policy.observe(
            50,
            {"a": 0.52, "b": 0.52},
            HEALTHY,
        )

        self.assertEqual(decision.target_concurrency, 1)
        self.assertTrue(decision.changed)
        self.assertIn(2, policy.blacklisted_levels)

    def test_hardware_resource_error_reduces_target_immediately(self):
        policy = accept_two_way_trial()

        decision = policy.observe(
            60,
            {"a": 0.6, "b": 0.6},
            HEALTHY,
            hardware_resource_error=True,
        )

        self.assertEqual(decision.target_concurrency, 1)
        self.assertTrue(decision.changed)
        self.assertIn("resource", decision.reason)

    def test_manual_mode_only_reduces_for_hardware_protection(self):
        policy = DynamicConcurrencyPolicy(
            mode=ConcurrencyMode.MANUAL,
            manual_limit=4,
        )

        unchanged = policy.observe(
            100,
            {"a": 0.1, "b": 0.1, "c": 0.1, "d": 0.1},
            ResourceSnapshot(99.0, 8 * GIB, 16 * GIB),
        )
        reduced = policy.observe(
            101,
            {},
            HEALTHY,
            hardware_resource_error=True,
        )

        self.assertEqual(unchanged.target_concurrency, 4)
        self.assertEqual(reduced.target_concurrency, 3)

    def test_low_memory_reduces_target(self):
        policy = accept_two_way_trial()
        low_memory = ResourceSnapshot(
            cpu_percent=50.0,
            available_memory=512 * 1024**2,
            total_memory=16 * GIB,
        )

        decision = policy.observe(
            60,
            {"a": 0.6, "b": 0.6},
            low_memory,
        )

        self.assertEqual(decision.target_concurrency, 1)
        self.assertIn("memory", decision.reason)

    def test_paused_observation_does_not_advance_window(self):
        policy = auto_policy()
        policy.observe(0, {"a": 1.0}, HEALTHY)

        policy.observe(100, {"a": 1.0}, HEALTHY, paused=True)
        decision = policy.observe(101, {"a": 1.0}, HEALTHY)

        self.assertEqual(decision.target_concurrency, 1)
        self.assertFalse(decision.changed)

    def test_task_set_change_restarts_the_observation_window(self):
        policy = auto_policy()
        policy.observe(0, {"a": 1.0}, HEALTHY)
        policy.observe(15, {"a": 1.0, "b": 1.0}, HEALTHY)

        decision = policy.observe(
            20,
            {"a": 1.0, "b": 1.0},
            HEALTHY,
        )

        self.assertEqual(decision.target_concurrency, 1)

    def test_two_high_cpu_windows_reduce_an_accepted_level(self):
        policy = accept_two_way_trial()
        high_cpu = ResourceSnapshot(95.0, 8 * GIB, 16 * GIB)

        policy.observe(70, {"a": 0.65, "b": 0.65}, high_cpu)
        first = policy.observe(
            90,
            {"a": 0.65, "b": 0.65},
            high_cpu,
        )
        policy.observe(100, {"a": 0.65, "b": 0.65}, high_cpu)
        second = policy.observe(
            120,
            {"a": 0.65, "b": 0.65},
            high_cpu,
        )

        self.assertEqual(first.target_concurrency, 2)
        self.assertEqual(second.target_concurrency, 1)
        self.assertIn("cpu", second.reason)


if __name__ == "__main__":
    unittest.main()
