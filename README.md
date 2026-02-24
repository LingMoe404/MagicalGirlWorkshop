# ✨ 魔法少女工坊 (Magical Girl Workshop) - NAS Edition

![Version](https://img.shields.io/badge/version-1.2.2-FB7299?style=for-the-badge&logo=bilibili&logoColor=white)
![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Platform](https://img.shields.io/badge/OS-Windows11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-green?style=for-the-badge)

[English](README_EN.md) | [日本語](README_JP.md)

> **"NAS 媒体库洗版神器 · Intel & NVIDIA & AMD 三位一体"**
>
> 专为 **NAS 用户** 和 **仓鼠党** 打造的 AV1 硬件转码工具。
> 利用 Intel QSV、NVIDIA NVENC 或 AMD AMF 技术，在保留画质的前提下，将庞大的影视库体积缩小 **30% - 50%**。
> *Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini.*

---

## 📸 界面预览

![软件截图](screenshot.gif)

## 🎯 核心功能

*   **🚀 三核硬件加速**:
    *   **Intel QSV**: 专为 Intel Arc (A380/A750/B580) 及 Core Ultra 核显优化，满血释放 `av1_qsv` 性能。
    *   **NVIDIA NVENC**: 支持 RTX 40 系列显卡 AV1 编码，内置 **AQ (感知画质增强)** 开关，画质更细腻。
    *   **AMD AMF**: **[New]** 新增对 Radeon RX 7000 系列显卡及 RDNA 3 架构核显 (如 Ryzen 8000G) AV1 编码支持。
 *   **🧠 智能码率 (ab-av1)**: 集成 `ab-av1` 算法，根据设定的 VMAF 分数（全平台默认 93）自动测算最佳压制参数，支持 **10-bit** 深度 (AMD 暂限 8-bit)。
*   **📂 批量洗版**: 支持选择整个文件夹，自动扫描视频文件并加入队列。支持断点续传，适合挂机处理 TB 级数据。
*   **🔮 真理之眼**: 拖入视频文件即可快速查看详细媒体信息（编码、流信息、码率等），二次元风格报告。
*   **🛠️ 媒体库友好**:
    *   **音频**: 默认混缩为立体声 (Opus @ 96k + Loudnorm)，**[New]** 自动识别并保留 5.1/7.1 环绕声通道 (Opus Multichannel)。
    *   **字幕**: 智能处理字幕流 (MKV 保留特效字幕，MP4 转 SRT)，确保 Emby/Plex/Jellyfin 兼容性。
    *   **元数据**: 尽可能保留原文件的元数据信息，**[New]** 增强了对 HDR10/HLG 元数据的保留。
*   **📊 预知之眼**: UI 进度条现在不仅能显示百分比，还能实时预估**剩余时间**、**压制速度**与**当前码率**，掌控全局。
*   **🎨 Win11 风格**: 基于 `PySide6` + `QFluentWidgets` 开发，支持云母 (Mica) 特效与深色模式，界面精美。
*   **🔌 贴心辅助**: 支持任务完成后**自动关机**，以及一键清理 ab-av1 产生的临时缓存文件。

## 📊 编码器参数对比

| 特性 / 参数 | Intel QSV (默认) | NVIDIA NVENC | AMD AMF |
| :--- | :--- | :--- | :--- |
| **FFmpeg 编码器** | `av1_qsv` | `av1_nvenc` | `av1_amf` |
| **默认 VMAF 目标** | `93.0` | `93.0` | `93.0` |
| **默认灵力偏移** | `-2` | `-4` | `-6` |
| **质量控制参数** | `-global_quality:v` | `-cq` | `-qvbr_quality_level` |
| **速度预设 (Preset)** | `1` (慢) - `7` (快) | `p7` (慢) - `p1` (快) | `quality` (慢) - `speed` (快) |
| **码率控制模式** | 硬件 ICQ 模式 | `vbr` + `-b:v 0` | `vbr_latency` + QVBR |
| **感知增强 (AQ)** | 默认启用 (Lookahead) | 默认启用 (Spatial/Temporal) | 默认启用 (Pre-Analysis) |
 | **像素格式** | `p010le` (10-bit) | `p010le` (10-bit) | `yuv420p` (8-bit) |
| **特殊优化** | `-async_depth 1` (防溢出) | 解除码率限制 (`-b:v 0`) | 启用 VBAQ 自适应量化 |
| **硬件门槛** | Intel Arc / Core Ultra | NVIDIA RTX 40 系列 | AMD RX 7000 / RDNA 3 |

*注：由于三家算法不同，相同的质量数值（如 30）在不同显卡上的表现不可直接类比，请以 VMAF 结果为准。*
*预设映射：软件界面统一使用 `1` (慢/高质量) - `7` (快/低质量) 的数字。NVIDIA 映射为 `p7`→`p1`；AMD 映射为：`1-2`→`quality`, `3-5`→`balanced`, `6-7`→`speed`。*

## 🧪 VMAF 调优指南

详细的 VMAF 参数说明与画质建议请参阅 [VMAF_GUIDE](docs/VMAF_GUIDE.md)。

## ⚙️ 系统要求

*   **操作系统**: Windows 10 / 11 (推荐 Win11 以获得最佳 UI 体验)
*   **显卡**: **必须** 支持 AV1 硬件编码
    *   🔵 **Intel**: Arc A380 / A750 / B580 等独显，或 Core Ultra 系列核显。
    *   🟢 **NVIDIA**: GeForce RTX 40 系列 (如 RTX 4060 / 4080 / 4090)。
    *   🔴 **AMD**: Radeon RX 7000 系列独显或 RDNA 3 架构核显 (如 Ryzen 8000G)。*(注: 由于需使用 CPU 辅助探测，建议搭配较新 CPU 以获得最佳体验)*
    *   *注意: 旧款 NVIDIA (30系及以下) 及 AMD (RX 6000系及以下) 不支持。*
*   **驱动**: 请安装最新的显卡驱动。

### 🔍 硬件兼容性自测

详细的硬件自测方法请参阅 [HARDWARE_CHECK](docs/HARDWARE_CHECK.md)。

## 📥 下载与使用

### 方式一：下载正式版 (推荐)

1.  前往 [**Releases 页面**](https://github.com/LingMoe404/MagicalGirlWorkshop/releases) 下载最新版本的压缩包。
2.  解压至任意目录。
3.  双击 `MagicalGirlWorkshop.exe` 即可直接使用 (已内置 FFmpeg, ab-av1 等核心组件，无需额外配置)。

### 方式二：源码运行 (Dev)

如果您熟悉 Python 开发，可以使用源码运行：

1.  **克隆仓库**
    ```bash
    git clone https://github.com/LingMoe404/MagicalGirlWorkshop.git
    cd MagicalGirlWorkshop
    ```

2.  **安装依赖**
    本项目推荐使用 `uv` 进行依赖管理 (根目录已包含 `uv.lock`)。
    ```bash
    # 安装 uv
    pip install uv
    # 同步环境
    uv sync
    ```
    *或者使用 pip 安装核心库: `pip install PySide6 PySide6-Fluent-Widgets`*

3.  **准备工具链**
    请确保项目根目录下的 `tools/` 文件夹内包含以下可执行文件：
    *   `ffmpeg.exe` & `ffprobe.exe`: **注意**：仓库源码中上传的是 `essentials` 版本，缺少部分编码支持。建议前往 gyan.dev 下载 `ffmpeg-release-full.7z` (Full 版本) 并替换。*(注：下载的正式版 Releases 压缩包已内置 Full 版本，无需额外操作)*
    *   `ab-av1.exe`

4.  **启动**
    ```bash
    # 使用 uv
    uv run main.py
    
    # 或标准 python
    python main.py
    ```

---

## 🚀 更新日志

详细更新日志请参阅 [CHANGELOG](CHANGELOG.md)。

## 🛠️ 常见问题

常见问题解答及 NAS 用户建议请参阅 [FAQ](docs/FAQ.md)。

## 🔗 关于作者

我是 **泠萌404**，一名喜欢折腾硬件、NAS的普通上班族。

| 平台 | ID / 频道 | 链接 |
| :--- | :--- | :--- |
| Bilibili | **泠萌404** | [点击跳转](https://space.bilibili.com/136850) |
| YouTube | **泠萌404** | [点击跳转](https://www.youtube.com/@LingMoe404) |
| Douyin | **泠萌404** | [点击跳转](https://www.douyin.com/user/MS4wLjABAAAA8fYebaVF2xlczanlTvT-bVoRxLqNjp5Tr01pV8wM88Q) |

## 🙏 致谢

本项目离不开以下优秀的开源项目与工具的支持：

*   [**FFmpeg**](https://ffmpeg.org/): 强大的多媒体处理框架。
*   [**ab-av1**](https://github.com/alexheretic/ab-av1): 自动寻找最佳 AV1 编码参数的工具。
*   [**PySide6**](https://doc.qt.io/qtforpython/): Python 的 Qt 绑定。
*   [**QFluentWidgets**](https://github.com/zhiyiYo/PyQt-Fluent-Widgets): 精美的 Fluent Design 风格组件库。
*   [**Google Gemini**](https://deepmind.google/technologies/gemini/): 提供了强大的代码生成与辅助能力。

## 🤖 开发幕后

本项目是一个纯粹的 **AI 辅助开发** 实验。
**100% 的代码** 均由 **Google Gemini** 在我的 Prompt 引导下生成。
我负责提供逻辑架构和需求，AI 负责编写 Python 代码和 UI 实现。

## 🤝 贡献指南 (Contributing)

欢迎各位适格者参与到魔法少女工坊的建设中！无论是修复 Bug、优化文档还是提交新功能，我们都非常感谢。

详细贡献流程与开发规范请参阅 [CONTRIBUTING](CONTRIBUTING.md)。

## 📜 开源协议

本项目遵循 GPL-3.0 开源协议。

*   **GUI**: 基于 PySide6 和 QFluentWidgets (GPLv3)。
*   **Core**: 核心算法基于 FFmpeg (LGPL/GPL) 和 ab-av1 (MIT)。
*   **License**: MagicalGirlWorkshop by 泠萌404 is licensed under GPL-3.0.

Copyright © 2026 泠萌404