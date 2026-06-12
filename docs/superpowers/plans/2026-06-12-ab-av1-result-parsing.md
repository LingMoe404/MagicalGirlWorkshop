# ab-av1 探测结果解析实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 正确区分 ab-av1 的样本行、CRF 汇总行和最终成功行，并在“VMAF 与体积限制无解”时优先选择满足目标画质的最省空间候选。

**Architecture:** 新增 `workers/ab_av1_result.py`，以纯 Python 数据类收集每个 CRF 的汇总 VMAF 和预测体积百分比，并根据退出码和最终错误决定正常成功、画质优先后备或失败。`EncoderWorker` 不再根据任意样本行设置成功状态。

**Tech Stack:** Python 3.12、标准库 `dataclasses`/`re`/`unittest`、ab-av1 0.10.4。

---

### Task 1: ab-av1 输出解析器

**Files:**
- Create: `workers/ab_av1_result.py`
- Create: `tests/test_ab_av1_result.py`

- [x] **Step 1: 写失败测试**

使用真实输出格式覆盖：

```python
parser.feed("sample 1/13 crf 23 VMAF 95.28 (84%)")
parser.feed(
    "crf 23 VMAF 93.69 predicted video stream size "
    "5.00 GiB (84%) taking 10 minutes"
)
parser.feed("crf 23 successful")
result = parser.finish(return_code=0, target_vmaf=93.0)
assert result.crf == 23
assert result.mode is SearchResultMode.SUCCESS
```

并验证多个样本行不会创建重复汇总候选。

- [x] **Step 2: 运行测试确认失败**

Run: `uv run python -m unittest tests.test_ab_av1_result -v`

Expected: FAIL，因为 `workers.ab_av1_result` 尚不存在。

- [x] **Step 3: 实现最小解析器**

定义：

```python
class SearchResultMode(Enum):
    SUCCESS = "success"
    QUALITY_FALLBACK = "quality_fallback"

@dataclass(frozen=True)
class CrfCandidate:
    crf: int
    vmaf: float
    encoded_percent: float

@dataclass(frozen=True)
class SearchResult:
    mode: SearchResultMode
    crf: int
    vmaf: float
    encoded_percent: float

class AbAv1ResultParser:
    def feed(self, line): ...
    def finish(self, return_code, target_vmaf): ...
```

- [x] **Step 4: 增加无解后备测试**

测试：

- CRF 23 汇总 VMAF 93.69、84%，CRF 24 汇总 VMAF 92.76、79%。
- 最终错误为 `Failed to find a suitable crf`。
- 返回 CRF 23，模式为 `QUALITY_FALLBACK`。
- 所有候选低于目标时返回 `None`。
- 未知错误或设备错误返回 `None`。

- [x] **Step 5: 运行解析器测试**

Run: `uv run python -m unittest tests.test_ab_av1_result -v`

Expected: PASS。

### Task 2: 接入 EncoderWorker

**Files:**
- Modify: `workers/encoder.py`
- Modify: `tests/test_ab_av1_result.py`

- [x] **Step 1: 写集成失败测试**

检查 `EncoderWorker.run`：

- 创建 `AbAv1ResultParser`。
- 每行调用 `parser.feed(decoded)`。
- 只对 CRF 汇总候选输出一次日志。
- 在进程结束后调用 `parser.finish(...)`。
- 不再使用 `attempt_success` 或“强行采用”日志。

- [x] **Step 2: 运行测试确认失败**

Run: `uv run python -m unittest tests.test_ab_av1_result.EncoderIntegrationTests -v`

Expected: FAIL。

- [x] **Step 3: 修改探测循环**

删除通用 `CRF + VMAF` 正则和 `attempt_success`。解析器识别到新的 CRF 汇总候选时才更新 UI；结束后：

- `SUCCESS`：正常接受。
- `QUALITY_FALLBACK`：接受候选并显示 VMAF 与预测体积警告。
- `None`：当前策略失败，记录真实尾部日志并进入下一个探测器。

- [x] **Step 4: 运行全部测试**

Run: `uv run python -m unittest discover -s tests -v`

Expected: PASS。

### Task 3: 版本文档

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/releases/Releases1.3.1.md`

- [x] **Step 1: 更新 CHANGELOG**

增加：

- 修复样本日志刷屏。
- 修复 Code 1 仍强行采用最后样本 CRF。
- 无法同时满足 VMAF 与 80% 体积限制时优先保证目标画质。

- [x] **Step 2: 更新 Releases1.3.1.md**

说明正常成功、画质优先后备和真实异常三种结果。

### Task 4: 验证

**Files:**
- Verify all modified files

- [x] **Step 1: 运行全部单元测试**

Run: `uv run python -m unittest discover -s tests -v`

- [x] **Step 2: 运行语法编译**

Run: `uv run python -m compileall workers tests config.py`

- [x] **Step 3: 运行 Ruff**

Run: `uv run ruff check workers/ab_av1_result.py workers/ffmpeg_retry.py tests config.py`

- [x] **Step 4: 使用真实 ab-av1 输出做冒烟测试**

验证成功搜索解析为 `SUCCESS`，人为制造的 `Failed to find a suitable crf` 解析为画质后备或失败，不再采用样本行。

- [x] **Step 5: 检查最终差异**

Run: `git diff --check` 和 `git status --short`。
