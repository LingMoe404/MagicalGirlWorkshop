import ctypes

from .concurrency_policy import ResourceSnapshot


class _FileTime(ctypes.Structure):
    _fields_ = [
        ("low", ctypes.c_ulong),
        ("high", ctypes.c_ulong),
    ]


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


class WindowsResourceSampler:
    def __init__(self, times_reader=None, memory_reader=None):
        self._times_reader = times_reader or _read_system_times
        self._memory_reader = memory_reader or _read_memory_status
        self._previous_times = None

    def sample(self):
        current_times = self._times_reader()
        available_memory, total_memory = self._memory_reader()
        cpu_percent = self._calculate_cpu_percent(current_times)
        self._previous_times = current_times
        return ResourceSnapshot(
            cpu_percent=cpu_percent,
            available_memory=int(available_memory),
            total_memory=int(total_memory),
        )

    def _calculate_cpu_percent(self, current_times):
        if self._previous_times is None:
            return 0.0

        idle_delta = current_times[0] - self._previous_times[0]
        kernel_delta = current_times[1] - self._previous_times[1]
        user_delta = current_times[2] - self._previous_times[2]
        total_delta = kernel_delta + user_delta
        if total_delta <= 0:
            return 0.0

        busy_delta = total_delta - idle_delta
        percentage = (busy_delta / total_delta) * 100
        return round(max(0.0, min(100.0, percentage)), 2)


def _read_system_times():
    idle = _FileTime()
    kernel = _FileTime()
    user = _FileTime()
    success = ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    )
    if not success:
        raise ctypes.WinError()
    return (
        _file_time_value(idle),
        _file_time_value(kernel),
        _file_time_value(user),
    )


def _read_memory_status():
    status = _MemoryStatusEx()
    status.length = ctypes.sizeof(_MemoryStatusEx)
    success = ctypes.windll.kernel32.GlobalMemoryStatusEx(
        ctypes.byref(status)
    )
    if not success:
        raise ctypes.WinError()
    return status.available_physical, status.total_physical


def _file_time_value(file_time):
    return (file_time.high << 32) | file_time.low
