v1.1.0 - ✨ 魔法少女工坊 (Magical Girl Workshop) v1.1.0 - 降临 (Advent) | Intel & NVIDIA 双核 AV1 炼成

> **"双核驱动，魔力倍增！NVIDIA RTX 40 系列适格者，参上！"**

随着魔力回路的重构，**魔法少女工坊 (Magical Girl Workshop) v1.1.0** 正式解除了对 NVIDIA 显卡的封印！现在，不仅是 Intel Arc/Ultra 用户，手持 **RTX 40 系列** 显卡的仓鼠党们也能加入这场 AV1 洗版盛宴。我们引入了全新的 **感知增强 (AQ)** 术式，让 N 卡压制画质更上一层楼。

## 🎉 版本亮点 (Highlights)

*   **🟢 NVIDIA NVENC 强力支援**: 新增对 **RTX 40 系列** (如 4060/4080/4090) 的原生支持。
*   **👁️ 感知画质增强 (AQ)**: 针对 N 卡引入 `Spatial AQ` (空间自适应量化) 与 `Temporal AQ` (时间自适应量化) 开关，配合 VBR 模式解除码率上限，大幅提升视觉观感。
*   **🧠 智能双核调优**:
    *   **Intel 模式**: 默认 VMAF 93，追求极致平衡。
    *   **NVIDIA 模式**: 默认 VMAF 95，追求极致画质。
    *   程序会自动根据选择的显卡切换最佳默认值。
*   **🛡️ 结界稳定性提升**: 重写了硬件自检逻辑，现在能精准识别驱动问题、硬件不支持或组件缺失，并给出二次元风格的详细诊断日志。

## 🚀 更新日志 (Changelog)

*   [New] **新增编码器选择**: 界面增加 "Intel QSV" / "NVIDIA NVENC" 切换下拉框。
*   [New] **NVIDIA 专属优化**: 修复 `ab-av1` 与 NVENC 的参数兼容性 (Pixel Format)，解决画质劣化问题。
*   [New] **AQ 开关**: 设置面板新增 "NVIDIA 感知增强" 开关。
*   [Fix] **日志增强**: `ab-av1` 探测阶段现在会实时显示每一轮的 VMAF 分数，让你心里有底。
*   [Fix] **单文件支持**: 修复了无法直接拖入或粘贴单个视频文件路径的问题。
*   [Fix] **进程清理**: 优化了退出逻辑，关闭窗口时会自动追杀残留的 FFmpeg 进程。

## ⚙️ 适格者要求 (Requirements)

*   **OS**: Windows 10 / 11 (推荐 Win11)
*   **GPU (二选一)**:
    *   🟢 **Intel**: Arc A380 / A750 / B580 等独显，或 Core Ultra 核显。
    *   🟢 **NVIDIA**: GeForce RTX 40 系列 (需支持 AV1 编码)。
    *   *❌ 暂不支持 AMD 显卡及旧款 NVIDIA (30系及以下)*
*   **Driver**: 请务必安装最新的显卡驱动！

## 📥 部署指南 (Installation)

*   **小白/懒人**: 请下载 `MagicalGirlWorkshop_v1.1.0_Full.zip` 解压即用，已内嵌所有工具。
*   **老手/网速慢**: 请下载 `MagicalGirlWorkshop_v1.1.0_Lite.zip` 解压后需手动放入 `ffmpeg.exe`, `ffprobe.exe`, `ab-av1.exe`。

> **注意**: 首次启动建议运行一次“真理之眼”或查看日志，确认显卡驱动已正确识别。

---
*“无论是蓝厂还是绿厂的信徒，此刻都汇聚于此吧！”*