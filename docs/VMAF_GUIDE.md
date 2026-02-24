# 🧪 VMAF 调优指南 (VMAF Tuning Guide)

[← 返回主页 (Back to README)](../README.md)

本工具通过 `ab-av1` 自动寻找最佳 ICQ 码率。VMAF 是衡量画质的关键指标：

*   **VMAF 95+ (极高画质)**: 适合 4K 收藏，画质几乎等同于原盘，体积缩减约 20-30%。
*   **VMAF 93 (推荐平衡)**: **默认设置**。肉眼无损的黄金分割点，体积缩减可达 40-60%。
*   **VMAF 90 (高压缩比)**: 适合在平板或手机上观看，在保持良好观感的前提下极大节省空间。
*   **VMAF < 85**: 可能会出现可见的压缩伪影，不建议用于长期收藏。

（全平台默认推荐 93，但画质仍会有差距 `(QSV > NVENC > AMF)` ，可根据个人喜好微调）

---

# 🧪 VMAF Tuning Guide (English)

← Back to README

This tool uses `ab-av1` to automatically find the best ICQ bitrate. VMAF is a key indicator for measuring image quality:

*   **VMAF 95+ (Extreme Quality)**: Suitable for 4K archiving, quality is almost identical to the original disc, volume reduction about 20-30%.
*   **VMAF 93 (Recommended Balance)**: **Default Setting**. The golden ratio for visually lossless quality, volume reduction can reach 40-60%.
*   **VMAF 90 (High Compression)**: Suitable for viewing on tablets or mobile phones, saving a lot of space while maintaining a good viewing experience.
*   **VMAF < 85**: Visible compression artifacts may appear, not recommended for long-term collection.

(93 is recommended by default for all platforms, but quality will still vary `(QSV > NVENC > AMF)`, fine-tune according to personal preference)