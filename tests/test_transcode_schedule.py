import unittest

from workers.transcode_schedule import BatchSchedule, TaskState


class BatchScheduleTests(unittest.TestCase):
    def test_fill_slots_starts_queued_files_in_order(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4", "c.mp4"])

        started = schedule.fill_slots(target_concurrency=2)

        self.assertEqual(started, ["a.mp4", "b.mp4"])
        self.assertEqual(schedule.state_of("a.mp4"), TaskState.PROBING)
        self.assertEqual(schedule.state_of("c.mp4"), TaskState.QUEUED)
        self.assertEqual(schedule.active_files, ("a.mp4", "b.mp4"))

    def test_waiting_decision_releases_a_slot(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4"])
        schedule.fill_slots(target_concurrency=1)

        schedule.mark_waiting_decision("a.mp4")

        self.assertEqual(schedule.waiting_count, 1)
        self.assertEqual(schedule.fill_slots(1), ["b.mp4"])
        self.assertEqual(schedule.active_files, ("b.mp4",))

    def test_lower_target_does_not_cancel_active_tasks(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4", "c.mp4"])
        schedule.fill_slots(target_concurrency=3)

        started = schedule.fill_slots(target_concurrency=1)

        self.assertEqual(started, [])
        self.assertEqual(
            schedule.active_files,
            ("a.mp4", "b.mp4", "c.mp4"),
        )

    def test_mark_encoding_preserves_active_slot(self):
        schedule = BatchSchedule(["a.mp4"])
        schedule.fill_slots(1)

        schedule.mark_encoding("a.mp4")

        self.assertEqual(schedule.state_of("a.mp4"), TaskState.ENCODING)
        self.assertEqual(schedule.active_files, ("a.mp4",))

    def test_terminal_states_finish_batch(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4"])
        schedule.fill_slots(2)

        schedule.mark_terminal("a.mp4", TaskState.SUCCESS)
        schedule.mark_terminal("b.mp4", TaskState.SKIPPED)

        self.assertTrue(schedule.is_finished)
        self.assertEqual(schedule.terminal_files, ("a.mp4", "b.mp4"))

    def test_stop_cancels_queued_active_and_waiting_files(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4", "c.mp4"])
        schedule.fill_slots(2)
        schedule.mark_waiting_decision("a.mp4")

        schedule.cancel_all()

        self.assertEqual(schedule.state_of("a.mp4"), TaskState.CANCELLED)
        self.assertEqual(schedule.state_of("b.mp4"), TaskState.CANCELLED)
        self.assertEqual(schedule.state_of("c.mp4"), TaskState.CANCELLED)
        self.assertTrue(schedule.is_finished)
        self.assertEqual(schedule.queued_count, 0)

    def test_terminal_task_cannot_be_requeued(self):
        schedule = BatchSchedule(["a.mp4", "b.mp4"])
        schedule.fill_slots(1)
        schedule.mark_terminal("a.mp4", TaskState.FAILED)

        self.assertEqual(schedule.fill_slots(1), ["b.mp4"])
        self.assertEqual(schedule.state_of("a.mp4"), TaskState.FAILED)

    def test_mark_terminal_rejects_nonterminal_state(self):
        schedule = BatchSchedule(["a.mp4"])

        with self.assertRaises(ValueError):
            schedule.mark_terminal("a.mp4", TaskState.ENCODING)


if __name__ == "__main__":
    unittest.main()
