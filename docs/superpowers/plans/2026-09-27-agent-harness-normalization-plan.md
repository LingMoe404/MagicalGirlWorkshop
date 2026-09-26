# Agent/Harness 规范化实施计划

> 依据 `agent-harness-guide` 的 L1–L6 规范与 checker 实测结果（2026-09-27 审计）。
> 目标：缩小启动上下文、建立真正的验证门、消除文档失真与重复，且**不重构业务代码**。

## Global Constraints

- **只改 agent/harness 表面与测试基建**，不动 `ui/**`、`workers/**` 的业务逻辑（唯一例外见 Task 2，且仅限测试文件的 teardown）。
- **不删除用户数据**：`docs/superpowers/**` 的历史计划、`docs/releases/**`、`tools/*.exe`、`config.ini`、日志、缓存一律保留。
- **测试必须用 `unittest`**：本仓库**没有 pytest**（不在 `pyproject.toml`、不在 `uv.lock`、不在 `.venv`）。任何测试命令必须写 `uv run python -m unittest ...`，**禁止**写 `pytest`。
- **AGENTS.md 的 §8「不要做的事」逐字保留**：那是安全与正确性约束，任何精简都不得删减其条目。
- **所有面向用户的字符串走 `tr()`**；本任务不改 locale 文件，因此无需跑 i18n 校验，但也不得新增硬编码中文 UI 字符串（文档与注释不受此限）。
- **文档语言为简体中文**（与仓库现状一致），命令、路径、字段名、identifier 保留原文。
- 提交信息用中文，格式 `type: 描述`。
- 每个任务结束前必须运行该任务的验证命令并贴出真实输出；**没有新鲜验证输出不得声称完成**。
- 不得运行 `git add .`、不得 force-push、不得重写已推送的历史。
- 不得扩大工具权限、不得修改 `.github/workflows/autobuild.yml` 里的打包步骤逻辑（只许改 `paths-ignore` 触发器）。

## 背景事实（审计实测，实施时以此为准）

| 事实 | 值 |
| --- | --- |
| always-loaded guidance | `AGENTS.md` = 13,884 B / 276 行 |
| 效率软目标 | 8,192 B（checker `oversized-always-loaded`） |
| 强制必读链 | `AGENTS.md:191` → `docs/ROADMAP.md` Phase 1（48,396 B） |
| 全量测试 | 355 tests，**366 秒**（QT 组占 370s，非 QT 组仅 4.1s / 229 tests） |
| 泄漏根因 | 无事件循环时 `deleteLater` 不执行，MainWindow 逐次累积（0.21s→1.16s） |
| 修复验证 | 排空 `DeferredDelete` 后恒定 0.22s（已实测） |
| CI 现状 | `autobuild.yml` 13 步**全是打包**，无 lint、无测试 |
| 客户端表面 | 0（无 `.agents/skills`、无 rules、无 preset） |
| 文档失真 | `AGENTS.md:191` 行数、`:237` 测试缺口陈述、`:58` 的 pytest 命令 |

---

## Task 1: 建立真正的验证门（CI + i18n 只读校验）

**目标**：把"文档里写的命令"变成"CI 里机械执行的门"，并确保新增 workflow 不会触发全量打包。

### 1.1 `autobuild.yml` 的 `paths-ignore` 增加 `.github/**`

文件：`.github/workflows/autobuild.yml`，当前 `on.push.paths-ignore` 为：

```yaml
    paths-ignore:
      # 结界过滤规则：忽略以下微小的魔力扰动（文档变动不引发炼成，节约云端算力）
      - '**.md'
      - '.gitignore'
      - 'LICENSE'
      - 'docs/**'
```

追加一项 `- '.github/**'`（保持既有缩进与注释风格）。理由：否则新增任何 workflow 文件都会触发一次 90 分钟 Nuitka 全量打包并可能产出 Release 资产。

### 1.2 `check_lang.py` 增加 `--check` 只读模式

文件：`check_lang.py`（199 行，已读过）。

现状：`append_missing_keys()`（`:37-105`）在发现缺键时会**直接改写** locale 文件。这对"验证"是危险副作用。

要求：
- 用 `argparse`（标准库）新增 `--check` 开关，**默认行为完全不变**（不加参数时仍然自动补齐，保持向后兼容）。
- `--check` 模式下：检测到缺失键/占位符不匹配时**只报告、不写文件**，并以**非零退出码**结束；全部通过时退出码为 0。
- 实现方式：给 `append_missing_keys` 增加一个 `write: bool = True` 参数（或等价的最小改动），在 `check` 模式下传 `False` 并打印"（--check 模式：跳过自动补齐）"。
- 退出码：`sys.exit(1)` 当存在 `has_error`（在 `--check` 模式下）；默认无参模式保持现有退出行为（当前始终 0）。
- 注释用中文，与文件现有风格一致。
- **不得**改动 `i18n/locales/*.py` 任何内容。

### 1.3 新增 `.github/workflows/verify.yml`

新建文件。要求：

- 触发：`push` 到 `main`、`pull_request`，以及 `workflow_dispatch`。
- runner：`windows-latest`（与现有 CI 一致；测试需要 PySide6 offscreen）。
- 步骤（按序）：
  1. `actions/checkout@v7`
  2. `astral-sh/setup-uv@v7`，`python-version: "3.12"`，`enable-cache: true`
  3. `uv sync --locked`（**注意：不能带 `--no-dev`**，否则 ruff 缺失）
  4. `uv run ruff check .`
  5. `uv run python -m unittest discover -s tests`
  6. `uv run python check_lang.py --check`
- 设置 `env: QT_QPA_PLATFORM: offscreen`（部分测试依赖它；测试文件里用的是 `setdefault`，显式设置更稳）。
- 加 `concurrency` 与现有 `autobuild.yml` 一致的取消策略（`group: ${{ github.workflow }}-${{ github.ref }}`，`cancel-in-progress: true`）。
- `permissions: contents: read`（最小权限，与现有 CI 一致）。
- 注释用中文，风格与 `autobuild.yml` 一致（可用克制、专业的措辞，不必模仿其"炼成阵"风格的夸张度）。
- **不要**加打包、不要加 `uv run ruff format`（main 上 `docs/CODE_AUDIT_2026-07-02.md` 的代码块会被 ruff format 改动，属既有噪音，本任务不引入 format 门）。

### 验证命令

```bash
uv run python check_lang.py --check          # 期望：退出码 0（251 键 × 4 语言当前全绿）
uv run python check_lang.py --check; echo "exit=$?"
uv run python -m unittest tests.test_packaging_config -v   # 现有 CI 断言必须仍通过
git status --short                            # 期望：只有本次改动的 3 个文件
```

---

## Task 2: 修复测试套件的 MainWindow 累积泄漏（366s → ~70s）

**目标**：消除 QT 测试组的时间膨胀，让全量验证从 6 分钟降到 1 分钟级。

### 根因（已实测确认）

`MainWindow` 在 headless 测试里通过 `addCleanup(w.deleteLater)` 释放，但**没有事件循环**时 `deleteLater()` 投递的 `DeferredDelete` 事件永不派发，窗口对象持续存活。下一个 `MainWindow` 构造时会把这些存活的窗口重新纳入父子关系遍历，于是每次构造成本线性上升：

```
win 1: 0.21s  win 2: 0.34s  win 3: 0.48s  win 4: 0.62s  win 5: 0.75s  win 6: 1.02s
```

排空 `DeferredDelete` 后：

```
win 1: 1.30s  win 2: 0.27s  win 3: 0.24s  win 4: 0.22s  win 5: 0.22s  win 6: 0.23s
```

### 要求

构造 `MainWindow` 的测试文件共 6 个：

- `tests/test_main_window_transcode_integration.py`
- `tests/test_main_window_log_integration.py`
- `tests/test_main_window_file_list_integration.py`
- `tests/test_home_ui_builder.py`
- `tests/test_settings_controller.py`
- `tests/test_config_manager.py`

要求：
- 提供一个**共享的清理 helper**，避免 6 处复制粘贴。优先方案：在 `tests/` 下新增一个小模块（例如 `tests/qt_cleanup.py`，或复用 `tests/__init__.py`——后者当前是空文件），暴露形如 `drain_deferred_deletes()` 的函数：

```python
from PySide6.QtCore import QCoreApplication, QEvent

def drain_deferred_deletes():
    """headless 测试无事件循环，deleteLater 投递的 DeferredDelete 永不派发；
    在这里手动排空，避免 MainWindow 实例跨测试累积导致构造成本线性上升。"""
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
```

- 在上述 6 个文件里，把 `self.addCleanup(w.deleteLater)` 改为先 `deleteLater` 再排空（例如 `self.addCleanup(self._cleanup_window, w)` 或直接 `addCleanup` 一个同时做两件事的闭包）。
- **只改测试文件的 teardown，不改任何 `ui/**` 或 `workers/**` 源码**。产品本身有事件循环，`deleteLater` 正常工作；这是 headless 测试的环境特性。
- 若某个文件已有自己的 cleanup 逻辑，保持其现有断言与语义不变，只追加排空动作。

### 验证命令

```bash
# 1. 全量测试仍须全绿，且耗时显著下降（基线 366s）
python -c "import subprocess,time; t=time.time(); r=subprocess.run(['uv','run','python','-m','unittest','discover','-s','tests'],capture_output=True,text=True); print('elapsed',round(time.time()-t,1),'rc=',r.returncode); print([l for l in r.stderr.splitlines() if 'Ran ' in l])"

# 2. 单独跑 3 个最慢的文件，确认不再线性上升
uv run python -m unittest tests.test_main_window_transcode_integration tests.test_main_window_log_integration tests.test_main_window_file_list_integration

# 3. ruff 干净
uv run ruff check .
```

**验收门槛**：全量测试 `rc=0` 且 **355 tests OK 不变**；耗时从 366s 降到 **≤120s**（预期 ~70s）。若耗时未显著下降，说明清理未生效，必须查明原因后再报完成。

---

## Task 3: 新增 `.normalizer.toml` 路由 + 补 `.gitignore` + 修 ROADMAP 计数

**目标**：为 agent 提供机器可读的最小 read set 与定向验证路由，并清理两处低风险项。

### 3.1 新增 `.normalizer.toml`

项目根新增。这是 `project-normalizer` 的原生配置入口（`routing.py` 会读它），用于声明 path → read/verify 路由，**覆盖 checker 的默认推断**（默认推断会给出 `python -m pytest tests`，而本仓库没有 pytest）。

**格式与两个已被实测确认的硬约束**（控制器在临时目录里跑过 `routing.py` 验证，不要凭直觉改）：

1. `path` 支持 glob 与 `dir/**` 前缀匹配；最长字面前缀优先。
2. **`read` 只能写具体文件路径——目录条目会被静默丢弃。** `context_for` 用 `[r for r in route['read'] if r in inv.files]` 过滤，而 `inv.files` 只含常规文件。写成 `["workers/"]` 会得到**空的 read set**。`[scan].exclude` 反过来只接受**目录名或相对路径前缀**，两者语义不同，不要混用。

实测确认的行为（作为编写依据）：

```text
read = ["workers/encoder.py", "tests/test_encoder.py"]   → 两个都保留 ✅
read = ["workers/encoder.py", "workers/"]                → "workers/" 被丢弃，只剩具体文件 ✅（目录条目无效）
[scan] exclude = ["tools", "build"]                      → 两者都进 skipped:private-state-or-generated ✅
[delegation] language = "zh"                             → resolve_language 返回 ('zh', 'configured:zh') ✅
```

写法（`read` 全部用具体文件）：

```toml
[[routes]]
path = "workers/encoder.py"
read = ["workers/encoder.py", "workers/command_builder.py", "tests/test_encoder.py", "tests/test_command_builder.py"]
verify = ["uv run python -m unittest tests.test_encoder tests.test_command_builder"]

[[routes]]
path = "workers/command_builder.py"
read = ["workers/command_builder.py", "config.py", "tests/test_command_builder.py", "tests/test_encoder.py"]
verify = ["uv run python -m unittest tests.test_command_builder tests.test_encoder"]

[[routes]]
path = "workers/**"
read = ["workers/__init__.py", "config.py", "utils.py"]
verify = ["uv run python -m unittest discover -s tests -p 'test_*.py'"]

[[routes]]
path = "ui/**"
read = ["ui/__init__.py", "ui/main_window.py", "config.py"]
verify = ["uv run python -m unittest discover -s tests -p 'test_*.py'"]

[[routes]]
path = "i18n/locales/**"
read = ["i18n/locales/zh_CN.py", "check_lang.py"]
verify = ["uv run python check_lang.py --check"]

[[routes]]
path = "check_lang.py"
read = ["check_lang.py", "i18n/translator.py"]
verify = ["uv run python check_lang.py --check"]

[[routes]]
path = ".github/workflows/**"
read = [".github/workflows/autobuild.yml", "tests/test_packaging_config.py"]
verify = ["uv run python -m unittest tests.test_packaging_config"]

[[routes]]
path = "installer/**"
read = ["installer/MagicalGirlWorkshop.iss", "tests/test_packaging_config.py"]
verify = ["uv run python -m unittest tests.test_packaging_config"]

[[routes]]
path = "tests/**"
read = ["tests/__init__.py"]
verify = ["uv run python -m unittest discover -s tests -p 'test_*.py'"]

[delegation]
language = "zh"

[scan]
exclude = ["tools", "build", "cache", ".ruff_cache", ".superpowers", ".venv"]
```

要点：
- 每条 `read` 里的路径必须**在仓库中真实存在**，否则被静默丢弃；写完后按「验证命令」第 2 条逐条核对实际返回。
- `workers/**` 与 `ui/**` 这两条宽路由的 `read` 故意只放少量**入口文件**（而非全目录），因为这是"最小 read set"——具体到单文件的路由（如 `workers/encoder.py`）优先命中，宽路由只在没有更具体路由时兜底。
- `[delegation] language = "zh"` 固定 preset prompt 语言（本仓库是中文优先项目）。
- 文件需用 UTF-8 **无 BOM**（`tomllib` 要求）；注意 `AGENTS.md` 与 `docs/ROADMAP.md` 是**带 BOM** 的，但新文件不要跟。
- `[scan].exclude` 会减少 inventory 体积（`tools/` 下有 3 个共约 196 MB 的 exe），让 checker 更快且不误报。

### 3.2 `.gitignore` 补 `.env`

在 `# --- 本地配置与运行缓存 ---` 段落内、`config.ini` 附近追加：

```
.env
.env.*
```

checker 报 `gitignore-gap`（探针 `.env`，当前仓库不存在该文件，属预防性）。`.gitignore` 已在 `autobuild.yml` 的 `paths-ignore` 中，改它不会触发打包。

### 3.3 `docs/ROADMAP.md` 修正测试计数

文件 `docs/ROADMAP.md:148` 原文含：

> 302 项 unittest 全绿

实测当前为 **355** 项（`grep -c "def test" tests/*.py` 与 unittest discover 一致）。改为 `355 项 unittest 全绿`。

**只改这一个数字**，不动 ROADMAP 的其余内容（740 行，是历史记录）。

### 验证命令

```bash
# 1. toml 可被标准库解析
uv run python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('.normalizer.toml').read_text(encoding='utf-8')); print('routes:',len(d.get('routes',[]))); print('exclude:',d.get('scan',{}).get('exclude'))"

# 2. checker 能读到路由（不再推断出 pytest）
python "A:/Code/agent-harness-guide/.agents/skills/project-normalizer/scripts/check_project_normalization.py" "A:/Code/MagicalGirlWorkshop" --harness codex --context-for workers/encoder.py --task refactor

# 3. checker 确认 gitignore-gap 消失
python "A:/Code/agent-harness-guide/.agents/skills/project-normalizer/scripts/check_project_normalization.py" "A:/Code/MagicalGirlWorkshop" --harness codex --brief
```

**期望**：第 2 条输出的 `verify` 使用 `uv run python -m unittest ...`（不再是 `python -m pytest`）；第 3 条 findings 里不再出现 `gitignore-gap`。

---

## Task 4: AGENTS.md 精简至 ≤8,192 B 并新增承载 skill

**目标**：把每轮都付的 13,884 B 降到 8,192 B 以内，取消强制必读链，修正三处失真，同时**一条安全约束都不丢**。

### 硬性约束

- **§8「不要做的事」逐字保留**（全部 8 条 ❌ 项）。
- 修正以下三处**已失真陈述**：
  - `:191` "这两个文件分别约 3000 行 / 760 行" → 实测 `ui/main_window.py` = **1,258 行**、`workers/encoder.py` = **1,105 行**。
  - `:237` "当前**无 UI 测试、无 encoder.py 测试、无集成测试**——这是已知缺口" → **已不成立**：现有 8 个 UI 测试文件、`tests/test_encoder.py`（37 方法）、`tests/test_integration.py`。改为反映现状（例如说明"已覆盖，缺口见 ROADMAP"）。
  - `:58` 的 `uv run python -m pytest tests/` → **删除或改为** `uv run python -m unittest discover -s tests`（pytest 未安装，该命令会直接 `ModuleNotFoundError`）。
- **删除 `:191` 对 `docs/ROADMAP.md` 的强制预读**（checker `mandatory-read-fanout` 的根因）。改为"按需查 ROADMAP"的指针，不得表述为开工前必读。
- §2 的打包片段（约 647 B）、§3 架构总览的逐文件清单（约 3,283 B）、§5.3 编码器参数细节（约 637 B）移入 Task 4 新建的 skill，AGENTS.md 中**只留一行指针 + 路由信息**。

### 目标结构（建议，总预算 ≤8,192 B）

| 区块 | 保留内容 | 预算 |
| --- | --- | --- |
| 头部 | 项目一句话 + 技术栈 + 版本指针 | ~300 B |
| 命令 | 环境/运行/lint/测试/i18n/打包**入口**（每条 1 行，细节移到 skill） | ~700 B |
| 架构路由 | **改为 path → 读什么 → 跑什么** 的路由表，取代逐文件描述 | ~1,500 B |
| 约定 | 4.1–4.5 的**硬规则**（3.12 锁定、i18n 走 tr()、Signal 跨线程、long path、配置持久化） | ~1,500 B |
| 陷阱 | 只留"改前必读"的硬约束；细节移 skill | ~1,200 B |
| 测试 | 命令 + unittest 风格 + 不依赖真实 ffmpeg/GPU + 现状覆盖说明 | ~600 B |
| 提交/PR | 保持 | ~700 B |
| §8 不要做的事 | **逐字保留** | ~700 B |
| 文档索引 | 保留，但标注"按需" | ~400 B |

### 4.1 新增 `.agents/skills/mgw-dev-workflow/`

结构：

```
.agents/skills/mgw-dev-workflow/
  SKILL.md                      # 元数据 + 路由正文
  references/architecture.md    # 从 AGENTS.md §3 移出的文件地图 + 关键数据流 + 并发模型
  references/encoder-params.md  # 从 AGENTS.md §5.3 移出；含 QSV/NVENC/AMF 参数差异 + ab-av1 探测说明
  references/packaging.md       # 从 AGENTS.md §2 移出的 Nuitka 打包步骤 + CI 说明
  references/workflows.md       # i18n 改动 / 版本发布 / 发版清单等可复用流程
```

`SKILL.md` 的 frontmatter **必须**含 `name` 与 `description`（`name: mgw-dev-workflow`）。`description` 要短、只写触发条件（例如"在魔法少女工坊仓库修改编码参数、i18n、打包或发版流程时使用"），**不要在 description 里写步骤**（那是正文的事）。

**重要**：`.agents/skills` 是 registry 中 **zcode 与 codex 两个客户端的 canonical skill 根**，因此只维护这一份，不要为其他客户端复制副本（会触发 S1 违规）。

### 验证命令

```bash
# 1. 体积（硬门槛）
python -c "import pathlib; b=pathlib.Path('AGENTS.md').read_bytes(); print('AGENTS.md bytes =', len(b), 'limit 8192'); assert len(b) <= 8192, 'TOO LARGE'"

# 2. 安全约束未丢：§8 的 8 条逐条核对
grep -c "❌" AGENTS.md    # 期望仍为 8

# 3. 失真陈述已修正
grep -n "3000 行\|760 行\|pytest\|无 UI 测试" AGENTS.md || echo "OK: 陈旧陈述已清除"

# 4. 必读链已取消
python "A:/Code/agent-harness-guide/.agents/skills/project-normalizer/scripts/check_project_normalization.py" "A:/Code/MagicalGirlWorkshop" --harness codex --brief

# 5. skill 元数据
python -c "import pathlib; t=pathlib.Path('.agents/skills/mgw-dev-workflow/SKILL.md').read_text(encoding='utf-8'); assert 'name:' in t and 'description:' in t; print('skill frontmatter OK')"

# 6. 内容确实搬走而非丢失
ls -la .agents/skills/mgw-dev-workflow/references/
```

**期望**：第 1 条通过；第 4 条 findings 不再含 `oversized-always-loaded` 与 `mandatory-read-fanout`。

---

## Task 5: 新增 code-reviewer 子代理预设

**目标**：落地 checker 唯一推荐的 preset（D1–D10 全 pass）。

### 文件

新建 `.zcode/agents/code-reviewer.md`。内容用 checker 已渲染的 artifact（已审计，`safe_to_write: true`，未写入）：

```markdown
---
name: code-reviewer
description: "Code Reviewer: review a change for correctness and regressions."
tools: Read, Grep, Glob
generated-by: project-normalizer
schema-version: project-subagent-plan/2
source-role-id: code-reviewer
---
角色
审查改动本身的正确性与回归风险。

范围
只看改动的文件与直接相关的测试。

做什么
找出具体缺陷：逻辑错误、未处理的分支、被改坏的调用方。
只报告可以据以行动的问题。

输出
返回 review-findings：严重级别、路径、原因，以及最小的修复方向。

何时停
改动意图不清楚、或路由的读取集覆盖不到这次改动时，停下来提问。

禁止
不要改文件，不要执行远端命令，不要扩大成无关重构。
```

### 要求

- **权限严格保持 `tools: Read, Grep, Glob`**——不含 `Bash`、不含 `Edit`/`Write`。这是 least privilege，不得扩大。
- 保留 `generated-by` / `schema-version` / `source-role-id` 三个 marker（供 drift 检测；缺 marker 会被判为 human-authored）。
- 不要创建 `.claude/` 或 `.codex/` 下的副本。

### 验证命令

```bash
# D1–D10 逐条
python "A:/Code/agent-harness-guide/.agents/skills/project-normalizer/scripts/check_project_normalization.py" "A:/Code/MagicalGirlWorkshop" --harness zcode --subagents check

# 已安装状态应为 current（不再是 missing）
python "A:/Code/agent-harness-guide/.agents/skills/project-normalizer/scripts/check_project_normalization.py" "A:/Code/MagicalGirlWorkshop" --harness zcode --subagents render
```

**期望**：`passed: true`、`problems: []`；render 输出里 `installed.counts.current = 1`、`missing = 0`。

---

## 收尾验证（全部任务完成后）

```bash
# 1. checker 全量对照（与审计基线 13,884 B 比较）
python "A:/Code/agent-harness-guide/.agents/skills/project-normalizer/scripts/check_project_normalization.py" "A:/Code/MagicalGirlWorkshop" --harness all --brief

# 2. 目标项目自己的验证入口
uv run ruff check .
uv run python -m unittest discover -s tests
uv run python check_lang.py --check

# 3. 工作区确认
git status --short
```

**必须如实报告**：checker 的 `undetermined` 项（G2/S1–S3/C2–C3/V2–V3）**不得**当作 pass；客户端是否真的加载这些文件属 `client_confirmation`，未经实际运行不得声称已验证。
