# AI Collaboration Credit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 统一项目的 AI 协作署名，准确体现作者主导及 Codex、GPT、Antigravity、Gemini 的参与。

**Architecture:** 不新增运行逻辑，只更新现有翻译字典、界面默认文本和 README 文案。所有语言保留相同语义，历史发布记录不修改。

**Tech Stack:** Markdown、Python 翻译字典、PySide6 界面文本

---

### Task 1: 更新软件内署名

**Files:**
- Modify: `ui/main_window.py`
- Modify: `i18n/locales/zh_CN.py`
- Modify: `i18n/locales/zh_TW.py`
- Modify: `i18n/locales/en_US.py`
- Modify: `i18n/locales/ja_JP.py`

- [ ] 将主界面页脚改为作者署名、技术栈和 AI 协作短版。
- [ ] 将致谢页脚统一为 Codex、GPT、Antigravity 与 Gemini。
- [ ] 运行 `uv run python check_lang.py`，预期四种语言键完全一致。

### Task 2: 更新 README

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `README_JP.md`

- [ ] 将 Gemini 单独徽章改为多模型 AI 协作徽章。
- [ ] 更新简介中的 Powered by 文本。
- [ ] 在致谢和开发幕后中说明作者主导及多 AI 协作，删除“100% Gemini 生成”。

### Task 3: 验证

- [ ] 搜索当前项目中的旧 Gemini 独占描述，确认仅历史发布记录保留。
- [ ] 运行语言一致性检查。
- [ ] 离屏初始化主窗口，确认页脚文本包含四个协作名称。
