# NVENC 远程桌面解码降级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 NVIDIA 硬件解码从 DXVA2 自动选择改为 CUDA 优先，并根据真实 FFmpeg 错误最多执行三次有针对性的降级尝试。

**Architecture:** 新增不依赖 Qt 的 `workers/ffmpeg_retry.py`，集中生成硬件解码参数、分类 FFmpeg 错误并计算下一次尝试状态。`EncoderWorker` 使用该模块构造命令和控制重试，现有 NVENC 编码质量参数保持不变。

**Tech Stack:** Python 3.12、标准库 `dataclasses`/`enum`/`unittest`、FFmpeg、PySide6。

---

### Task 1: FFmpeg 降级策略

**Files:**
- Create: `workers/ffmpeg_retry.py`
- Create: `tests/test_ffmpeg_retry.py`

- [x] **Step 1: 写入失败测试**

测试以下行为：

```python
def test_nvenc_uses_explicit_cuda_decode(self):
    self.assertEqual(
        build_hw_decode_args("av1_nvenc", enabled=True),
        ["-hwaccel", "cuda", "-v", "verbose"],
    )

def test_hardware_error_falls_back_to_software_decode(self):
    state = RetryState(use_hw_decode=True, include_subtitles=True)
    result = next_retry_state(
        state,
        ["[DXVA2] Failed to create Direct3D device", "Device creation failed"],
    )
    self.assertEqual(
        result,
        RetryDecision(
            state=RetryState(use_hw_decode=False, include_subtitles=True),
            reason=FailureKind.HARDWARE_DEVICE,
        ),
    )

def test_subtitle_error_drops_only_subtitles(self):
    state = RetryState(use_hw_decode=True, include_subtitles=True)
    result = next_retry_state(
        state,
        ["Error while decoding subtitle stream #0:2"],
    )
    self.assertEqual(
        result,
        RetryDecision(
            state=RetryState(use_hw_decode=True, include_subtitles=False),
            reason=FailureKind.SUBTITLE,
        ),
    )

def test_unknown_error_does_not_retry(self):
    self.assertIsNone(
        next_retry_state(
            RetryState(use_hw_decode=True, include_subtitles=True),
            ["Permission denied while opening output file"],
        )
    )
```

- [x] **Step 2: 运行测试并确认失败**

Run: `uv run python -m unittest tests.test_ffmpeg_retry -v`

Expected: FAIL，因为 `workers.ffmpeg_retry` 尚不存在。

- [x] **Step 3: 实现最小策略模块**

实现：

```python
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

def build_hw_decode_args(encoder_name, enabled):
    ...

def classify_ffmpeg_failure(log_lines):
    ...

def next_retry_state(state, log_lines):
    ...
```

NVENC 返回显式 CUDA 参数；QSV 和 AMF 保留原行为。硬件设备错误仅关闭硬解，字幕错误仅关闭字幕，未知错误返回 `None`。

- [x] **Step 4: 补充顺序和三次上限测试**

覆盖：

```python
def test_hardware_then_subtitle_uses_three_unique_states(self):
    first = RetryState(True, True)
    second = next_retry_state(first, ["Device creation failed"]).state
    third = next_retry_state(
        second, ["Error while decoding subtitle stream #0:2"]
    ).state
    self.assertEqual(
        [first, second, third],
        [
            RetryState(True, True),
            RetryState(False, True),
            RetryState(False, False),
        ],
    )

def test_subtitle_then_hardware_uses_three_unique_states(self):
    first = RetryState(True, True)
    second = next_retry_state(
        first, ["Error while decoding subtitle stream #0:2"]
    ).state
    third = next_retry_state(second, ["Failed to create CUDA context"]).state
    self.assertEqual(
        [first, second, third],
        [
            RetryState(True, True),
            RetryState(True, False),
            RetryState(False, False),
        ],
    )
```

- [x] **Step 5: 运行策略测试**

Run: `uv run python -m unittest tests.test_ffmpeg_retry -v`

Expected: PASS。

### Task 2: 接入 EncoderWorker

**Files:**
- Modify: `workers/encoder.py`
- Modify: `tests/test_ffmpeg_retry.py`

- [x] **Step 1: 添加命令参数回归断言**

确认 NVENC 参数不含 `auto`，关闭硬解时不注入 `-hwaccel`。

- [x] **Step 2: 运行测试并确认当前集成要求失败**

Run: `uv run python -m unittest tests.test_ffmpeg_retry -v`

Expected: 新增集成断言 FAIL。

- [x] **Step 3: 修改命令构造和重试循环**

在 `EncoderWorker` 中：

```python
retry_state = RetryState(
    use_hw_decode=self.config.get("hw_decoding", True),
    include_subtitles=True,
)
attempted_states = set()

for attempt in range(3):
    attempted_states.add(retry_state)
    cmd.extend(build_hw_decode_args(enc_name, retry_state.use_hw_decode))
    ...
    if retry_state.include_subtitles:
        cmd.extend(["-c:s", sub_codec, "-map", "0:s?"])
    else:
        cmd.extend(["-sn"])
    ...
    decision = next_retry_state(retry_state, err_log)
    if decision is None or decision.state in attempted_states:
        break
    retry_state = decision.state
```

根据 `FailureKind` 输出硬解降级或字幕降级日志，并在每次重试前删除失败的临时文件。

- [x] **Step 4: 运行测试**

Run: `uv run python -m unittest discover -s tests -v`

Expected: PASS。

### Task 3: 版本与发布说明

**Files:**
- Modify: `config.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `README_JP.md`
- Create: `docs/releases/Releases1.3.1.md`

- [x] **Step 1: 将版本更新为 1.3.1**

更新应用版本和包锁定信息：

```text
config.py: VERSION = "1.3.1"
pyproject.toml: version = "1.3.1"
uv.lock: magicalgirlworkshop version = "1.3.1"
```

- [x] **Step 2: 编写发布说明**

说明：

- RDP 锁屏或断开后不再因 DXVA2 Direct3D 设备创建失败而中止。
- NVIDIA 解码改为 CUDA 优先。
- CUDA 硬解失败时当前文件自动切换 CPU 解码，NVENC 编码质量参数不变。
- 只有真实字幕错误才丢弃字幕。
- 未知错误不再被误报为字幕错误。

- [x] **Step 3: 更新 CHANGELOG**

在顶部增加 `v1.3.1 (2026-06-12)` 条目。

### Task 4: 完整验证

**Files:**
- Verify all modified files

- [x] **Step 1: 运行单元测试**

Run: `uv run python -m unittest discover -s tests -v`

Expected: 全部 PASS。

- [x] **Step 2: 运行语法编译**

Run: `uv run python -m compileall workers tests config.py`

Expected: exit code 0。

- [x] **Step 3: 运行 Ruff**

Run: `uv run ruff check workers/ffmpeg_retry.py tests/test_ffmpeg_retry.py config.py`

Expected: exit code 0。`workers/encoder.py` 的历史格式告警不在本次修复范围内。

- [x] **Step 4: 执行 FFmpeg CUDA 冒烟测试**

生成一秒 H.264 测试源，再执行显式 CUDA 解码到 null 输出，确认当前 FFmpeg 构建支持该命令。

- [x] **Step 5: 检查最终差异**

Run: `git diff --check` 和 `git status --short`

Expected: 无空白错误，只包含本次设计、计划、实现、测试、版本和发布文档。
