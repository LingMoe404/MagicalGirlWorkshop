import re
from dataclasses import dataclass
from enum import Enum


class FailureKind(Enum):
    HARDWARE_DEVICE = "hardware_device"
    SUBTITLE = "subtitle"


@dataclass(frozen=True)
class RetryState:
    use_hw_decode: bool
    include_subtitles: bool


@dataclass(frozen=True)
class RetryDecision:
    state: RetryState
    reason: FailureKind


_HARDWARE_DEVICE_ERRORS = (
    "failed to create direct3d device",
    "failed to create d3d11 device",
    "failed to create d3d12 device",
    "device creation failed",
    "device setup failed for decoder",
    "no device available for decoder",
    "failed to create cuda context",
    "failed to initialize cuda",
    "failed to initialise cuda",
    "cannot load nvcuda",
    "could not dynamically load cuda",
    "failed to create specified hw device",
    "failed to get hw surface format",
    "cuda_error",
)

_SUBTITLE_ERROR_DETAILS = (
    "error",
    "failed",
    "invalid",
    "not supported",
    "only possible",
    "unable",
    "could not",
)

_HARDWARE_RESOURCE_ERRORS = (
    "out of memory",
    "not enough memory",
    "cannot allocate memory",
    "mfx_err_memory_alloc",
    "mfx_err_device_busy",
    "amf_out_of_memory",
    "amf_input_full",
    "maximum number of concurrent sessions",
    "too many concurrent sessions",
    "failed to open encode session",
    "encoder device is busy",
    "resource temporarily unavailable",
)


def build_hw_decode_args(encoder_name, enabled):
    if not enabled:
        return ["-v", "verbose"]

    if encoder_name.endswith("_qsv"):
        return [
            "-init_hw_device",
            "qsv=hw",
            "-filter_hw_device",
            "hw",
            "-hwaccel",
            "qsv",
            "-v",
            "verbose",
        ]
    if encoder_name.endswith("_nvenc"):
        return ["-hwaccel", "cuda", "-v", "verbose"]
    if encoder_name.endswith("_amf"):
        return ["-hwaccel", "auto", "-v", "verbose"]
    return ["-v", "verbose"]


def classify_ffmpeg_failure(log_lines):
    normalized_lines = [line.casefold() for line in log_lines]

    if any(
        marker in line
        for line in normalized_lines
        for marker in _HARDWARE_DEVICE_ERRORS
    ):
        return FailureKind.HARDWARE_DEVICE

    subtitle_stream_ids = {
        match.group("stream")
        for line in normalized_lines
        if (
            match := re.search(
                r"stream #(?P<stream>\d+:\d+)(?:\([^)]*\))?: subtitle",
                line,
            )
        )
    }

    for line in normalized_lines:
        has_error_detail = any(detail in line for detail in _SUBTITLE_ERROR_DETAILS)
        if not has_error_detail:
            continue
        if "subtitle" in line or "[sost#" in line:
            return FailureKind.SUBTITLE
        if any(f"stream #{stream_id}" in line for stream_id in subtitle_stream_ids):
            return FailureKind.SUBTITLE

    return None


def next_retry_state(state, log_lines):
    failure_kind = classify_ffmpeg_failure(log_lines)

    if failure_kind is FailureKind.HARDWARE_DEVICE and state.use_hw_decode:
        return RetryDecision(
            state=RetryState(
                use_hw_decode=False,
                include_subtitles=state.include_subtitles,
            ),
            reason=failure_kind,
        )

    if failure_kind is FailureKind.SUBTITLE and state.include_subtitles:
        return RetryDecision(
            state=RetryState(
                use_hw_decode=state.use_hw_decode,
                include_subtitles=False,
            ),
            reason=failure_kind,
        )

    return None


def is_hardware_resource_error(log_lines):
    return any(
        marker in line.casefold()
        for line in log_lines
        for marker in _HARDWARE_RESOURCE_ERRORS
    )
