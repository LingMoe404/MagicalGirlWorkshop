import statistics
from dataclasses import dataclass
from enum import Enum

GIB = 1024**3


class ConcurrencyMode(Enum):
    AUTO = "auto"
    MANUAL = "manual"


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_percent: float
    available_memory: int
    total_memory: int


@dataclass(frozen=True)
class ConcurrencyDecision:
    target_concurrency: int
    reason: str = ""
    changed: bool = False
    accepted: bool = False


class DynamicConcurrencyPolicy:
    def __init__(
        self,
        mode,
        manual_limit=2,
        auto_max=3,
        warmup_seconds=60,
        window_seconds=90,
        cooldown_seconds=120,
        minimum_gain=0.15,
    ):
        self.mode = ConcurrencyMode(mode)
        self.auto_max = max(1, min(3, int(auto_max)))
        self.warmup_seconds = max(0.0, float(warmup_seconds))
        self.window_seconds = max(0.0, float(window_seconds))
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self.minimum_gain = max(0.0, float(minimum_gain))

        if self.mode is ConcurrencyMode.MANUAL:
            self.target_concurrency = max(1, min(4, int(manual_limit)))
        else:
            self.target_concurrency = 1

        self._baselines = {}
        self._blacklisted_levels = set()
        self._trial_from_level = None
        self._window_task_ids = None
        self._window_started_at = None
        self._throughput_samples = []
        self._resource_samples = []
        self._cooldown_until = 0.0
        self._high_cpu_windows = 0
        self._low_throughput_windows = 0

    @property
    def blacklisted_levels(self):
        return frozenset(self._blacklisted_levels)

    def baseline_for(self, level):
        return self._baselines.get(level)

    def observe(
        self,
        now,
        encoding_speeds,
        resources,
        hardware_resource_error=False,
        paused=False,
    ):
        now = float(now)

        if hardware_resource_error:
            return self._reduce_target(
                now,
                "hardware resource pressure",
                blacklist_current=True,
            )

        if self._is_critical_memory(resources):
            return self._reduce_target(now, "low memory")

        if self.mode is ConcurrencyMode.MANUAL:
            return self._unchanged()

        if paused:
            self._reset_window()
            return self._unchanged()

        speeds = {
            str(task_id): float(speed)
            for task_id, speed in encoding_speeds.items()
            if float(speed) >= 0
        }
        if not speeds:
            self._reset_window()
            return self._unchanged()

        task_ids = frozenset(speeds)
        total_throughput = sum(speeds.values())
        if self._window_task_ids != task_ids:
            self._start_window(
                now,
                task_ids,
                total_throughput,
                resources,
            )
            return self._unchanged()

        self._throughput_samples.append(total_throughput)
        self._resource_samples.append(resources)
        required_duration = self.warmup_seconds + self.window_seconds
        if now - self._window_started_at < required_duration:
            return self._unchanged()

        throughput = statistics.median(self._throughput_samples)
        average_cpu = statistics.fmean(
            sample.cpu_percent for sample in self._resource_samples
        )
        minimum_available_memory = min(
            sample.available_memory for sample in self._resource_samples
        )
        total_memory = max(sample.total_memory for sample in self._resource_samples)

        if self._trial_from_level is not None:
            return self._finish_trial(now, throughput)

        current_baseline = self._baselines.get(self.target_concurrency)
        if current_baseline is None:
            self._baselines[self.target_concurrency] = throughput
            current_baseline = throughput

        if average_cpu >= 92.0:
            self._high_cpu_windows += 1
        else:
            self._high_cpu_windows = 0

        if throughput < current_baseline * 0.8:
            self._low_throughput_windows += 1
        else:
            self._low_throughput_windows = 0

        if self._high_cpu_windows >= 2:
            return self._reduce_target(now, "sustained high cpu")
        if self._low_throughput_windows >= 2:
            return self._reduce_target(now, "sustained throughput loss")

        can_upgrade = (
            now >= self._cooldown_until
            and self.target_concurrency < self.auto_max
            and self.target_concurrency + 1 not in self._blacklisted_levels
            and average_cpu < 85.0
            and minimum_available_memory >= 2 * GIB
            and (total_memory <= 0 or minimum_available_memory >= total_memory * 0.1)
        )
        if can_upgrade:
            previous_level = self.target_concurrency
            self.target_concurrency += 1
            self._trial_from_level = previous_level
            self._cooldown_until = now + self.cooldown_seconds
            self._reset_window()
            return ConcurrencyDecision(
                target_concurrency=self.target_concurrency,
                reason=f"trial concurrency {self.target_concurrency}",
                changed=True,
            )

        self._reset_window()
        return self._unchanged()

    def _finish_trial(self, now, throughput):
        previous_level = self._trial_from_level
        previous_baseline = self._baselines[previous_level]
        trial_level = self.target_concurrency
        self._trial_from_level = None
        self._cooldown_until = now + self.cooldown_seconds
        self._reset_window()

        if throughput >= previous_baseline * (1 + self.minimum_gain):
            self._baselines[trial_level] = throughput
            self._high_cpu_windows = 0
            self._low_throughput_windows = 0
            return ConcurrencyDecision(
                target_concurrency=trial_level,
                reason=f"accepted concurrency {trial_level}",
                accepted=True,
            )

        self._blacklisted_levels.update(range(trial_level, self.auto_max + 1))
        self.target_concurrency = previous_level
        return ConcurrencyDecision(
            target_concurrency=previous_level,
            reason=f"rejected concurrency {trial_level}",
            changed=True,
        )

    def _reduce_target(
        self,
        now,
        reason,
        blacklist_current=False,
    ):
        if self.target_concurrency <= 1:
            return self._unchanged(reason)

        previous_level = self.target_concurrency
        self.target_concurrency -= 1
        if blacklist_current:
            self._blacklisted_levels.update(range(previous_level, self.auto_max + 1))
        self._trial_from_level = None
        self._cooldown_until = now + self.cooldown_seconds
        self._high_cpu_windows = 0
        self._low_throughput_windows = 0
        self._reset_window()
        return ConcurrencyDecision(
            target_concurrency=self.target_concurrency,
            reason=reason,
            changed=True,
        )

    def _is_critical_memory(self, resources):
        if resources.available_memory < GIB:
            return True
        return (
            resources.total_memory > 0
            and resources.available_memory < resources.total_memory * 0.05
        )

    def _start_window(
        self,
        now,
        task_ids,
        throughput,
        resources,
    ):
        self._window_task_ids = task_ids
        self._window_started_at = now
        self._throughput_samples = [throughput]
        self._resource_samples = [resources]

    def _reset_window(self):
        self._window_task_ids = None
        self._window_started_at = None
        self._throughput_samples = []
        self._resource_samples = []

    def _unchanged(self, reason=""):
        return ConcurrencyDecision(
            target_concurrency=self.target_concurrency,
            reason=reason,
        )
