language_name = "繁體中文"

# 這是一個充滿「中二」風格（二次元/魔法設定）的語言檔案。
# 右側註釋為實際對應的技術功能。
translation = {
    # -------------------------------------------------------------------------
    # Main Window (main.py)
    # -------------------------------------------------------------------------
    "app.title": "魔法少女工坊", # 應用主標題
    "app.subtitle": "AV1 硬體加速魔力驅動 · 絕對領域 Edition", # 應用副標題
    "app.welcome": "歡迎來到魔法少女工坊 ✨", # 歡迎訊息
    "app.designed_by": "Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # 設計者和技術支援資訊

    # -------------------------------------------------------------------------
    # Home Interface (view/home_interface.py)
    # -------------------------------------------------------------------------
    "home.title": "鍊成祭壇", # 首頁
    "home.header.title": "鍊成祭壇", # 首頁標題
    "home.header.subtitle": "AV1 硬體加速魔力驅動 · 絕對領域 Edition", # 首頁副標題
    "home.header.theme_combo.auto": "世界線收束 (Auto)", # 主題：跟隨系統
    "home.header.theme_combo.light": "光之加護 (Light)", # 主題：淺色模式
    "home.header.theme_combo.dark": "深淵凝視 (Dark)", # 主題：深色模式
    
    # Cache Card
    "home.cache_card.title": "魔力迴路快取 (Cache)", # 快取設定
    "home.cache_card.clear_button": "🧹 淨化殘渣", # 清除快取
    "home.cache_card.path_placeholder": "ab-av1 暫存檔案存放處...", # 快取路徑輸入框的佔位符
    "home.cache_card.browse_button": "鎖定座標", # 瀏覽快取路徑按鈕
    
    # Settings Card
    "home.settings_card.encoder.label": "魔力核心 (Encoder)", # 編碼器選擇 (QSV/NVENC/AMF)
    "home.settings_card.vmaf.label": "視界還原度 (VMAF)", # VMAF 目標畫質評分
    "home.settings_card.bitrate.label": "共鳴頻率 (Bitrate)", # 碼率控制
    "home.settings_card.preset.label": "詠唱速度 (Preset)", # 編碼預設 (速度 vs 畫質)
    "home.settings_card.offset.label": "靈力偏移 (Offset)", # 硬體編碼參數微調
    "home.settings_card.loudnorm.label": "音量均一化術式 (Loudnorm)", # 音訊響度統一
    "home.settings_card.nv_aq.label.nvidia": "NVIDIA 感知增強 (AQ)", # NVIDIA AQ 設定標籤
    "home.settings_card.nv_aq.label.amd": "AMD 預分析 (PreAnalysis)", # AMD 預分析設定標籤
    "home.settings_card.nv_aq.label.intel": "Intel 深度分析 (Lookahead)", # Intel 深度分析設定標籤
    "home.settings_card.nv_aq.on": "展開", # 開啟 (Enable)
    "home.settings_card.nv_aq.off": "收束", # 關閉 (Disable)
    "home.settings_card.save_button": "💾 銘刻記憶 (Save)", # 保存設定
    "home.settings_card.reset_button": "↩️ 記憶回溯 (Reset)", # 重置設定
    "home.settings_card.loudnorm_mode.auto": "調和之詠 (智慧繞行多聲道)", # 自動 (Auto: 5.1/7.1 不進行響度均衡)
    "home.settings_card.loudnorm_mode.always": "歸一之詠 (強制同調萬物聲)", # 強制開啟 (Always)
    "home.settings_card.loudnorm_mode.disable": "寂靜之詠 (保留原始聲之貌)", # 禁用 (Disable)
    
    # Action Card
    "home.action_card.save_mode.save_as": "開闢新世界 (Save As)", # 另存為
    "home.action_card.save_mode.overwrite": "元素覆寫 (Overwrite)", # 覆蓋原檔案
    "home.action_card.save_mode.remain": "元素保留 (Remain)", # 保留源檔案
    "home.action_card.export_path_placeholder": "新世界座標...", # 匯出路徑輸入框的佔位符
    "home.action_card.choose_button": "指定座標", # 選擇匯出路徑按鈕
    "home.action_card.start_button": "✨ 締結契約 (Start)", # 開始轉碼
    "home.action_card.pause_button": "⏳ 時空凍結 (Pause)", # 暫停
    "home.action_card.stop_button": " 契約破棄 (Stop)", # 停止
    
    # Source Card
    "home.source_card.title": "素材次元 (Source)", # 輸入源設定
    "home.source_card.folder_button": "以資料夾之名", # 選擇資料夾
    "home.source_card.file_button": "以檔案之名", # 選擇檔案
    
    # File List Card
    "home.file_list_card.title": "次元空間 (List)", # 任務列表
    "home.file_list_card.clear_button": "歸於虛無", # 清空列表
    "home.file_list_card.placeholder": "將素材投入鍊成法陣...", # 檔案列表的佔位符
    "list.item.remove_button": "放逐", # 列表中移除檔案按鈕
    "list.item.duration_button": "窺探時間線", # 列表中查看時長按鈕
    
    # Status Bar
    "home.status_bar.current_label": "目前鍊成:", # 狀態列當前任務標籤
    "home.status_bar.total_label": "總體進度:", # 狀態列總體進度標籤

    # -------------------------------------------------------------------------
    # Media Info Interface (view/info_interface.py)
    # -------------------------------------------------------------------------
    "info.title": "真理之眼", # 「真理之眼」頁面標題
    "info.drop_card.title": "真理之眼 · 物質解析", # 「真理之眼」頁面拖放卡片標題
    "info.drop_card.hint": "將未知的遺物投入此地以窺探真理... (拖曳檔案)", # 「真理之眼」頁面拖放卡片提示
    "info.text_edit.placeholder": "等待魔力注入... (Waiting for file drop)", # 「真理之眼」頁面文本框佔位符
    "info.buttons.add_to_list": "納入祭壇", # 「真理之眼」頁面添加到列表按鈕
    "info.buttons.clear": "因果切斷", # 「真理之眼」頁面清空按鈕
    "info.buttons.copy": "拓印報告", # 「真理之眼」頁面複製報告按鈕
    "info.analysis.in_progress": "✨ 正在窺探真理，請稍候...", # 「真理之眼」頁面分析中提示
    "info.infobar.copy_success.title": "拓印完成", # 「真理之眼」頁面複製成功提示標題
    "info.infobar.copy_success.content": "鑑定報告已拓印至記憶水晶 (剪貼簿)。", # 「真理之眼」頁面複製成功提示內容
    
    # Report Content
    "info.report.title": "📜 物質真理鑑定書",
    "info.report.perfect_form": "✨ 已是完美形態 (Perfect Form)",
    "info.report.parse_error": "💥 解析失敗 (Error):",
    "info.report.container_title": "📦 容器構造 (Container)",
    "info.report.format": "• 封印術式 (Format):",
    "info.report.size": "• 物質總量 (Size):",
    "info.report.duration": "• 時間軸跨度 (Duration):",
    "info.report.total_bitrate": "• 綜合魔力流速 (Total Bitrate):",
    "info.report.stream_count": "• 構成元素數 (Stream Count):",
    "info.report.video_title": "👁️ 視覺投影 (Stream #{idx} - Video)",
    "info.report.codec": "• 構築術式 (Codec):",
    "info.report.profile_level": "• 術式階位 (Profile/Level):",
    "info.report.resolution": "• 視界解析度 (Resolution):",
    "info.report.pix_fmt": "• 粒子排列 (Pixel Format):",
    "info.report.color_space": "• 色彩領域 (Color Space):",
    "info.report.bitrate": "• 魔力流速 (Bitrate):",
    "info.report.audio_title": "🔊 聽覺共鳴 (Stream #{idx} - Audio)",
    "info.report.sample_rate": "• 共鳴頻率 (Sample Rate):",
    "info.report.sample_fmt": "• 波形精度 (Sample Format):",
    "info.report.channel_layout": "• 空間聲場 (Channel Layout):",
    "info.report.subtitle_title": "📝 銘文記載 (Stream #{idx} - Subtitle)",
    "info.report.language": "• 銘文語種 (Language):",

    # -------------------------------------------------------------------------
    # Profile Interface (view/profile_interface.py)
    # -------------------------------------------------------------------------
    "profile.title": "觀測者檔案", # 「觀測者檔案」頁面標題
    "profile.card.author_desc": "「 🌙 上班族 | 🎥 UP主 | 🛠️ 喜歡3C產品 」", # 「觀測者檔案」頁面作者描述
    "profile.card.author_motto": "「在程式碼的海洋裡尋找魔法，在數位的世界裡觀測真理。」", # 「觀測者檔案」頁面作者座右銘
    "profile.buttons.bilibili": "📺 嗶哩嗶哩", # 「觀測者檔案」頁面嗶哩嗶哩按鈕
    "profile.buttons.youtube": "▶️ YouTube", # 「觀測者檔案」頁面YouTube按鈕
    "profile.buttons.douyin": "🎵 抖音", # 「觀測者檔案」頁面抖音按鈕
    "profile.buttons.github": "🐙 GitHub", # 「觀測者檔案」頁面GitHub按鈕
    "profile.buttons.show_wizard": "✨ 重溫入職嚮導", # 「觀測者檔案」頁面顯示歡迎嚮導按鈕

    # -------------------------------------------------------------------------
    # Credits Interface (view/credits_interface.py)
    # -------------------------------------------------------------------------
    "credits.title": "羈絆之證", # 「羈絆之證」頁面標題
    "credits.card.contributor_role": "術式構築協力", # 「羈絆之證」頁面貢獻者角色
    "credits.card.intro": "v{version} 工坊升級改造貢獻者，其偉績如下：", # 「羈絆之證」頁面介紹
    "credits.contributions.item1.title": "新魔力循環系統", # 「羈絆之證」頁面貢獻項1標題
    "credits.contributions.item1.desc": "最佳化魔力流動穩定性", # 「羈絆之證」頁面貢獻項1描述
    "credits.contributions.item2.title": "固化核心詠唱基盤", # 「羈絆之證」頁面貢獻項2標題
    "credits.contributions.item2.desc": "提升儀式穩定性", # 「羈絆之證」頁面貢獻項2描述
    "credits.contributions.item3.title": "聖遺物框架升級", # 「羈絆之證」頁面貢獻項3標題
    "credits.contributions.item3.desc": "擁抱開源與更強的力量", # 「羈絆之證」頁面貢獻項3描述
    "credits.contributions.item4.title": "鍊成物可攜化封裝", # 「羈絆之證」頁面貢獻項4標題
    "credits.contributions.item4.desc": "靈體更小，召喚更快", # 「羈絆之證」頁面貢獻項4描述
    "credits.contributions.item5.title": "重構鍊成工具鏈", # 「羈絆之證」頁面貢獻項5標題
    "credits.contributions.item5.desc": "支援更靈活的術式分發", # 「羈絆之證」頁面貢獻項5描述
    "credits.contributions.item6.title": "自動化鍊金工坊", # 「羈絆之證」頁面貢獻項6標題
    "credits.contributions.item6.desc": "雲端自動構築與分發", # 「羈絆之證」頁面貢獻項6描述
    "credits.card.footer": "特別鳴謝: PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # 「羈絆之證」頁面頁尾

    # -------------------------------------------------------------------------
    # Welcome Wizard (view/welcome_wizard.py)
    # -------------------------------------------------------------------------
    "welcome.wizard.title": "歡迎來到魔法少女工坊 ✨", # 歡迎嚮導標題
    "welcome.wizard.page1.title": "初次見面，適格者！", # 歡迎嚮導第一頁標題
    "welcome.wizard.page1.content": "這是一個專為 NAS 倉鼠黨打造的 AV1 硬體轉檔工具。\n\n它能利用 Intel/NVIDIA/AMD 顯示卡的算力，將影片體積縮小 30%-50%，同時保持肉眼無損的畫質。\n\n接下來，讓我為您簡單介紹幾個關鍵設定...", # 歡迎嚮導第一頁內容
    "welcome.wizard.page2.title": "1. 魔力核心 (Encoder)", # 歡迎嚮導第二頁標題
    "welcome.wizard.page2.content": "這是轉檔引擎的選擇。\n\n• Intel QSV: 適合 Arc 獨顯 / Ultra 內顯。\n• NVIDIA NVENC: 適合 RTX 40 系列。\n• AMD AMF: 適合 RX 7000 系列 / RDNA 3 架構內顯。\n\n程式啟動時會自動偵測您的硬體，通常無需手動更改。", # 歡迎嚮導第二頁內容
    "welcome.wizard.page3.title": "2. 視界還原度 (VMAF)", # 歡迎嚮導第三頁標題
    "welcome.wizard.page3.content": "這是決定畫質的核心指標 (0-100)。\n\n• 95+: 極高畫質，適合收藏。\n• 93 (預設): 黃金平衡點，肉眼無損，體積縮減顯著。\n• 90: 高壓縮比，適合行動裝置觀看。\n\n建議保持預設 93.0。", # 歡迎嚮導第三頁內容
    "welcome.wizard.page4.title": "3. 詠唱速度 (Preset)", # 歡迎嚮導第四頁標題
    "welcome.wizard.page4.content": "平衡編碼速度與壓縮效率 (1-7)。\n\n• 數字越小 (1-3): 速度慢，體積更小，畫質更好。\n• 數字越大 (5-7): 速度快，體積稍大。\n• 預設 4: 均衡之選。\n\n掛機洗版建議設為 3 或 4。", # 歡迎嚮導第四頁內容
    "welcome.wizard.page5.title": "4. 靈力偏移 (Offset)", # 歡迎嚮導第五頁標題
    "welcome.wizard.page5.content": "針對硬體編碼器的微調參數。\n\n由於硬體編碼器效率不同，我們需要對 CPU 偵測出的參數進行修正。\n• AMD 預設 -6\n• NVIDIA 預設 -4\n• Intel 預設 -2\n\n這能確保最終畫質接近您的 VMAF 預期。", # 歡迎嚮導第五頁內容
    "welcome.wizard.next_button": "翻閱魔導書", # 歡迎嚮導下一頁按鈕
    "welcome.wizard.skip_button": "瞬間展開", # 歡迎嚮導跳過按鈕
    "welcome.wizard.start_button": "開始鍊成", # 歡迎嚮導開始按鈕

    # -------------------------------------------------------------------------
    # Dialogs
    # -------------------------------------------------------------------------
    "dialog.clear_list.title": "確認要歸於虛無嗎？", # 清空列表確認對話方塊標題
    "dialog.clear_list.content": "此操作將從祭壇中移除所有待淨化的異變體，因果律將被重置。確定要繼續嗎？", # 清空列表確認對話方塊內容
    "dialog.clear_list.yes_button": "確定 (Void)", # 清空列表確認對話方塊「是」按鈕
    "dialog.clear_list.cancel_button": "取消 (Stay)", # 清空列表確認對話方塊「取消」按鈕
    "dialog.clear_cache.title": "確認要肅清魔力殘渣嗎？", # 清除快取確認對話方塊標題
    "dialog.clear_cache.content": "這些是鍊成儀式中產生的混沌碎片 (*.temp.mkv)，繼續留存可能會干擾世界線的穩定。\n\n目標區域：{path}\n\n一旦執行肅清，這些碎片將徹底歸於虛無，無法找回。確定要發動淨化術式嗎？", # 清除快取確認對話方塊內容
    "dialog.clear_cache.yes_button": "發動淨化 (Purify)", # 清除快取確認對話方塊「是」按鈕
    "dialog.clear_cache.cancel_button": "維持結界", # 清除快取確認對話方塊「取消」按鈕
    "dialog.error.skip_button": "跳過並繼續 (Skip)", # 錯誤對話方塊「跳過」按鈕
    "dialog.error.stop_button": "緊急中斷", # 錯誤對話方塊「停止」按鈕
    "dialog.dependency_missing.title": "⚠️ 結界破損警告 (Critical Error)", # 依賴缺失對話方塊標題
    "dialog.dependency_missing.content": "嗚哇！大事不好了！(>_<)\n工坊的魔力迴路偵測到了嚴重的斷裂！\n\n以下核心聖遺物似乎離家出走了：\n{missing_files}\n\n沒有它們，鍊成儀式將無法進行！\n請儘快將它們召回至工坊目錄！", # 依賴缺失對話方塊內容
    "dialog.dependency_missing.yes_button": "召喚支援", # 依賴缺失對話方塊「是」按鈕
    "dialog.dependency_missing.cancel_button": "我明白了", # 依賴缺失對話方塊「取消」按鈕
    "dialog.language_change.title": "世界線變動確認", # 語言更改對話方塊標題
    "dialog.language_change.content": "為了讓世界線收束至新的語言領域，建議重啟觀測終端。", # 語言更改對話方塊內容
    "dialog.language_change.yes_button": "遵命", # 語言變更對話方塊「是」按鈕
    "dialog.language_change.cancel_button": "片刻之後", # 語言變更對話方塊「取消」按鈕
    "dialog.encoder.crash_title": "術式崩壞警告", # 編碼器崩潰警告標題
    "dialog.encoder.crash_content": "任務 {fname} 遭遇未知錯誤。\n是否跳過此任務並繼續？", # 編碼器崩潰警告內容

    # -------------------------------------------------------------------------
    # InfoBars / Notifications
    # -------------------------------------------------------------------------
    "infobar.success.settings_saved.title": "記憶已銘刻", # 設置已保存成功提示標題
    "infobar.success.settings_saved.content": "目前術式參數已銘刻至虛空記憶 (config.ini)", # 設置已保存成功提示內容
    "infobar.success.files_added.title": "素材投入成功", # 檔案已添加成功提示標題
    "infobar.success.files_added.content": "已將 {count} 個素材投入鍊成陣。", # 檔案已添加成功提示內容
    "infobar.success.drag_drop_added.content": "透過空間傳送投入了 {count} 個素材。", # 拖曳添加檔案成功提示內容
    "infobar.success.cache_cleared.title": "淨化完成", # 快取已清除成功提示標題
    "infobar.success.cache_cleared.content": "已清除 {count} 個魔力殘渣！", # 快取已清除成功提示內容
    "infobar.success.synced.title": "同步成功", # 同步成功提示標題
    "infobar.success.synced.content": "該物質已成功納入祭壇！", # 同步成功提示內容
    "infobar.info.settings_reset.title": "記憶回溯成功", # 設置已重置提示標題
    "infobar.info.settings_reset.content": "參數已重置為初始形態", # 設置已重置提示內容
    "infobar.warning.no_files_selected.title": "魔力不足", # 未選擇檔案警告提示標題
    "infobar.warning.no_files_selected.content": "請先指定要淨化的目標！", # 未選擇檔案警告提示內容
    "infobar.warning.no_export_dir.title": "座標遺失", # 未選擇匯出目錄警告提示標題
    "infobar.warning.no_export_dir.content": "目前為「開闢新世界」模式，請為新世界指定座標！", # 未選擇匯出目錄警告提示內容
    "infobar.warning.no_files_found.title": "素材探知失敗", # 未找到檔案警告提示標題
    "infobar.warning.no_files_found.content": "該次元未發現可鍊成的素材。", # 未找到檔案警告提示內容
    "infobar.warning.no_new_files_dropped.title": "投入失敗", # 未添加新檔案警告提示標題
    "infobar.warning.no_new_files_dropped.content": "投入的素材無效，或已存在於法陣中。", # 未添加新檔案警告提示內容
    "infobar.warning.task_running.title": "術式進行中", # 任務正在運行警告提示標題
    "infobar.warning.task_running.content": "鍊成儀式尚未結束，無法強行重置次元空間！", # 任務正在運行警告提示內容
    "infobar.warning.invalid_cache_path.title": "座標無效", # 無效快取路徑警告提示標題
    "infobar.warning.invalid_cache_path.content": "請先指定有效的魔力緩衝區域...", # 無效快取路徑警告提示內容
    "infobar.warning.dependency_check_skipped.title": "魔力核心重檢已跳過", # 依賴檢查已跳過警告提示標題
    "infobar.warning.dependency_check_skipped.content": "目前正在進行鍊成，停止任務後再執行記憶回溯可觸發自檢。", # 依賴檢查已跳過警告提示內容
    "infobar.warning.hardware_unsupported.title": "聖遺物排斥反應", # 硬體不支援警告提示標題
    "infobar.warning.hardware_unsupported.content": "汝之聖遺物似乎無法與此地的魔力同調。(硬體不支援或驅動程式錯誤)", # 硬體不支援警告提示內容
    "infobar.warning.duplicate_dependency_check.content": "自檢術式已在執行中，請勿重複詠唱。", # 重複依賴檢查警告提示內容
    "infobar.error.vmaf_not_number.title": "術式構成錯誤", # VMAF 非數字錯誤提示標題
    "infobar.error.vmaf_not_number.content": "視界還原度必須由數字符文構成 (如 93.0)", # VMAF 非數字錯誤提示內容
    "infobar.error.cache_clear_failed.title": "淨化術式反噬", # 清除快取失敗錯誤提示標題
    "infobar.copy_warning.title": "空空如也", # 「真理之眼」頁面複製警告提示標題
    "infobar.copy_warning.content": "還沒有解析任何物質喔...", # 「真理之眼」頁面複製警告提示內容

    # -------------------------------------------------------------------------
    # Core / Worker / Logger
    # -------------------------------------------------------------------------
    "common.unknown_error": "不可名狀之錯誤", # 通用未知錯誤
    "dependency.ffmpeg_desc": "核心術式構築 (FFmpeg)", # FFmpeg 描述
    "dependency.ffprobe_desc": "真理之眼組件 (FFprobe)", # FFprobe 描述
    "dependency.ab_av1_desc": "極限詠唱觸媒 (ab-av1)", # ab-av1 描述
    
    # Button States
    "button.start.in_progress": "✨ 奇蹟發生中...", # 開始按鈕進行中狀態
    "button.save.saved": "✅ 已銘刻", # 儲存按鈕已儲存狀態
    "button.reset.restored": "✅ 已回溯", # 重設按鈕已恢復狀態
    "button.start.missing_components": "🚫 缺少組件", # 開始按鈕缺少組件狀態

    # Logs
    "log.system_ready": "系統就緒... {kaomoji}", # 系統就緒日誌
    "log.dependency_check_start": ">>> 正在啟動環境自檢術式 (Initializing environment check)...", # 開始依賴檢查日誌
    "log.dependency_check_finished.success": ">>> 適格者認證通過：", # 依賴檢查成功日誌
    "log.dependency_check_finished.fail": ">>> 警告：未偵測到有效的 AV1 硬體編碼器 (QSV/NVENC/AMF)。", # 依賴檢查失敗日誌
    "log.autoselect_encoder": ">>> 已自動切換至 {encoder} 術式。", # 自動選擇編碼器日誌
    "log.recalibrating": ">>> 正在重新校準魔力核心可用性 (Re-calibrating)...", # 重新校準日誌
    "log.list_cleared": ">>> 祭壇已清空，所有因果律已重置。 (Voided)", # 列表已清空日誌
    "log.task_pause": ">>> 固有結界已凍結 (Paused)...", # 任務暫停日誌
    "log.task_resume": ">>> 時空流動已恢復...", # 任務恢復日誌
    "log.task_stop_request": ">>> 正在請求中止...", # 請求停止任務日誌
    "log.fatal_error_component_missing": ">>> 致命錯誤：關鍵組件缺失，系統已停擺。", # 組件缺失致命錯誤日誌
    "log.dependency.qsv_failed": ">>> Intel QSV 自檢未通過: {error}", # QSV 自檢失敗日誌
    "log.dependency.qsv_exception": ">>> Intel QSV 檢測異常: {error}", # QSV 檢測異常日誌
    "log.dependency.nvenc_unsupported_gpu": ">>> 提示: 偵測到 NVIDIA 顯示卡，但該型號不支援 AV1 硬體編碼 (需 RTX 40 系列)。", # NVENC 不支援日誌
    "log.dependency.nvenc_failed": ">>> NVENC 自檢未通過: {error}", # NVENC 自檢失敗日誌
    "log.dependency.nvenc_exception": ">>> NVENC 檢測異常: {error}", # NVENC 檢測異常日誌
    "log.dependency.amf_failed": ">>> AMD AMF 自檢未通過: {error}", # AMF 自檢失敗日誌
    "log.dependency.amf_exception": ">>> AMD AMF 檢測異常: {error}", # AMF 檢測異常日誌
    "log.dependency.check_exception": ">>> 環境自檢異常: {error}", # 環境自檢異常日誌
    "log.encoder.no_files_found": "偵測不到任何魔力殘留... (｡•ˇ‸ˇ•｡)", # 未發現檔案日誌
    "log.encoder.tasks_found": "捕捉到 {total_tasks} 個待淨化異變體！( •̀ ω •́ )y", # 發現任務日誌
    "log.encoder.task_start": "[{i}/{total_tasks}] 正在對 {fname} 展開固有結界...", # 任務開始日誌
    "log.encoder.skip_av1": " -> 此物質已是純淨形態 (AV1)，跳過~ (Pass)", # 跳過 AV1 日誌
    "log.encoder.status_skipped": "✨ 跳過", # 狀態：跳過
    "log.encoder.status_duration": "耗時: {total_duration:.2f}s", # 狀態：耗時
    "log.encoder.ab_av1_fallback": " -> 嘗試備用方案: {desc}...", # ab-av1 備用方案日誌
    "log.encoder.ab_av1_start": " -> 正在推演最強術式 (ab-av1)...", # ab-av1 開始日誌
    "log.encoder.ab_av1_probing": "    -> 探測中: {probe_crf} => VMAF: {vmaf_val}", # ab-av1 探測日誌
    "log.encoder.ab_av1_success_offset_corrected": " -> 術式解析完畢 ({desc}): 原始CRF {cpu_crf} + 偏移 {offset} = {raw_icq} (已修正為{reason}限制 {best_icq}) [耗時: {search_duration:.1f}s]", # ab-av1 成功(修正)日誌
    "log.encoder.ab_av1_success_offset": " -> 術式解析完畢 ({desc}): 原始CRF {cpu_crf} + 偏移 {offset} => 最終參數 {best_icq} [耗時: {search_duration:.1f}s]", # ab-av1 成功(偏移)日誌
    "log.encoder.ab_av1_success": " -> 術式解析完畢 (ICQ): {best_icq} [耗時: {search_duration:.1f}s] (๑•̀ㅂ•́)و✧", # ab-av1 成功日誌
    "log.encoder.ab_av1_failed": " -> 解析失敗，強制使用基礎術式 ICQ: {best_icq} (T_T)", # ab-av1 失敗日誌
    "log.encoder.ab_av1_error_log_header": "    [ab-av1 錯誤回溯]:", # ab-av1 錯誤頭日誌
    "log.encoder.icq_corrected": " -> 修正: 硬體編碼器參數限制 ({icq} -> 51)", # ICQ 修正日誌
    "log.encoder.ffmpeg_exception": " -> 魔力逆流: {error} (×_×)", # FFmpeg 異常日誌
    "log.encoder.success_overwrite": " -> 淨化完成！舊世界已被重寫 (Overwrite) (ﾉ>ω<)ﾉ [壓制: {encode_duration:.1f}s | 總耗時: {total_duration:.1f}s]", # 成功(覆蓋)日誌
    "log.encoder.error_move_overwrite": "無法替換來源檔案，可能被其他程式佔用。", # 移動覆蓋失敗日誌
    "log.encoder.success_remain": " -> 淨化完成！元素已保留，最佳化體已生成 (Remain) (ﾉ>ω<)ﾉ [壓制: {encode_duration:.1f}s | 總耗時: {total_duration:.1f}s]", # 成功(保留)日誌
    "log.encoder.success_save_as": " -> 淨化完成！新世界已確立 (Save As) (ﾉ>ω<)ﾉ [壓制: {encode_duration:.1f}s | 總耗時: {total_duration:.1f}s]", # 成功(另存為)日誌
    "log.encoder.status_done": "✅ 完成", # 狀態：完成
    "log.encoder.error_move": " -> 封印儀式失敗: {error} (T_T)", # 移動檔案失敗日誌
    "log.encoder.ffmpeg_crash": " -> 術式失控 (Crash)... (T_T)", # FFmpeg 崩潰日誌
    "log.encoder.cooling_down": " -> 正在冷卻魔術迴路 (Cooling down GPU)...", # 冷卻日誌
    "log.encoder.all_done": ">>> 奇蹟達成！(๑•̀ㅂ•́)و✧", # 全部完成日誌
    "log.encoder.stopped": ">>> 契約被強制切斷。", # 停止日誌
    "log.encoder.fatal_error": "世界線變動率異常 (Fatal): {error}", # 致命錯誤日誌
    "log.encoder.info_multichannel": " -> 感知到多重聲場 ({channels}ch)，已保持原樣。", # 多聲道資訊日誌
    "log.encoder.info_loudnorm_enabled": " -> 聲場調和 (Loudnorm): 啟用 ({mode})", # 響度均衡啟用日誌
    "log.encoder.info_loudnorm_skipped": " -> 聲場調和 (Loudnorm): 跳過 ({mode})", # 響度均衡跳過日誌
}