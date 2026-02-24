v1.0.0 - ✨ 魔法少女工坊 (Magical Girl Workshop) v1.0.0 - 始动 (Genesis) | Intel Arc AV1 专属洗版神器

> **"以 Intel QSV 之名，重塑影像的绝对领域！"**

经过无数个夜晚的炼成与调试，**魔法少女工坊 (Magical Girl Workshop)** 的初号机终于正式与各位适格者见面了！这是一个专为 **NAS 仓鼠党** 和 **画质强迫症** 打造的 AV1 硬件转码工具，旨在利用 Intel Arc/Ultra 显卡的强大算力，将庞大的影视库体积“净化”缩减 30%-50%，同时保留肉眼无损的画质。

## 🎉 核心术式 (Highlights)

*   **🚀 Intel QSV 极速咏唱**: 深度适配 **Intel Arc (A380/A750/B580)** 独显及 **Core Ultra (如 265T)** 核显，满血释放 `av1_qsv` 硬件编码性能。
*   **🧠 智能魔力推演 (Smart VMAF)**: 内置 `ab-av1` 算法，拒绝盲猜码率！根据设定的 VMAF 分数（默认 93）自动测算最佳压制参数 (ICQ)，实现画质与体积的完美平衡。
*   **🎨 幻想风格 UI**: 基于 `PyQt-Fluent-Widgets` 打造的 Win11 风格界面，支持云母 (Mica) 特效与深色模式，让转码也能赏心悦目。
*   **🔮 真理之眼 (True Eye)**: 拖入视频即可触发详细物质分析，快速查看编码、流信息与元数据。
*   **🎧 NAS 兼容性优化**: 
    *   音频强制混缩为立体声 (Opus @ 96k + Loudnorm)，完美适配移动端与电视外放。
    *   智能字幕处理（MP4 转 SRT，MKV 保留特效），确保 Emby/Plex/Jellyfin 丝滑播放。

## 🛠️ 功能特性 (Features)

*   [x] **批量净化**: 支持文件夹拖拽与递归扫描，自动过滤非视频文件。
*   [x] **断点续传**: 遇到错误自动跳过，支持任务队列管理。
*   [x] **贴心辅助**: 支持任务完成后**自动关机**，以及一键清理临时缓存残渣。
*   [x] **环境自检**: 启动时自动检测 FFmpeg/ab-av1 组件及硬件兼容性，并输出二次元风格日志。

## ⚙️ 适格者要求 (Requirements)

*   **OS**: Windows 10 / 11 (推荐 Win11)
*   **GPU**: **必须** 是支持 AV1 硬件编码的 Intel 显卡
    *   Intel Arc A380 / A750 / A770 / B580 等 (独显)
    *   Intel Core Ultra 系列 (核显)
    *   *❌ 暂不支持 NVIDIA / AMD 显卡*
*   **Driver**: 请确保安装了最新的 Intel 显卡驱动。

## 📥 部署指南 (Installation)

1.  下载下方的 `MagicalGirlWorkshop_Lite_v1.0.0_Portable.zip`。
2.  解压至任意目录。
3.  **重要**：请自行下载以下圣遗物（组件）并放入软件根目录：
    *   `ffmpeg.exe` & `ffprobe.exe` (推荐 gyan.dev 的 release-full 版本)
    *   `ab-av1.exe` (从 ab-av1 release 页面下载并重命名)
4.  双击 `MagicalGirlWorkshop.exe` 启动仪式。

## 🤖 致谢 (Credits)

*   Code & Logic by **Google Gemini** (AI Assisted)
*   UI powered by **PyQt-Fluent-Widgets**
*   Core powered by **FFmpeg** & **ab-av1**

---
*“契约已成，开始你的炼成仪式吧！”*
