import os
import shutil
import time
from dataclasses import dataclass

from config import (
    SAVE_MODE_OVERWRITE,
    SAVE_MODE_REMAIN,
    SAVE_MODE_SAVE_AS,
)


SESSION_PREFIX = "mgw-session-"


@dataclass(frozen=True)
class TaskPaths:
    task_dir: str
    ab_av1_dir: str
    temp_output: str
    final_output: str


@dataclass(frozen=True)
class OutputConflict:
    output_path: str
    input_paths: tuple[str, ...]


def build_final_output(input_path, save_mode, export_dir):
    absolute_input = os.path.abspath(os.fspath(input_path))
    base_name = os.path.splitext(os.path.basename(absolute_input))[0]
    source_dir = os.path.dirname(absolute_input)

    if save_mode == SAVE_MODE_OVERWRITE:
        output_dir = source_dir
        output_name = f"{base_name}.mkv"
    elif save_mode == SAVE_MODE_REMAIN:
        output_dir = source_dir
        output_name = f"{base_name}_opt.mkv"
    elif save_mode == SAVE_MODE_SAVE_AS:
        output_dir = os.path.abspath(os.fspath(export_dir))
        output_name = f"{base_name}.mkv"
    else:
        raise ValueError(f"unsupported save mode: {save_mode!r}")

    return os.path.abspath(os.path.join(output_dir, output_name))


def find_output_conflicts(inputs, save_mode, export_dir):
    absolute_inputs = [
        os.path.abspath(os.fspath(path))
        for path in inputs
    ]
    normalized_inputs = {
        _normalize(path): path
        for path in absolute_inputs
    }
    outputs = {}

    for input_path in absolute_inputs:
        output_path = build_final_output(
            input_path,
            save_mode,
            export_dir,
        )
        normalized_output = _normalize(output_path)
        entry = outputs.setdefault(
            normalized_output,
            {
                "output_path": output_path,
                "producers": [],
            },
        )
        entry["producers"].append(input_path)

    conflicts = []
    for normalized_output, entry in outputs.items():
        involved = list(entry["producers"])
        matched_input = normalized_inputs.get(normalized_output)
        if matched_input is not None:
            producer_norms = {
                _normalize(path)
                for path in entry["producers"]
            }
            if (
                len(entry["producers"]) > 1
                or producer_norms != {normalized_output}
            ):
                involved.append(matched_input)

        unique_inputs = tuple(dict.fromkeys(involved))
        if len(entry["producers"]) > 1 or len(unique_inputs) > 1:
            conflicts.append(
                OutputConflict(
                    output_path=entry["output_path"],
                    input_paths=unique_inputs,
                )
            )

    return tuple(conflicts)


def create_session_root(cache_root, batch_id):
    session_root = os.path.abspath(
        os.path.join(
            os.fspath(cache_root),
            f"{SESSION_PREFIX}{batch_id}",
        )
    )
    os.makedirs(session_root, exist_ok=False)
    return session_root


def create_task_paths(session_root, task_id, final_output):
    task_dir = os.path.abspath(
        os.path.join(
            os.fspath(session_root),
            f"task-{task_id}",
        )
    )
    ab_av1_dir = os.path.join(task_dir, "ab-av1")
    os.makedirs(ab_av1_dir, exist_ok=False)
    return TaskPaths(
        task_dir=task_dir,
        ab_av1_dir=ab_av1_dir,
        temp_output=os.path.join(task_dir, "output.temp.mkv"),
        final_output=os.path.abspath(os.fspath(final_output)),
    )


def cleanup_stale_sessions(
    cache_root,
    active_session_ids=(),
    min_age_seconds=24 * 60 * 60,
    now=None,
):
    root = os.path.abspath(os.fspath(cache_root))
    if not os.path.isdir(root):
        return ()

    active_names = {
        f"{SESSION_PREFIX}{session_id}"
        for session_id in active_session_ids
    }
    current_time = time.time() if now is None else float(now)
    removed = []

    for entry in os.scandir(root):
        if not entry.is_dir(follow_symlinks=False):
            continue
        if not entry.name.startswith(SESSION_PREFIX):
            continue
        if entry.name in active_names:
            continue
        age = current_time - entry.stat(follow_symlinks=False).st_mtime
        if age < min_age_seconds:
            continue
        shutil.rmtree(entry.path)
        removed.append(entry.path)

    return tuple(removed)


def _normalize(path):
    return os.path.normcase(
        os.path.normpath(
            os.path.abspath(path)
        )
    )
