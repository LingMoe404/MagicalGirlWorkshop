# 🛠️ 常见问题 & NAS 指南 (FAQ & NAS Tips)

[← 返回主页 (Back to README)](../README.md)

## ❓ 常见问题 (FAQ)

**Q: 为什么启动时提示“结界破损警告”？**
A: 说明程序目录下的 `tools/` 文件夹内缺少 `ffmpeg.exe`、`ffprobe.exe` 或 `ab-av1.exe`。请确保这些工具存在于 `tools/` 目录中。

**Q: 为什么部分视频转码失败？**
A: 源码仓库中有单文件体积限制，上传的 `ffmpeg.exe` 为 `essentials` 版本，可能缺少部分非主流编码格式的支持。建议前往 gyan.dev 下载 `ffmpeg-release-full.7z` (Full 版本) 并替换 `tools/` 目录下的文件。*(注：Releases 发布页下载的正式版已内置 Full 版本)*

**Q: 为什么点击开始后直接报错/闪退？**
A: 请检查您的显卡是否支持 AV1 硬件编码。
   - **Intel**: 需要 Arc A380/A750/B580 或 Core Ultra 核显。
   - **NVIDIA**: 需要 RTX 40 系列 (如 4060/4080/4090)。
   - **AMD**: 需要 Radeon RX 7000 系列或 RDNA 3 架构核显。

**Q: 为什么 AMD 模式下显示 "CPU 探测"？**
A: 由于核心组件 `ab-av1` 目前尚未原生支持 AMD AMF 硬件编码器。为了实现自动码率控制，程序会使用 CPU (SVT-AV1 -> AOM-AV1) 进行“代理探测”，然后通过算法将结果换算为 AMF 所需的参数。虽然探测阶段会占用 CPU，但最终的转码过程依然是纯硬件加速的。

**Q: 转换后的 MKV 字幕显示不正常？**
A: 程序会自动判断：如果是 MP4 源文件，字幕会转为 SRT 以兼容 MKV；如果是 MKV 源文件，则保留原始字幕（如 ASS 特效）。

**Q: 支持 HDR 或杜比视界 (Dolby Vision) 吗？**
A: ⚠️ **警告**：目前版本暂不建议压制 HDR 或杜比视界内容。虽然已包含基础元数据保留逻辑，但在某些情况下仍可能导致色调映射错误（画面发灰）或元数据丢失。建议仅用于 SDR (标准动态范围) 视频。

## 💡 给 NAS 用户的建议

*   **路径映射**: 为了获得最佳稳定性，建议将 NAS 的共享文件夹映射为本地磁盘（例如映射为 `Z:` 盘），然后再拖入软件处理，避免使用 `\\192.168.x.x` 路径。
*   **虚拟机直通或 SR-IOV**: 如果您是在宿主机系统下的 Windows 虚拟机中使用，请确保显卡已正确直通 (Passthrough) 或 SR-IOV 虚拟，并安装了最新的显卡驱动 (Intel/NVIDIA/AMD)。
*   **原始文件**: 软件默认开启“覆盖源文件”模式，但对于珍贵的原盘资源，建议先开启“另存为”模式测试效果。

---

# 🛠️ FAQ & NAS Tips (English)

← Back to README

## ❓ Frequently Asked Questions (FAQ)

**Q: Why do I get a "Barrier Breach Warning" on startup?**
A: This indicates that `ffmpeg.exe`, `ffprobe.exe`, or `ab-av1.exe` are missing from the `tools/` folder in the program directory. Please ensure these tools exist in the `tools/` directory.

**Q: Why do some video transcodes fail?**
A: The source code repository has a single file size limit, so the uploaded `ffmpeg.exe` is the `essentials` version, which may lack support for some non-mainstream encoding formats. It is recommended to download `ffmpeg-release-full.7z` (Full version) from gyan.dev and replace the files in the `tools/` directory. *(Note: The official version downloaded from the Releases page already has the Full version built-in)*

**Q: Why does it crash/close immediately after clicking start?**
A: Please check if your graphics card supports AV1 hardware encoding.
   - **Intel**: Requires Arc A380/A750/B580 or Core Ultra iGPU.
   - **NVIDIA**: Requires RTX 40 series (e.g., 4060/4080/4090).
   - **AMD**: Requires Radeon RX 7000 series or RDNA 3 architecture iGPU.

**Q: Why does it show "CPU Probing" in AMD mode?**
A: Because the core component `ab-av1` does not yet natively support the AMD AMF hardware encoder. To achieve automatic bitrate control, the program uses the CPU (SVT-AV1 -> AOM-AV1) for "proxy probing" and then converts the results into parameters required by AMF via an algorithm. Although the probing phase consumes CPU, the final transcoding process is still purely hardware accelerated.

**Q: Subtitles in the converted MKV are not displaying correctly?**
A: The program automatically judges: if the source file is MP4, subtitles are converted to SRT to be compatible with MKV; if the source file is MKV, original subtitles (such as ASS effects) are retained.

**Q: Is HDR or Dolby Vision supported?**
A: ⚠️ **Warning**: It is currently not recommended to encode HDR or Dolby Vision content with this version. Although basic metadata retention logic is included, in some cases it may still lead to tone mapping errors (washed out colors) or metadata loss. It is recommended for use with SDR (Standard Dynamic Range) videos only.

## 💡 Tips for NAS Users

*   **Path Mapping**: For best stability, it is recommended to map the NAS shared folder as a local disk (e.g., map as `Z:` drive) and then drag it into the software for processing, avoiding the use of `\\192.168.x.x` paths.
*   **VM Passthrough or SR-IOV**: If you are using it in a Windows virtual machine under a host system, please ensure that the graphics card is correctly passed through (Passthrough) or virtualized via SR-IOV, and the latest graphics driver (Intel/NVIDIA/AMD) is installed.
*   **Original Files**: The software enables "Overwrite Source File" mode by default, but for precious original resources, it is recommended to enable "Save As" mode first to test the effect.