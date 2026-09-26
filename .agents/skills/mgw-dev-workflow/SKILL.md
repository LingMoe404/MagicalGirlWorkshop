---
name: mgw-dev-workflow
description: 当在魔法少女工坊仓库修改编码参数、i18n 文案、打包脚本或执行发版流程时使用。
---

# mgw-dev-workflow

魔法少女工坊（MagicalGirlWorkshop）的按需参考资料：文件地图、QSV/NVENC/AMF 参数差异、
Nuitka 打包与可复用流程。这些内容原先塞在每轮都加载的 `AGENTS.md` 里，已移到这里，
只有相关任务才需要支付。

**硬性约束以仓库根目录 `AGENTS.md` 为准**（§4 编码约定、§5 陷阱、§8 不要做的事）：
i18n 走 `tr()`、四个 locale 同步、worker 只用 `Signal` 跨线程、`creationflags=get_subprocess_flags()`、
`to_long_path()`、不得绕过 `find_output_conflicts`、提交前 ruff + unittest + `check_lang.py`。
本 skill 只补充细节，不替代这些规则。

## 参考路由

| 需要了解 | 打开 |
| --- | --- |
| 文件地图、关键数据流、并发模型、缓存与输出隔离、进度映射、错误降级顺序 | `references/architecture.md` |
| QSV / NVENC / AMF 参数差异、预设映射、ab-av1 探测策略、三阶段重试 | `references/encoder-params.md` |
| Nuitka 本地复现命令、CI autobuild / verify 工作流、打包约束 | `references/packaging.md` |
| i18n 改动、版本发布、编码参数改动的逐步流程 | `references/workflows.md` |

## 常用入口

```bash
uv sync                                   # 安装依赖（CI/打包用 uv sync --no-dev）
uv run python main.py                     # 运行（需 tools/ 下 ffmpeg/ffprobe/ab-av1）
uv run ruff check . --fix && uv run ruff format .   # 提交前必须
uv run python -m unittest discover -s tests -v      # 唯一测试入口（无第三方测试框架）
uv run python check_lang.py --check       # locale 改动后必跑（只读模式）
```

打包为 Nuitka standalone + 7z 便携版 + Inno Setup 安装版，完整命令见 `references/packaging.md`。
`README.md` 的“编码器参数对比”表是面向用户的参数速查；改参数时必须同步核对。
