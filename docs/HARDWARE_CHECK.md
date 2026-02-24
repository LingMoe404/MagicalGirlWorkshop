# 🔍 硬件兼容性自测 (Hardware Compatibility Check)

[← 返回主页 (Back to README)](../README.md)

程序启动时会自动检测环境（真实初始化硬件）。

## 软件内状态 (GUI Log)

*   **✅ 通过**: `>>> 适格者认证通过： [Intel QSV] [NVIDIA NVENC] [AMD AMF] (Ready)` (根据实际硬件显示)
*   **❌ 失败**: `>>> 警告：未侦测到有效的 AV1 硬件编码器...`

## 手动确认 (Terminal)

如果您想手动确认，请在终端执行对应显卡的检测命令：

### Intel QSV
```bash
.\tools\ffmpeg.exe -init_hw_device qsv=hw -f lavfi -i color=black:s=1280x720 -pix_fmt p010le -c:v av1_qsv -frames:v 1 -f null - -v error
```

### NVIDIA NVENC
```bash
.\tools\ffmpeg.exe -f lavfi -i color=black:s=1280x720 -pix_fmt p010le -c:v av1_nvenc -frames:v 1 -f null - -v error
```

### AMD AMF
```bash
.\tools\ffmpeg.exe -f lavfi -i color=black:s=1280x720 -pix_fmt yuv420p -c:v av1_amf -usage transcoding -quality balanced -rc vbr_latency -qvbr_quality_level 30 -frames:v 1 -f null - -v error
```

*   **无输出**: 恭喜！您的硬件完美支持 QSV, NVENC 或 AMF AV1 硬件编码。
*   **有输出 (报错)**: 说明您的显卡不支持对应的硬件编码器或驱动未正确安装。

---

# 🔍 Hardware Compatibility Check (English)

← Back to README

The program automatically detects the environment (real hardware initialization) upon startup.

## In-Software Status (GUI Log)

*   **✅ Passed**: `>>> Chosen One Certification Passed: [Intel QSV] [NVIDIA NVENC] [AMD AMF] (Ready)` (Displayed based on actual hardware)
*   **❌ Failed**: `>>> Warning: No valid AV1 hardware encoder (QSV/NVENC/AMF) detected.`

## Manual Confirmation (Terminal)

If you want to manually confirm, please execute the detection command corresponding to your graphics card in the terminal:

### Intel QSV
```bash
.\tools\ffmpeg.exe -init_hw_device qsv=hw -f lavfi -i color=black:s=1280x720 -pix_fmt p010le -c:v av1_qsv -frames:v 1 -f null - -v error
```

### NVIDIA NVENC
```bash
.\tools\ffmpeg.exe -f lavfi -i color=black:s=1280x720 -pix_fmt p010le -c:v av1_nvenc -frames:v 1 -f null - -v error
```

### AMD AMF
```bash
.\tools\ffmpeg.exe -f lavfi -i color=black:s=1280x720 -pix_fmt yuv420p -c:v av1_amf -usage transcoding -quality balanced -rc vbr_latency -qvbr_quality_level 30 -frames:v 1 -f null - -v error
```

*   **No Output**: Congratulations! Your hardware perfectly supports QSV, NVENC, or AMF AV1 hardware encoding.
*   **Output (Error)**: Indicates that your graphics card does not support the corresponding hardware encoder or the driver is not installed correctly.