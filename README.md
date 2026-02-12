# ✨ 魔法少女工坊 (Magic Workshop) - NAS Edition

![Version](https://img.shields.io/badge/version-1.1.0-FB7299?style=for-the-badge&logo=bilibili&logoColor=white)
![Built with Gemini](https://img.shields.io/badge/Built%20with-Gemini-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Platform](https://img.shields.io/badge/OS-Windows11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-green?style=for-the-badge)

> **"NAS 媒体库洗版神器 · Intel Arc & NVIDIA RTX 40 系列专用"**
>
> 专为 **NAS 用户** 和 **仓鼠党** 打造的 AV1 硬件转码工具。
> 利用 Intel QSV 或 NVIDIA NVENC 技术，在保留画质的前提下，将庞大的影视库体积缩小 **30% - 50%**。
> *Powered by Python, PyQt6, QFluentWidgets, FFmpeg, ab-av1, Gemini.*

---

## 📸 界面预览

![软件截图](screenshot1.jpg)
![软件截图](screenshot2.jpg)

## 🎯 核心功能

*   **🚀 双核硬件加速**:
    *   **Intel QSV**: 专为 Intel Arc (A380/A750/B580) 及 Core Ultra 核显优化，满血释放 `av1_qsv` 性能。
    *   **NVIDIA NVENC**: **[New]** 支持 RTX 40 系列显卡 AV1 编码，内置 **AQ (感知画质增强)** 开关，画质更细腻。
*   **🧠 智能码率 (ab-av1)**: 集成 `ab-av1` 算法，根据设定的 VMAF 分数（Intel 默认 93 / NVIDIA 默认 95）自动测算最佳压制参数，支持 **10-bit** 深度。
*   **📂 批量洗版**: 支持选择整个文件夹，自动扫描视频文件并加入队列。支持断点续传，适合挂机处理 TB 级数据。
*   **🔮 真理之眼**: 拖入视频文件即可快速查看详细媒体信息（编码、流信息、码率等），二次元风格报告。
*   **🛠️ 媒体库友好**:
    *   **音频**: 强制混缩为立体声 (Opus @ 96k + Loudnorm)，适合移动端/平板/电视外放。*(注：暂不支持保留 5.1/7.1 环绕声)*
    *   **字幕**: 智能处理字幕流 (MKV 保留特效字幕，MP4 转 SRT)，确保 Emby/Plex/Jellyfin 兼容性。
    *   **元数据**: 尽可能保留原文件的元数据信息。
*   **🎨 Win11 风格**: 基于 `PyQt6-Fluent-Widgets` 开发，支持云母 (Mica) 特效与深色模式，界面精美。
*   **🔌 贴心辅助**: 支持任务完成后**自动关机**，以及一键清理 ab-av1 产生的临时缓存文件。

## 📊 编码器参数对比

| 特性 / 参数 | Intel QSV (默认) | NVIDIA NVENC |
| :--- | :--- | :--- |
| **FFmpeg 编码器** | `av1_qsv` | `av1_nvenc` |
| **默认 VMAF 目标** | `93.0` | `95.0` |
| **质量控制参数** | `-global_quality:v` | `-cq` |
| **速度预设 (Preset)** | `1` (慢) - `7` (快) | `p1` (慢) - `p7` (快) |
| **码率控制模式** | 硬件 ICQ 模式 | `vbr` + `-b:v 0` (解除上限) |
| **感知增强 (AQ)** | 不支持 | 支持 (Spatial/Temporal AQ) |
| **像素格式** | `p010le` (10-bit) | `p010le` (10-bit) |
| **特殊优化** | `-async_depth 1` (防溢出) | 自动开启感知增强开关 |
| **硬件门槛** | Intel Arc / Core Ultra | NVIDIA RTX 40 系列 |

*注：由于两家算法不同，相同的质量数值（如 30）在不同显卡上的表现不可直接类比，请以 VMAF 结果为准。*

## 🧪 VMAF 调优指南

本工具通过 `ab-av1` 自动寻找最佳 ICQ 码率。VMAF 是衡量画质的关键指标：
*   **VMAF 95+ (极高画质)**: 适合 4K HDR 收藏，画质几乎等同于原盘，体积缩减约 20-30%。
*   **VMAF 93 (推荐平衡)**: **默认设置**。肉眼无损的黄金分割点，体积缩减可达 40-60%。
*   **VMAF 90 (高压缩比)**: 适合在平板或手机上观看，在保持良好观感的前提下极大节省空间。
*   **VMAF < 85**: 可能会出现可见的压缩伪影，不建议用于长期收藏。

## ⚙️ 系统要求

*   **操作系统**: Windows 10 / 11 (推荐 Win11 以获得最佳 UI 体验)
*   **显卡**: **必须** 支持 AV1 硬件编码
    *   🟢 **Intel**: Arc A380 / A750 / B580 等独显，或 Core Ultra 系列核显。
    *   🟢 **NVIDIA**: GeForce RTX 40 系列 (如 RTX 4060 / 4080 / 4090)。
    *   *注意: AMD 显卡及旧款 NVIDIA (30系及以下) 暂不支持。*
*   **驱动**: 请安装最新的显卡驱动。

### 🔍 硬件兼容性自测
程序启动时会自动检测环境（真实初始化硬件）。

**软件内状态 (GUI Log):**
*   **✅ 通过**: `>>> 适格者认证通过： [Intel QSV] [NVIDIA NVENC] (Ready)` (根据实际硬件显示)
*   **❌ 失败**: `>>> 警告：未侦测到有效的 AV1 硬件编码器...`

**手动确认 (Terminal):**
如果您想手动确认，请在终端执行对应显卡的检测命令：

**Intel QSV:**
```bash
.\ffmpeg.exe -init_hw_device qsv=hw -f lavfi -i color=black:s=1280x720 -pix_fmt p010le -c:v av1_qsv -frames:v 1 -f null - -v error
```
**NVIDIA NVENC:**
```bash
.\ffmpeg.exe -f lavfi -i color=black:s=1280x720 -pix_fmt p010le -c:v av1_nvenc -frames:v 1 -f null - -v error
```
*   **无输出**: 恭喜！您的硬件完美支持 QSV or NVENC AV1 硬件编码。
*   **有输出 (报错)**: 说明您的显卡不支持 QSV or NVENC AV1 或驱动未正确安装。

## 📥 下载与使用

---

## 🚀 更新日志

*   **v1.1.0 (2026-02-13)**
    *   💡 **新增 NVIDIA NVENC AV1 硬件编码支持** (需 RTX 40 系列)。
    *   ⚙️ 优化硬件检测逻辑，区分显卡型号和驱动问题。
    *   🚀 修复 `ab-av1` 参数兼容性问题，大幅提升 NVENC 压制画质 (开启 AQ 感知增强)。
    *   📝 增加日志 VMAF 实时显示，NVENC 感知增强开关，以及 VMAF 默认值智能切换。

*   **v1.0.0 (2026-01-28)**
    *   🎉 首次发布！支持 Intel QSV AV1 硬件编码。
    *   ✨ 集成 `ab-av1` 智能 VMAF 码率控制。
    *   🎨 Win11 Fluent Design 风格界面。

---

### 方式一：下载全能版 (懒人推荐)

1.  前往 Releases 页面下载 `MagicWorkshop_v1.1.0_Full.zip`。
2.  解压至任意目录。
3.  双击 `魔法少女工坊.exe` 即可直接使用 (已内置所有核心组件)。

### 方式二：下载纯净版 (Lite)

如果您已有 FFmpeg 或网速较慢：
1.  下载 `MagicWorkshop_v1.1.0_Lite.zip`。
2.  解压后，需**手动下载**以下组件并放入软件根目录：
    ```text
    MagicWorkshop/
    ├── 魔法少女工坊_Lite.exe
    ├── ffmpeg.exe       <-- 必须存在
    ├── ffprobe.exe      <-- 必须存在
    └── ab-av1.exe       <-- 必须存在
    ```
3.  双击 `魔法少女工坊_Lite.exe` 启动。

### 方式二：源码运行

如果您想自行修改或学习代码：

1.  **克隆仓库**
    ```bash
    git clone https://github.com/LingMoe404/MagicWorkshop.git
    cd MagicWorkshop
    ```

2.  **安装依赖**
    ```bash
    pip install PyQt6 PyQt6-Fluent-Widgets
    ```

3.  **准备核心组件**
    *   下载 FFmpeg & FFprobe (https://www.gyan.dev/ffmpeg/builds) (推荐 `ffmpeg-release-full.7z`)
    *   下载 ab-av1 (https://github.com/alexheretic/ab-av1/releases) (请下载 Windows 版本并重命名为 `ab-av1.exe`)
    *   将 `ffmpeg.exe`, `ffprobe.exe`, `ab-av1.exe` 放入项目根目录。

4.  **运行**
    ```bash
    python main.py
    ```

## 🛠️ 常见问题

**Q: 为什么启动时提示“结界破损警告”？**
A: 说明程序目录下缺少 `ffmpeg.exe`、`ffprobe.exe` 或 `ab-av1.exe`。请下载这些工具并和 exe 放在一起。

**Q: 为什么点击开始后直接报错/闪退？**
A: 请检查您的显卡是否支持 AV1 硬件编码。
   - **Intel**: 需要 Arc A380/A750/B580 或 Core Ultra 核显。
   - **NVIDIA**: 需要 RTX 40 系列 (如 4060/4080/4090)。
   - **AMD**: 暂不支持。

**Q: 转换后的 MKV 字幕显示不正常？**
A: 程序会自动判断：如果是 MP4 源文件，字幕会转为 SRT 以兼容 MKV；如果是 MKV 源文件，则保留原始字幕（如 ASS 特效）。

## 💡 给 NAS 用户的建议

*   **路径映射**: 为了获得最佳稳定性，建议将 NAS 的共享文件夹映射为本地磁盘（例如映射为 `Z:` 盘），然后再拖入软件处理，避免使用 `\\192.168.x.x` 路径。
*   **虚拟机直通或 SR-IOV**: 如果您是在宿主机系统下的 Windows 虚拟机中使用，请确保显卡已正确直通 (Passthrough) 或 SR-IOV 虚拟，并安装了最新的显卡驱动 (Intel/NVIDIA)。
*   **原始文件**: 软件默认开启“覆盖源文件”模式，但对于珍贵的原盘资源，建议先开启“另存为”模式测试效果。

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
*   [**PyQt6**](https://www.riverbankcomputing.com/software/pyqt/): Python 的 Qt 绑定。
*   [**PyQt-Fluent-Widgets**](https://github.com/zhiyiYo/PyQt-Fluent-Widgets): 精美的 Fluent Design 风格组件库。
*   [**Google Gemini**](https://deepmind.google/technologies/gemini/): 提供了强大的代码生成与辅助能力。

## 🤖 开发幕后

本项目是一个纯粹的 **AI 辅助开发** 实验。
**100% 的代码** 均由 **Google Gemini** 在我的 Prompt 引导下生成。
我负责提供逻辑架构和需求，AI 负责编写 Python 代码和 UI 实现。

## 📜 开源协议

本项目遵循 GPL-3.0 开源协议。

*   **GUI**: 基于 PyQt6 和 QFluentWidgets (GPLv3)。
*   **Core**: 核心算法基于 FFmpeg (LGPL/GPL) 和 ab-av1 (MIT)。
*   **License**: MagicWorkshop by 泠萌404 is licensed under GPL-3.0.

Copyright © 2026 泠萌404
