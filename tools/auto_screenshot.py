import sys
import os
import time

# 确保 Windows 终端下能够正确输出 UTF-8 字符 (避免 Emoji 导致的 GBK 编码报错)
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# 确保能加载项目根目录下的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_API"] = "pyside6"

from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

# --- 【黑魔法防御】全局 Mock 阻断所有模态弹窗的阻塞行为 ---
from qfluentwidgets import MessageDialog, MessageBoxBase
MessageDialog.exec = lambda self: 1  # 彻底让“世界线变动确认”等弹窗静默并立即返回
MessageBoxBase.exec = lambda self: 1

from ui.main_window import MainWindow

# --- 【三语 & 亮暗自适应】真理之眼鉴定书模拟数据生成器 ---
def get_mock_report(lang_code, is_dark):
    title_color = "#FB7299"
    container_color = "#9B59B6" if not is_dark else "#C39BD3"
    video_color = "#2ECC71" if not is_dark else "#82E0AA"
    key_color = "#7F8C8D" if not is_dark else "#BDC3C7"
    val_color = "#2C3E50" if not is_dark else "#ECF0F1"
    
    if lang_code == "en_US":
        return f"""
<div style="font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace; font-size: 13px; line-height: 1.6;">
<div style="text-align: center; margin-bottom: 15px;">
<h2 style="color: {title_color}; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">🔮 Eye of Truth Analysis Report</h2>
<div style="color: {key_color}; font-size: 11px; margin-top: 4px;">G:/Anime/[LingMoe] Magical Girl AV1 HDR test.mkv</div>
</div>
<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F1C40F, stop:1 #F39C12); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; display: inline-block; font-size: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">✨ Perfect Matroska Form</div>
<div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid {container_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">
<b style="color: {container_color}; font-size: 14px;">Container Properties</b><br/>
<span style="color: {key_color};">Format:</span> <span style="color: {val_color};">Matroska / WebM</span><br/>
<span style="color: {key_color};">Size:</span> <span style="color: {val_color};">1420.50 MB</span><br/>
<span style="color: {key_color};">Duration:</span> <span style="color: {val_color};">1440.00 s (00:24:00)</span><br/>
<span style="color: {key_color};">Total Bitrate:</span> <span style="color: {val_color};">8200 kbps</span><br/>
<span style="color: {key_color};">Stream Count:</span> <span style="color: {val_color};">3</span><br/>
</div>
<div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid {video_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">
<b style="color: {video_color}; font-size: 14px;">Video Stream #0 [🌈 HDR10 & Dolby Vision]</b><br/>
<span style="color: {key_color};">Codec:</span> <span style="color: {val_color};">HEVC (High Efficiency Video Coding)</span><br/>
<span style="color: {key_color};">Pixel Format:</span> <span style="color: {val_color};">yuv420p10le (10 bit)</span><br/>
<span style="color: {key_color};">Resolution:</span> <span style="color: {val_color};">3840 x 2160 (DAR: 16:9)</span><br/>
<span style="color: {key_color};">Color Space:</span> <span style="color: {val_color};">bt2020nc / bt2020 (HDR10)</span><br/>
<span style="color: {key_color};">Metadata:</span> <span style="color: {val_color};">Dolby Vision Version 1.0, Profile 8.1, RPU Present</span><br/>
</div>
</div>
"""
    elif lang_code == "ja_JP":
        return f"""
<div style="font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace; font-size: 13px; line-height: 1.6;">
<div style="text-align: center; margin-bottom: 15px;">
<h2 style="color: {title_color}; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">🔮 真理の目 鑑定報告書 (Eye of Truth Report)</h2>
<div style="color: {key_color}; font-size: 11px; margin-top: 4px;">G:/Anime/[LingMoe] Magical Girl AV1 HDR test.mkv</div>
</div>
<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F1C40F, stop:1 #F39C12); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; display: inline-block; font-size: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">✨ 完璧なコンテナ形式 (Matroska)</div>
<div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid {container_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">
<b style="color: {container_color}; font-size: 14px;">コンテナ属性 (Container)</b><br/>
<span style="color: {key_color};">フォーマット:</span> <span style="color: {val_color};">Matroska / WebM</span><br/>
<span style="color: {key_color};">ファイルサイズ:</span> <span style="color: {val_color};">1420.50 MB</span><br/>
<span style="color: {key_color};">再生時間:</span> <span style="color: {val_color};">1440.00 秒 (00:24:00)</span><br/>
<span style="color: {key_color};">総ビットレート:</span> <span style="color: {val_color};">8200 kbps</span><br/>
<span style="color: {key_color};">ストリーム数:</span> <span style="color: {val_color};">3</span><br/>
</div>
<div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid {video_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">
<b style="color: {video_color}; font-size: 14px;">ビデオストリーム #0 [🌈 HDR10 & Dolby Vision]</b><br/>
<span style="color: {key_color};">コーデック:</span> <span style="color: {val_color};">HEVC (High Efficiency Video Coding)</span><br/>
<span style="color: {key_color};">ピクセルフォーマット:</span> <span style="color: {val_color};">yuv420p10le (10 bit)</span><br/>
<span style="color: {key_color};">解像度:</span> <span style="color: {val_color};">3840 x 2160 (DAR: 16:9)</span><br/>
<span style="color: {key_color};">カラースペース:</span> <span style="color: {val_color};">bt2020nc / bt2020 (HDR10)</span><br/>
<span style="color: {key_color};">メタデータ:</span> <span style="color: {val_color};">Dolby Vision Version 1.0, Profile 8.1, RPU Present</span><br/>
</div>
</div>
"""
    else: # zh_CN / zh_TW
        return f"""
<div style="font-family: 'Cascadia Code', 'Consolas', 'Microsoft YaHei UI', monospace; font-size: 13px; line-height: 1.6;">
<div style="text-align: center; margin-bottom: 15px;">
<h2 style="color: {title_color}; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">🔮 真理之眼 鉴定报告 (Eye of Truth Report)</h2>
<div style="color: {key_color}; font-size: 11px; margin-top: 4px;">G:/Anime/[LingMoe] Magical Girl AV1 HDR test.mkv</div>
</div>
<div style="background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F1C40F, stop:1 #F39C12); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; display: inline-block; font-size: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">✨ 完美容器形式 (Perfect Matroska Form)</div>
<div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid {container_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">
<b style="color: {container_color}; font-size: 14px;">容器属性 (Container)</b><br/>
<span style="color: {key_color};">格式:</span> <span style="color: {val_color};">Matroska / WebM</span><br/>
<span style="color: {key_color};">大小:</span> <span style="color: #ECF0F1;">1420.50 MB</span><br/>
<span style="color: {key_color};">时长:</span> <span style="color: {val_color};">1440.00 s (00:24:00)</span><br/>
<span style="color: {key_color};">总码率:</span> <span style="color: {val_color};">8200 kbps</span><br/>
<span style="color: {key_color};">流总数:</span> <span style="color: {val_color};">3</span><br/>
</div>
<div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid {video_color}; border-radius: 4px 8px 8px 4px; padding: 10px; margin-bottom: 12px;">
<b style="color: {video_color}; font-size: 14px;">视频流 #0 (Video Stream) [🌈 HDR10 & Dolby Vision]</b><br/>
<span style="color: {key_color};">编码格式:</span> <span style="color: {val_color};">HEVC (High Efficiency Video Coding)</span><br/>
<span style="color: {key_color};">色彩深度:</span> <span style="color: {val_color};">yuv420p10le (10 bit)</span><br/>
<span style="color: {key_color};">分辨率:</span> <span style="color: {val_color};">3840 x 2160 (DAR: 16:9)</span><br/>
<span style="color: {key_color};">色彩空间:</span> <span style="color: {val_color};">bt2020nc / bt2020 (HDR10)</span><br/>
<span style="color: {key_color};">元数据支持:</span> <span style="color: {val_color};">Dolby Vision (杜比视界) Version 1.0, Profile 8.1, RPU Present</span><br/>
</div>
</div>
"""

# --- 【三语 & 亮暗自适应】日志框高保真模拟数据生成器 ---
def get_mock_logs(lang_code, is_dark):
    text_color = "#2C3E50" if not is_dark else "#ECF0F1"
    time_color = "#7F8C8D" if not is_dark else "#BDC3C7"
    info_color = "#2ECC71" if not is_dark else "#82E0AA"
    warn_color = "#E67E22" if not is_dark else "#F5CBA7"
    
    if lang_code == "en_US":
        return f"""
<div style="font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; color: {text_color}; line-height: 1.4;">
<span style="color: {time_color};">[03:19:05]</span> <span style="color: {info_color};">[INFO]</span> 🔮 Magical Girl Workshop v1.3.0 environment initialized successfully. (｡•̀ᴗ-)✧<br/>
<span style="color: {time_color};">[03:19:06]</span> <span style="color: {info_color};">[INFO]</span> 🚀 Launching graphics hardware probe... NVENC/QSV/AMF status: READY.<br/>
<span style="color: {time_color};">[03:19:07]</span> <span style="color: {warn_color};">[WARN]</span> QSV offset correction applied successfully (-2 offset).
</div>
"""
    elif lang_code == "ja_JP":
        return f"""
<div style="font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; color: {text_color}; line-height: 1.4;">
<span style="color: {time_color};">[03:19:05]</span> <span style="color: {info_color};">[INFO]</span> 🔮 魔法少女工房 v1.3.0 環境初期化が正常に完了しました。(｡•̀ᴗ-)✧<br/>
<span style="color: {time_color};">[03:19:06]</span> <span style="color: {info_color};">[INFO]</span> 🚀 グラフィックスハードウェア検出器を起動中... NVENC/QSV/AMF 準備完了。<br/>
<span style="color: {time_color};">[03:19:07]</span> <span style="color: {warn_color};">[WARN]</span> QSV遅延補正が適用されました (-2 オフセット)。
</div>
"""
    else: # zh_CN / zh_TW
        return f"""
<div style="font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; color: {text_color}; line-height: 1.4;">
<span style="color: {time_color};">[03:19:05]</span> <span style="color: {info_color};">[INFO]</span> 🔮 魔法少女工坊 v1.3.0 环境初始化完成。 (｡•̀ᴗ-)✧<br/>
<span style="color: {time_color};">[03:19:06]</span> <span style="color: {info_color};">[INFO]</span> 🚀 正在启动显卡硬件探测器... NVENC/QSV/AMF 状态就绪。<br/>
<span style="color: {time_color};">[03:19:07]</span> <span style="color: {warn_color};">[WARN]</span> QSV 咏唱延迟校正已应用 (-2 灵力偏移)。
</div>
"""


def run_auto_screenshot():
    # 1. 初始化 Qt 应用
    app = QApplication(sys.argv)
    global_font = QFont("Microsoft YaHei UI", 9)
    global_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(global_font)

    # 2. 创建主窗口
    w = MainWindow()
    
    # 强制绕过欢迎向导与依赖检查弹窗干扰
    w.is_first_run = False
    if hasattr(w, 'show_welcome_wizard'):
        w.show_welcome_wizard = lambda: None
    
    # 【核心注入】阻断后台线程的 ffprobe/ffmpeg 物理探测，直接在内存中建立高逼真度预览列表，解决“次元空间没有预览”的问题
    w.get_file_duration = lambda path: None
    w.get_file_thumbnail = lambda path, dur: None
    
    mock_files = [
        "G:/Anime/[LingMoe] Magical Girl AV1 HDR test.mkv",
        "G:/Anime/Magical_Girl_Workshop_v1.3.0_Promo.mp4"
    ]
    w.selected_files = mock_files.copy()
    
    # 显示窗口，以便获取完美的 QWidget 像素渲染
    w.show()
    w.resize(1200, 800)  # 强制固定理想截图分辨率

    # 强制刷新列表项渲染
    w.update_selected_count()
    w.set_duration_text_in_list(mock_files[0], "00:24:00")
    w.set_duration_text_in_list(mock_files[1], "00:05:32")

    output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(output_dir, "cache", "screenshots")
    os.makedirs(temp_dir, exist_ok=True)

    # 记录语言特定截图的临时文件
    lang_screenshots = {
        "zh_CN": [],
        "en_US": [],
        "ja_JP": []
    }

    # 封装安全的事件刷新与等待逻辑
    def safe_wait(ms=1000):
        # 持续刷新事件循环，允许 Qt 充分进行布局计算和样式重绘，特别解决深色模式切换延迟 Bug
        start = time.time()
        while (time.time() - start) * 1000 < ms:
            QApplication.processEvents()
            QCoreApplication.processEvents()
            time.sleep(0.02)

    # 截图的内部函数
    def capture_state(lang_code, name):
        safe_wait(1200) # 给足过渡动画和样式重绘的渲染时间

        # 【核心修复】暂时禁用 Mica 效果
        # Mica 是 Windows 11 DWM 层渲染的，QWidget::grab() 截不到它。
        # 暗色模式下透明区域会被填充为黑色，导致截图一半黑一半白。
        # 临时改用实心背景色代替，截完后再恢复。
        from qfluentwidgets import isDarkTheme
        is_dark_now = isDarkTheme()
        solid_bg = "#1c1c1c" if is_dark_now else "#f3f3f3"
        original_stylesheet = w.styleSheet()
        w.windowEffect.setMicaEffect(w.winId(), False)  # 关闭 Mica
        w.setStyleSheet(original_stylesheet + f" MainWindow {{ background-color: {solid_bg}; }}")
        w.repaint()
        QApplication.processEvents()
        safe_wait(300)  # 等待背景切换渲染完成

        pixmap = w.grab()
        file_path = os.path.join(temp_dir, f"{lang_code}_{name}.png")
        pixmap.save(file_path, "PNG")
        lang_screenshots[lang_code].append(file_path)
        print(f"📸 [{lang_code}] 已成功捕获界面: {name}")

        # 恢复 Mica 效果
        w.windowEffect.setMicaEffect(w.winId())
        w.setStyleSheet(original_stylesheet)
        QApplication.processEvents()

    # 切换语言逻辑
    def switch_language(lang_code):
        for i in range(w.combo_lang.count()):
            if w.combo_lang.itemData(i) == lang_code:
                # 先关闭自动弹窗以双重确保不卡死，然后再通过 index 触发切换
                w.combo_lang.blockSignals(True)
                w.combo_lang.setCurrentIndex(i)
                w.combo_lang.blockSignals(False)
                w.on_language_changed(i)
                safe_wait(800)
                break

    # 切换主题并自适应刷新文本色系逻辑
    def switch_theme(theme_idx, lang_code):
        is_dark = (theme_idx == 2)
        
        # A. 切换核心主题
        w.combo_theme.setCurrentIndex(theme_idx)
        w.on_theme_changed(theme_idx)
        safe_wait(3000) # 【增大】暗色模式调色板广播需要更多时间传播至所有子控件 (3s)
        
        # B. 【核心修复】自适应更新“真理之眼鉴定报告”的 HTML 文本颜色
        w.info_interface.info_text.setHtml(get_mock_report(lang_code, is_dark))
        w.info_interface.btn_add_list.show()
        
        # C. 【核心修复】自适应更新“虚空日志框”的 HTML 文本颜色
        if hasattr(w, 'text_log') and w.text_log:
            w.text_log.setHtml(get_mock_logs(lang_code, is_dark))
        
        safe_wait(200)

    # 4. 精细控制多语言截图流
    def execute_flow(lang_code, next_callback):
        print(f"\n🔮 开始截取语言 [{lang_code}] 的全套流程...")
        
        # A. 切换到对应的语言
        switch_language(lang_code)
        
        # B. 浅色模式 - 压制面板
        switch_theme(1, lang_code) # Light Mode + Refresh text colors
        w.switchTo(w.home_interface)
        capture_state(lang_code, "01_light_home")
        
        # C. 浅色模式 - 媒体信息检测面板 (真理之眼预览)
        w.switchTo(w.info_interface)
        capture_state(lang_code, "02_light_info")
        
        # D. 浅色模式 - 系统设定面板
        w.switchTo(w.settings_interface)
        capture_state(lang_code, "03_light_settings")
        
        # E. 深色模式 - 压制面板 (色域觉醒)
        switch_theme(2, lang_code) # Dark Mode + Refresh text colors
        w.switchTo(w.home_interface)
        capture_state(lang_code, "04_dark_home")
        
        # F. 深色模式 - 媒体信息检测面板 (真理之眼预览)
        w.switchTo(w.info_interface)
        capture_state(lang_code, "05_dark_info")
        
        # G. 深色模式 - 系统设定面板
        w.switchTo(w.settings_interface)
        capture_state(lang_code, "06_dark_settings")
        
        next_callback()

    # 串联串行执行
    def run_zh():
        execute_flow("zh_CN", run_en)

    def run_en():
        execute_flow("en_US", run_jp)

    def run_jp():
        execute_flow("ja_JP", compile_all)

    def compile_all():
        w.close()
        print("\n🎉 自动化截图圆满完成，正在将各个语言的图集编译为对应的 GIF 动图...")
        try:
            from PIL import Image
            
            # 配置目标文件
            gif_configs = [
                ("zh_CN", os.path.join(output_dir, "screenshot.gif")),
                ("en_US", os.path.join(output_dir, "screenshot_en.gif")),
                ("ja_JP", os.path.join(output_dir, "screenshot_jp.gif"))
            ]
            
            for lang, target_path in gif_configs:
                files = lang_screenshots[lang]
                if not files:
                    continue
                
                images = [Image.open(fn) for fn in files]
                images[0].save(
                    target_path,
                    save_all=True,
                    append_images=images[1:],
                    duration=2000,  # 帧间隔 2 秒
                    loop=0
                )
                print(f"✨ 成功编译 [{lang}] 并覆盖 GIF: {os.path.basename(target_path)}")
                
            print("\n🌟 所有多语言动态截图完美构建！暗色 Bug 已修复，真理之眼数据已注入，且三语版已完全切分！")
        except ImportError:
            print("❌ 错误: 未检测到 pillow 库，无法自动融合成 GIF。请先运行: pip install pillow")
        except Exception as e:
            print(f"❌ 融合成 GIF 失败: {e}")
        finally:
            app.quit()

    # 启动首个延迟任务序列
    QTimer.singleShot(1500, run_zh)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    print("🔮 魔法少女工坊 - 自动化多语言高保真截图开始...")
    print("👉 脚本将依次切换 简体中文、英文、日文，并在浅色/深色主题间无缝切换截取。")
    print("👉 已深度优化：注入真理之眼高科技 HDR 分析报告，修复暗色重绘时延 Bug！")
    print("👉 已完美拦截：全局 Mock 并阻断了所有阻塞弹窗（包括“世界线变动确认”弹窗）！")
    print("👉 终极体自适应：亮暗切换时，自动同调重新生成日志框和鉴定报告的字体颜色，完美贴合亮暗背景！")
    print("👉 请不要在运行期间手动调整或最小化弹出的窗口以确保画面完美。")
    run_auto_screenshot()
