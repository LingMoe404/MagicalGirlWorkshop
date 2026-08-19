import statistics


def map_probe_progress(strategy_index, strategy_count):
    if strategy_count <= 0:
        return 0
    completed = max(0, min(strategy_count, strategy_index + 1))
    return min(15, round((completed / strategy_count) * 15))


def map_encode_progress(ffmpeg_percent):
    percent = max(0.0, min(100.0, float(ffmpeg_percent)))
    return round(15 + percent * 0.85)


def calculate_batch_progress(
    progresses,
    durations,
    terminal_files,
):
    if not progresses:
        return 100

    terminal_files = set(terminal_files)
    known_durations = [
        float(duration)
        for path, duration in durations.items()
        if path in progresses and float(duration) > 0
    ]
    fallback_duration = statistics.median(known_durations) if known_durations else 1.0

    weighted_progress = 0.0
    total_weight = 0.0
    for path, progress in progresses.items():
        duration = float(durations.get(path, 0) or 0)
        weight = duration if duration > 0 else fallback_duration
        effective_progress = (
            100.0 if path in terminal_files else max(0.0, min(100.0, float(progress)))
        )
        weighted_progress += weight * effective_progress
        total_weight += weight

    if total_weight <= 0:
        return 100
    return round(weighted_progress / total_weight)
