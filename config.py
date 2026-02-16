# config.py
from PySide6.QtCore import QSize

VERSION = "1.2.0"
APP_TITLE = f"魔法少女工坊 v{VERSION}"
APP_ID = f"LingMoe404.MagicWorkshop.Encoder.{VERSION}"

# 编码器名称
ENC_QSV = "Intel QSV"
ENC_NVENC = "NVIDIA NVENC"
ENC_AMF = "AMD AMF"

# 默认参数
DEFAULT_VMAF = "93.0"
DEFAULT_AUDIO_BITRATE = "96k"
DEFAULT_PRESET = "4"
DEFAULT_ICQ = 24
DEFAULT_LOUDNORM_FILTER = "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"

# FFmpeg 相关
AUDIO_CODEC = "libopus"
SAMPLE_RATE = "48000"
PIX_FMT_10BIT = "p010le"
PIX_FMT_AB_AV1 = "yuv420p10le"
SUBTITLE_CODEC_SRT = "subrip"

# 性能与限制
MAX_DURATION_WORKERS = 3
MAX_THUMBNAIL_WORKERS = 2
MAX_THUMBNAIL_CACHE_SIZE = 200
LOG_UPDATE_INTERVAL = 50
LOG_MAX_BLOCKS = 2000
GPU_COOLING_TIME = 3
ERROR_DECISION_TIMEOUT = 30
DEPENDENCY_CHECK_DELAY = 500

# UI 相关
MIN_WINDOW_SIZE = QSize(1180, 780)
NAV_EXPAND_WIDTH = 180
THEMES = ["Auto", "Light", "Dark"]

VIDEO_EXTS = ('.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts')
SAVE_MODE_SAVE_AS = "开辟新世界 (Save As)"
SAVE_MODE_OVERWRITE = "元素覆写 (Overwrite)"
SAVE_MODE_REMAIN = "元素保留 (Remain)"

LOUDNORM_MODE_ALWAYS = "全部启用 (Always)"
LOUDNORM_MODE_DISABLE = "全部禁用 (Disable)"
LOUDNORM_MODE_AUTO = "仅立体声/单声道 (Stereo/Mono Only)"

DEFAULT_SETTINGS = {
    "encoder": ENC_QSV,
    "theme": "Auto",
    "save_mode": "元素覆写 (Overwrite)",
    "export_dir": ""
}

ENCODER_CONFIGS = {
    ENC_QSV: {
        "vmaf": DEFAULT_VMAF,
        "audio_bitrate": DEFAULT_AUDIO_BITRATE,
        "preset": DEFAULT_PRESET,
        "loudnorm": DEFAULT_LOUDNORM_FILTER,
        "loudnorm_mode": LOUDNORM_MODE_AUTO,
        "nv_aq": "True"
    },
    ENC_NVENC: {
        "vmaf": "95.0",
        "audio_bitrate": DEFAULT_AUDIO_BITRATE,
        "preset": DEFAULT_PRESET,
        "loudnorm": DEFAULT_LOUDNORM_FILTER,
        "loudnorm_mode": LOUDNORM_MODE_AUTO,
        "nv_aq": "True"
    },
    ENC_AMF: {
        "vmaf": "97.0",
        "audio_bitrate": DEFAULT_AUDIO_BITRATE,
        "preset": DEFAULT_PRESET,
        "loudnorm": DEFAULT_LOUDNORM_FILTER,
        "loudnorm_mode": LOUDNORM_MODE_AUTO,
        "nv_aq": "True"
    }
}
