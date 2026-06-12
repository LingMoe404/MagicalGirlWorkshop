from collections import deque
from enum import Enum


class TaskState(Enum):
    QUEUED = "queued"
    PROBING = "probing"
    ENCODING = "encoding"
    WAITING_DECISION = "waiting_decision"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_STATES = {TaskState.PROBING, TaskState.ENCODING}
TERMINAL_STATES = {
    TaskState.SUCCESS,
    TaskState.SKIPPED,
    TaskState.FAILED,
    TaskState.CANCELLED,
}


class BatchSchedule:
    def __init__(self, files):
        self._files = tuple(files)
        self._queue = deque(self._files)
        self._states = {
            path: TaskState.QUEUED
            for path in self._files
        }

    @property
    def active_files(self):
        return tuple(
            path
            for path in self._files
            if self._states[path] in ACTIVE_STATES
        )

    @property
    def terminal_files(self):
        return tuple(
            path
            for path in self._files
            if self._states[path] in TERMINAL_STATES
        )

    @property
    def queued_count(self):
        return sum(
            state is TaskState.QUEUED
            for state in self._states.values()
        )

    @property
    def waiting_count(self):
        return sum(
            state is TaskState.WAITING_DECISION
            for state in self._states.values()
        )

    @property
    def is_finished(self):
        return all(
            state in TERMINAL_STATES
            for state in self._states.values()
        )

    def state_of(self, path):
        return self._states[path]

    def fill_slots(self, target_concurrency):
        available = max(
            0,
            int(target_concurrency) - len(self.active_files),
        )
        started = []
        while available and self._queue:
            path = self._queue.popleft()
            if self._states[path] is not TaskState.QUEUED:
                continue
            self._states[path] = TaskState.PROBING
            started.append(path)
            available -= 1
        return started

    def mark_encoding(self, path):
        self._states[path] = TaskState.ENCODING

    def mark_waiting_decision(self, path):
        self._states[path] = TaskState.WAITING_DECISION

    def mark_terminal(self, path, state):
        if state not in TERMINAL_STATES:
            raise ValueError(f"{state!r} is not a terminal task state")
        self._states[path] = state

    def cancel_all(self):
        self._queue.clear()
        for path, state in self._states.items():
            if state not in TERMINAL_STATES:
                self._states[path] = TaskState.CANCELLED
