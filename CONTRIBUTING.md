# ✨ 贡献指南 (Contributing to Magical Girl Workshop)

[← 返回主页 (Back to README)](README.md)

感谢你对 **魔法少女工坊** 的关注！作为一个旨在优化 NAS 媒体库体验的开源项目，我们非常欢迎来自社区的改进、建议和 Bug 修复。

由于本项目是一个 **AI 辅助开发 (AI-Augmented Development)** 的实验性项目，我们在接受贡献时会特别关注代码的逻辑清晰度和架构一致性。

## 🛠️ 开发环境配置

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。请确保你的开发环境符合以下要求：

1.  **Python 版本**: `3.12` (项目严格锁定此版本以确保 Nuitka 打包兼容性)。
2.  **安装 uv**:
    ```bash
    pip install uv
    ```
3.  **同步依赖**:
    ```bash
    uv sync
    ```
4.  **准备工具链**:
    确保 `tools/` 目录下有可执行的 `ffmpeg.exe`、`ffprobe.exe` 和 `ab-av1.exe`。建议使用 gyan.dev 的 Full Release 版本。

## 📝 贡献流程

### 1. 报告 Bug
*   在提交 Issue 之前，请先搜索现有的 Issue 列表。
*   请提供详细的复现步骤、显卡型号、驱动版本以及软件日志（GUI 下方的日志窗口内容）。

### 2. 提交功能建议
*   如果你有新的想法（例如支持新的编码器参数或 UI 改进），请先发起一个 Discussion 或 Issue 进行讨论。

### 3. 提交 Pull Request (PR)
*   **分支规范**: 请从 `main` 分支切出你的功能分支（如 `feat/amazing-feature` 或 `fix/bug-name`）。
*   **代码风格**: 本项目使用 `Ruff` 进行 lint 和格式化。在提交前请运行：
    ```bash
    uv run ruff check . --fix
    uv run ruff format .
    ```
*   **UI 规范**: 所有的 UI 组件应尽可能继承自 `qfluentwidgets`，并保持 Win11 Fluent Design 风格。
*   **注释**: 如果你的代码是由 AI 生成或辅助生成的，请在 PR 描述中注明所使用的模型和主要的 Prompt 思路，这有助于我们理解代码逻辑。

## 🏗️ 项目架构简述

*   `main.py`: 程序入口与主窗体逻辑。
*   `workers/`: 包含 FFmpeg 调用、ab-av1 逻辑封装及硬件检测核心。
*   `ui/`: 存放自定义组件与界面布局。
*   `i18n/`: 国际化支持模块，包含翻译加载器。
*   `i18n/locales/`: 存放各语言的翻译文件 (.py)。
*   `tools/`: 存放二进制依赖（不建议直接提交大型二进制文件到仓库）。

## ⚖️ 开源协议

提交贡献即表示你同意你的代码将遵循项目现有的 **GPL-3.0** 协议进行开源。

## 💬 联系方式

如果你在开发过程中遇到困难，可以通过以下方式联系：
*   GitHub Issues
*   Bilibili: 泠萌404 (UID:136850)

---
**"愿魔法与你的代码同在！"**

---

# ✨ Contributing Guide (English)


Thank you for your interest in **Magical Girl Workshop**! As an open-source project aimed at optimizing the NAS media library experience, we welcome improvements, suggestions, and bug fixes from the community.

Since this project is an experimental **AI-Augmented Development** project, we will pay special attention to code logic clarity and architectural consistency when accepting contributions.

## 🛠️ Development Environment Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management. Please ensure your development environment meets the following requirements:

1.  **Python Version**: `3.12` (The project strictly locks this version to ensure Nuitka packaging compatibility).
2.  **Install uv**:
    ```bash
    pip install uv
    ```
3.  **Sync Dependencies**:
    ```bash
    uv sync
    ```
4.  **Prepare Toolchain**:
    Ensure that executable `ffmpeg.exe`, `ffprobe.exe`, and `ab-av1.exe` are present in the `tools/` directory. It is recommended to use the Full Release version from gyan.dev.

## 📝 Contribution Process

### 1. Report Bugs
*   Before submitting an Issue, please search the existing Issue list.
*   Please provide detailed reproduction steps, graphics card model, driver version, and software logs (content of the log window at the bottom of the GUI).

### 2. Submit Feature Suggestions
*   If you have new ideas (such as supporting new encoder parameters or UI improvements), please start a Discussion or Issue for discussion first.

### 3. Submit Pull Request (PR)
*   **Branch Convention**: Please checkout your feature branch from the `main` branch (e.g., `feat/amazing-feature` or `fix/bug-name`).
*   **Code Style**: This project uses `Ruff` for linting and formatting. Before submitting, please run:
    ```bash
    uv run ruff check . --fix
    uv run ruff format .
    ```
*   **UI Guidelines**: All UI components should inherit from `qfluentwidgets` as much as possible and maintain the Win11 Fluent Design style.
*   **Comments**: If your code is generated or assisted by AI, please indicate the model used and the main Prompt ideas in the PR description, which helps us understand the code logic.

## 🏗️ Project Architecture Overview

*   `main.py`: Program entry point and main window logic.
*   `workers/`: Contains FFmpeg calls, ab-av1 logic encapsulation, and hardware detection core.
*   `ui/`: Stores custom components and interface layouts.
*   `i18n/`: Internationalization support module, contains translation loader.
*   `i18n/locales/`: Stores translation files (.py) for each language.
*   `tools/`: Stores binary dependencies (it is not recommended to submit large binary files directly to the repository).

## ⚖️ Open Source License

By submitting a contribution, you agree that your code will be open-sourced under the project's existing **GPL-3.0** license.

## 💬 Contact Information

If you encounter difficulties during development, you can contact us via:
*   GitHub Issues
*   Bilibili: 泠萌404 (UID:136850)

---

**"May magic be with your code!"**
