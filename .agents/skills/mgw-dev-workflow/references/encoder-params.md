# 硬件编码器参数差异（从 AGENTS.md §5.3 移出）

三种编码器（QSV/NVENC/AMF）参数差异巨大，集中在 `config.py` 的 `ENCODER_CONFIGS` 和
`workers/command_builder.py` 的 `build_video_encoder_args()`（编码参数）与
`workers/encoder.py` 的预设选择逻辑（约 975-995 行）。

## 参数对照

| 特性 / 参数 | Intel QSV (默认) | NVIDIA NVENC | AMD AMF |
| :--- | :--- | :--- | :--- |
| FFmpeg 编码器 | `av1_qsv` | `av1_nvenc` | `av1_amf` |
| 质量控制参数 | `-global_quality:v` | `-cq` | `-qvbr_quality_level` |
| 速度预设 | `1` (慢) - `7` (快) | `p7` (慢) - `p1` (快) | `quality` (慢) - `speed` (快) |
| 码率控制 | 硬件 ICQ 模式 | `vbr` + `-b:v 0`（解除码率限制） | `-rc vbr_latency` + QVBR |
| 感知增强 (AQ) | `-look_ahead 1` | `-spatial-aq 1 -temporal-aq 1` | `-preanalysis true` |
| 像素格式 | `p010le` (10-bit) | `p010le` (10-bit) | `yuv420p` (8-bit) |
| 附加参数 | — | — | `-usage transcoding`、`-quality <preset>` |

`config.py` 中默认 VMAF 目标均为 `93.0`；默认灵力偏移（`amf_offset`）为 QSV `-2`、
NVENC `-4`、AMF `-6`；统一预设值 `DEFAULT_PRESET = "4"`。

## 预设映射（UI 统一 1-7 数字）

`workers/encoder.py` 先把 UI 预设夹紧到 1-7（`max(1, min(7, p_val))`），再按编码器映射：

- **QSV**：直接使用数字本身 `str(p_val)`（1 慢 - 7 快）
- **NVENC**：`nv_p = 8 - p_val`，得到 `p{nv_p}`（即 1→`p7`，7→`p1`）
- **AMF**：`p_val <= 2` → `quality`；`3 <= p_val <= 5` → `balanced`；`p_val >= 6` → `speed`
  （界面统一数字的映射为 `1-2`→`quality`，`3-5`→`balanced`，`6-7`→`speed`）

## ab-av1 探测策略

`EncoderWorker._probe_vmaf()` 构造的探测策略列表有顺序含义：

- **AMF 被显式排除在硬件探测之外**（`if enc_name != "av1_amf"`），因为 ab-av1 原生不支持
  `av1_amf`；AMD 模式强制走 CPU 探测：`libsvtav1`（预设 `min(12, p_val + 5)`）→
  `libaom-av1`（预设 `6`）
- QSV / NVENC 先尝试硬件探测（`{"encoder": enc_name, "preset": enc_preset}`），失败再回退到
  上述 CPU 策略
- CPU 探测的 CRF 上限为 `63`；硬件/CPU 混用时的画质偏移由 `amf_offset` 校正
  （`raw_icq = cpu_crf + offset`，仅当探测走 CPU 而目标为硬件编码器时）
- `ab_av1_result.py` 负责解析 ab-av1 输出（CRF/VMAF 候选 + 质量回退）

## 修改参数时的检查清单

1. 改 `config.py` 的 `ENCODER_CONFIGS` / 常量，或 `workers/command_builder.py` 的参数拼装
2. 同步核对 `README.md` 的“编码器参数对比”表（面向用户的速查表）
3. `tests/test_command_builder.py` 与 `tests/test_encoder.py` 用 argv 快照锁定参数逐字输出，
   必须一并更新
4. 运行 `uv run python -m unittest tests.test_command_builder tests.test_encoder`

> 注：三家算法不同，相同质量数值（如 30）在不同显卡上的表现不可直接类比，以 VMAF 结果为准。
