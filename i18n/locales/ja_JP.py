language_name = "日本語"

# これは「中二病」スタイル（二次元/魔法設定）に満ちた言語ファイルです。
# 右側のコメントは実際の技術的機能に対応しています。
translation = {
    # -------------------------------------------------------------------------
    # Main Window (main.py)
    # -------------------------------------------------------------------------
    "app.title": "魔法少女工房", # アプリケーションのメインタイトル
    "app.subtitle": "AV1 ハードウェア加速魔力駆動 · 絶対領域 Edition", # アプリケーションのサブタイトル
    "app.welcome": "ようこそ、魔法少女工房へ ✨", # ウェルカムメッセージ
    "app.designed_by": "Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>泠萌404</a> | Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # 設計者と技術サポート情報

    # -------------------------------------------------------------------------
    # Home Interface (view/home_interface.py)
    # -------------------------------------------------------------------------
    "home.title": "錬成祭壇", # ホーム
    "home.header.title": "錬成祭壇", # ホームタイトル
    "home.header.subtitle": "AV1 ハードウェア加速魔力駆動 · 絶対領域 Edition", # ホームサブタイトル
    "home.header.theme_combo.auto": "世界線収束 (Auto)", # テーマ：システムに従う
    "home.header.theme_combo.light": "光の加護 (Light)", # テーマ：ライトモード
    "home.header.theme_combo.dark": "深淵の凝視 (Dark)", # テーマ：ダークモード
    
    # Cache Card
    "home.cache_card.title": "魔力回路キャッシュ (Cache)", # キャッシュ設定
    "home.cache_card.clear_button": "🧹 残滓浄化", # キャッシュクリア
    "home.cache_card.path_placeholder": "ab-av1 一時ファイル保管場所...", # キャッシュパス入力欄のプレースホルダー
    "home.cache_card.browse_button": "座標固定", # キャッシュパス参照ボタン
    
    # Settings Card
    "home.settings_card.encoder.label": "魔力コア (Encoder)", # エンコーダー選択 (QSV/NVENC/AMF)
    "home.settings_card.vmaf.label": "視界還元度 (VMAF)", # VMAF 目標画質スコア
    "home.settings_card.bitrate.label": "共鳴周波数 (Bitrate)", # ビットレート制御
    "home.settings_card.preset.label": "詠唱速度 (Preset)", # エンコードプリセット (速度 vs 画質)
    "home.settings_card.offset.label": "霊力オフセット (Offset)", # ハードウェアエンコードパラメータ微調整
    "home.settings_card.loudnorm.label": "音量均一化術式 (Loudnorm)", # 音声ラウドネス統一
    "home.settings_card.nv_aq.label.nvidia": "NVIDIA 感知増強 (AQ)", # NVIDIA AQ 設定ラベル
    "home.settings_card.nv_aq.label.amd": "AMD 予備分析 (PreAnalysis)", # AMD PreAnalysis 設定ラベル
    "home.settings_card.nv_aq.label.intel": "Intel 深度分析 (Lookahead)", # Intel Lookahead 設定ラベル
    "home.settings_card.nv_aq.on": "展開", # 有効 (Enable)
    "home.settings_card.nv_aq.off": "収束", # 無効 (Disable)
    "home.settings_card.save_button": "💾 記憶銘刻 (Save)", # 設定保存
    "home.settings_card.reset_button": "↩️ 記憶回帰 (Reset)", # 設定リセット
    "home.settings_card.loudnorm_mode.auto": "調和の詠 (スマートバイパス)", # 自動 (Auto: 5.1/7.1 はラウドネス均一化を行わない)
    "home.settings_card.loudnorm_mode.always": "帰一の詠 (強制同調)", # 強制有効 (Always)
    "home.settings_card.loudnorm_mode.disable": "寂静の詠 (オリジナル保持)", # 無効 (Disable)
    
    # Action Card
    "home.action_card.save_mode.save_as": "新世界創造 (Save As)", # 名前を付けて保存
    "home.action_card.save_mode.overwrite": "元素上書き (Overwrite)", # 元ファイルを上書き
    "home.action_card.save_mode.remain": "元素保持 (Remain)", # 元ファイルを保持
    "home.action_card.export_path_placeholder": "新世界の座標...", # エクスポートパス入力欄のプレースホルダー
    "home.action_card.choose_button": "座標指定", # エクスポートパス選択ボタン
    "home.action_card.start_button": "✨ 契約締結 (Start)", # トランスコード開始
    "home.action_card.pause_button": "⏳ 時空凍結 (Pause)", # 一時停止
    "home.action_card.stop_button": " 契約破棄 (Stop)", # 停止
    
    # Source Card
    "home.source_card.title": "素材次元 (Source)", # 入力ソース設定
    "home.source_card.folder_button": "フォルダの名において", # フォルダ選択
    "home.source_card.file_button": "ファイルの名において", # ファイル選択
    
    # File List Card
    "home.file_list_card.title": "次元空間 (List)", # タスクリスト
    "home.file_list_card.clear_button": "虚無へ帰す", # リストクリア
    "home.file_list_card.placeholder": "素材を錬成陣に投入せよ...", # ファイルリストのプレースホルダー
    "list.item.remove_button": "追放", # リストからファイルを削除ボタン
    "list.item.duration_button": "時間軸観測", # リストで長さを表示ボタン
    
    # Status Bar
    "home.status_bar.current_label": "現在の錬成:", # ステータスバー現在のタスクラベル
    "home.status_bar.total_label": "全体進捗:", # ステータスバー全体進捗ラベル

    # -------------------------------------------------------------------------
    # Media Info Interface (view/info_interface.py)
    # -------------------------------------------------------------------------
    "info.title": "真理の目", # 「真理の目」ページタイトル
    "info.drop_card.title": "真理の目 · 物質解析", # 「真理の目」ページドラッグ＆ドロップカードタイトル
    "info.drop_card.hint": "未知の遺物をここに投入し、真理を覗く... (ファイルをドロップ)", # 「真理の目」ページドラッグ＆ドロップカードヒント
    "info.text_edit.placeholder": "魔力注入待機中... (Waiting for file drop)", # 「真理の目」ページテキストボックスプレースホルダー
    "info.buttons.add_to_list": "祭壇に奉納", # 「真理の目」ページリストに追加ボタン
    "info.buttons.clear": "因果切断", # 「真理の目」ページクリアボタン
    "info.buttons.copy": "報告書写本", # 「真理の目」ページレポートコピーボタン
    "info.analysis.in_progress": "✨ 真理を覗いています、お待ちください...", # 「真理の目」ページ解析中ヒント
    "info.infobar.copy_success.title": "写本完了", # 「真理の目」ページコピー成功ヒントタイトル
    "info.infobar.copy_success.content": "鑑定報告書が記憶水晶(クリップボード)に写されました。", # 「真理の目」ページコピー成功ヒント内容
    
    # Report Content
    "info.report.title": "📜 物質真理鑑定書",
    "info.report.perfect_form": "✨ 既に完全な形態です (Perfect Form)",
    "info.report.parse_error": "💥 解析失敗 (Error):",
    "info.report.container_title": "📦 容器構造 (Container)",
    "info.report.format": "• 封印術式 (Format):",
    "info.report.size": "• 物質総量 (Size):",
    "info.report.duration": "• 時間軸スパン (Duration):",
    "info.report.total_bitrate": "• 総合魔力流速 (Total Bitrate):",
    "info.report.stream_count": "• 構成元素数 (Stream Count):",
    "info.report.video_title": "👁️ 視覚投影 (Stream #{idx} - Video)",
    "info.report.codec": "• 構築術式 (Codec):",
    "info.report.profile_level": "• 術式階位 (Profile/Level):",
    "info.report.resolution": "• 視界解像度 (Resolution):",
    "info.report.pix_fmt": "• 粒子配列 (Pixel Format):",
    "info.report.color_space": "• 色彩領域 (Color Space):",
    "info.report.bitrate": "• 魔力流速 (Bitrate):",
    "info.report.audio_title": "🔊 聴覚共鳴 (Stream #{idx} - Audio)",
    "info.report.sample_rate": "• 共鳴周波数 (Sample Rate):",
    "info.report.sample_fmt": "• 波形精度 (Sample Format):",
    "info.report.channel_layout": "• 空間音場 (Channel Layout):",
    "info.report.subtitle_title": "📝 碑文記録 (Stream #{idx} - Subtitle)",
    "info.report.language": "• 碑文言語 (Language):",

    # -------------------------------------------------------------------------
    # Profile Interface (view/profile_interface.py)
    # -------------------------------------------------------------------------
    "profile.title": "観測者ファイル", # 「観測者ファイル」ページタイトル
    "profile.card.author_desc": "「 🌙 社畜 | 🎥 配信者 | 🛠️ ガジェット好き 」", # 「観測者ファイル」ページ作者説明
    "profile.card.author_motto": "「コードの海で魔法を探し、デジタルの世界で真理を観測する。」", # 「観測者ファイル」ページ作者のモットー
    "profile.buttons.bilibili": "📺 Bilibili", # 「観測者ファイル」ページBilibiliボタン
    "profile.buttons.youtube": "▶️ YouTube", # 「観測者ファイル」ページYouTubeボタン
    "profile.buttons.douyin": "🎵 Douyin", # 「観測者ファイル」ページDouyinボタン
    "profile.buttons.github": "🐙 GitHub", # 「観測者ファイル」ページGitHubボタン
    "profile.buttons.show_wizard": "✨ 入職ガイドを回想", # 「観測者ファイル」ページウェルカムウィザード表示ボタン

    # -------------------------------------------------------------------------
    # Credits Interface (view/credits_interface.py)
    # -------------------------------------------------------------------------
    "credits.title": "絆の証", # 「絆の証」ページタイトル
    "credits.card.contributor_role": "術式構築協力", # 「絆の証」ページ貢献者役割
    "credits.card.intro": "工房アップグレード貢献者、その偉業は以下の通り：", # 「絆の証」ページ紹介
    "credits.contributions.item1.title": "新魔力循環システム", # 「絆の証」ページ貢献項目1タイトル
    "credits.contributions.item1.desc": "魔力流動の安定化", # 「絆の証」ページ貢献項目1説明
    "credits.contributions.item2.title": "コア詠唱基盤の固定", # 「絆の証」ページ貢献項目2タイトル
    "credits.contributions.item2.desc": "儀式安定性の向上", # 「絆の証」ページ貢献項目2説明
    "credits.contributions.item3.title": "聖遺物フレームワーク昇華", # 「絆の証」ページ貢献項目3タイトル
    "credits.contributions.item3.desc": "オープンソースとより強き力を", # 「絆の証」ページ貢献項目3説明
    "credits.contributions.item4.title": "錬成物ポータブル封入", # 「絆の証」ページ貢献項目4タイトル
    "credits.contributions.item4.desc": "霊体はより小さく、召喚はより速く", # 「絆の証」ページ貢献項目4説明
    "credits.contributions.item5.title": "錬成ツールチェーン再構築", # 「絆の証」ページ貢献項目5タイトル
    "credits.contributions.item5.desc": "より柔軟な術式配布をサポート", # 「絆の証」ページ貢献項目5説明
    "credits.contributions.item6.title": "自動化錬金工房", # 「絆の証」ページ貢献項目6タイトル
    "credits.contributions.item6.desc": "クラウドによる自動構築と配布", # 「絆の証」ページ貢献項目6説明
    "credits.card.footer": "特別感謝: PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # 「絆の証」ページフッター

    # -------------------------------------------------------------------------
    # Welcome Wizard (view/welcome_wizard.py)
    # -------------------------------------------------------------------------
    "welcome.wizard.title": "ようこそ、魔法少女工房へ ✨", # ウェルカムウィザードタイトル
    "welcome.wizard.page1.title": "はじめまして、適格者よ！", # ウェルカムウィザード1ページ目タイトル
    "welcome.wizard.page1.content": "これはNAS愛好家のためのAV1ハードウェアトランスコードツールです。\n\nIntel/NVIDIA/AMDグラフィックボードの演算能力を利用し、画質を肉眼で無劣化に保ちながら、動画サイズを30%-50%縮小します。\n\nそれでは、いくつかの重要な設定について説明しましょう...", # ウェルカムウィザード1ページ目内容
    "welcome.wizard.page2.title": "1. 魔力コア (Encoder)", # ウェルカムウィザード2ページ目タイトル
    "welcome.wizard.page2.content": "トランスコードエンジンの選択です。\n\n• Intel QSV: Arc dGPU / Ultra iGPU 向け。\n• NVIDIA NVENC: RTX 40 シリーズ向け。\n• AMD AMF: RX 7000 シリーズ / RDNA 3 iGPU 向け。\n\n起動時にハードウェアを自動検知するため、通常は手動変更不要です。", # ウェルカムウィザード2ページ目内容
    "welcome.wizard.page3.title": "2. 視界還元度 (VMAF)", # ウェルカムウィザード3ページ目タイトル
    "welcome.wizard.page3.content": "画質を決定する核心指標 (0-100) です。\n\n• 95+: 極上の画質、保存用に最適。\n• 93 (デフォルト): 黄金の均衡点、肉眼無劣化、サイズ縮小も顕著。\n• 90: 高圧縮率、モバイル視聴向け。\n\nデフォルトの 93.0 を推奨します。", # ウェルカムウィザード3ページ目内容
    "welcome.wizard.page4.title": "3. 詠唱速度 (Preset)", # ウェルカムウィザード4ページ目タイトル
    "welcome.wizard.page4.content": "エンコード速度と圧縮効率のバランス (1-7)。\n\n• 数字が小さい (1-3): 速度は遅いが、サイズは小さく画質は良い。\n• 数字が大きい (5-7): 速度は速いが、サイズは少し大きくなる。\n• デフォルト 4: 均衡の選択。\n\n放置エンコードなら 3 か 4 がおすすめ。", # ウェルカムウィザード4ページ目内容
    "welcome.wizard.page5.title": "4. 霊力オフセット (Offset)", # ウェルカムウィザード5ページ目タイトル
    "welcome.wizard.page5.content": "ハードウェアエンコーダー向けの微調整パラメータです。\n\nハードウェアごとの効率差を埋めるため、CPUで検出されたパラメータを修正します。\n• AMD デフォルト -6\n• NVIDIA デフォルト -4\n• Intel デフォルト -2\n\nこれにより、最終的な画質がVMAFの期待値に近づきます。", # ウェルカムウィザード5ページ目内容
    "welcome.wizard.next_button": "魔導書をめくる", # ウェルカムウィザード次へボタン
    "welcome.wizard.skip_button": "瞬間展開", # ウェルカムウィザードスキップボタン
    "welcome.wizard.start_button": "錬成開始", # ウェルカムウィザード開始ボタン

    # -------------------------------------------------------------------------
    # Dialogs
    # -------------------------------------------------------------------------
    "dialog.clear_list.title": "虚無へ帰しますか？", # リストクリア確認ダイアログタイトル
    "dialog.clear_list.content": "この操作は祭壇から全ての浄化対象を取り除き、因果律をリセットします。続けますか？", # リストクリア確認ダイアログ内容
    "dialog.clear_list.yes_button": "確定 (Void)", # リストクリア確認ダイアログ「はい」ボタン
    "dialog.clear_list.cancel_button": "取消 (Stay)", # リストクリア確認ダイアログ「キャンセル」ボタン
    "dialog.clear_cache.title": "魔力残滓を粛清しますか？", # キャッシュクリア確認ダイアログタイトル
    "dialog.clear_cache.content": "これらは錬成儀式中に生じた混沌の欠片 (*.temp.mkv) です。残しておくと世界線の安定に影響する可能性があります。\n\n対象領域：{path}\n\n粛清を実行すると、これらの欠片は完全に虚無へ帰し、復元できません。浄化術式を発動しますか？", # キャッシュクリア確認ダイアログ内容
    "dialog.clear_cache.yes_button": "浄化発動 (Purify)", # キャッシュクリア確認ダイアログ「はい」ボタン
    "dialog.clear_cache.cancel_button": "結界維持", # キャッシュクリア確認ダイアログ「キャンセル」ボタン
    "dialog.error.skip_button": "スキップして継続 (Skip)", # エラーダイアログ「スキップ」ボタン
    "dialog.error.stop_button": "緊急中断", # エラーダイアログ「停止」ボタン
    "dialog.dependency_missing.title": "⚠️ 結界破損警告 (Critical Error)", # 依存関係欠落ダイアログタイトル
    "dialog.dependency_missing.content": "うわぁ！大変です！(>_<)\n工房の魔力回路に深刻な断裂を検知しました！\n\n以下の核心聖遺物が家出しているようです：\n{missing_files}\n\nこれらが無いと、錬成儀式は行えません！\n至急、工房ディレクトリに召喚してください！", # 依存関係欠落ダイアログ内容
    "dialog.dependency_missing.yes_button": "支援要請", # 依存関係欠落ダイアログ「はい」ボタン
    "dialog.dependency_missing.cancel_button": "了解した", # 依存関係欠落ダイアログ「キャンセル」ボタン
    "dialog.language_change.title": "世界線変動確認", # 言語変更ダイアログタイトル
    "dialog.language_change.content": "世界線を新たな言語領域へ収束させるため、観測端末の再起動を推奨します。", # 言語変更ダイアログ内容
    "dialog.language_change.yes_button": "御意", # 言語変更ダイアログ「はい」ボタン
    "dialog.language_change.cancel_button": "また後で", # 言語変更ダイアログ「キャンセル」ボタン
    "dialog.encoder.crash_title": "術式崩壊警告", # エンコーダークラッシュ警告タイトル
    "dialog.encoder.crash_content": "任務 {fname} が未知のエラーに遭遇しました。\nこの任務をスキップして続けますか？", # エンコーダークラッシュ警告内容

    # -------------------------------------------------------------------------
    # InfoBars / Notifications
    # -------------------------------------------------------------------------
    "infobar.success.settings_saved.title": "記憶銘刻完了", # 設定保存成功ヒントタイトル
    "infobar.success.settings_saved.content": "現在の術式パラメータが虚空の記憶 (config.ini) に刻まれました。", # 設定保存成功ヒント内容
    "infobar.success.files_added.title": "素材投入成功", # ファイル追加成功ヒントタイトル
    "infobar.success.files_added.content": "{count} 個の素材を錬成陣に投入しました。", # ファイル追加成功ヒント内容
    "infobar.success.drag_drop_added.content": "空間転送により {count} 個の素材が投入されました。", # ドラッグ＆ドロップファイル追加成功ヒント内容
    "infobar.success.cache_cleared.title": "浄化完了", # キャッシュクリア成功ヒントタイトル
    "infobar.success.cache_cleared.content": "{count} 個の魔力残滓を消去しました！", # キャッシュクリア成功ヒント内容
    "infobar.success.synced.title": "同期成功", # 同期成功ヒントタイトル
    "infobar.success.synced.content": "対象物質は正常に祭壇へ格納されました！", # 同期成功ヒント内容
    "infobar.info.settings_reset.title": "記憶回帰成功", # 設定リセットヒントタイトル
    "infobar.info.settings_reset.content": "パラメータは初期形態へリセットされました。", # 設定リセットヒント内容
    "infobar.warning.no_files_selected.title": "魔力不足", # ファイル未選択警告ヒントタイトル
    "infobar.warning.no_files_selected.content": "まずは浄化する対象を指定してください！", # ファイル未選択警告ヒント内容
    "infobar.warning.no_export_dir.title": "座標消失", # エクスポートディレクトリ未選択警告ヒントタイトル
    "infobar.warning.no_export_dir.content": "現在は「新世界創造」モードです。新世界の座標を指定してください！", # エクスポートディレクトリ未選択警告ヒント内容
    "infobar.warning.no_files_found.title": "素材探知失敗", # ファイル未発見警告ヒントタイトル
    "infobar.warning.no_files_found.content": "この次元には錬成可能な素材が見当たりません。", # ファイル未発見警告ヒント内容
    "infobar.warning.no_new_files_dropped.title": "投入失敗", # 新規ファイル未追加警告ヒントタイトル
    "infobar.warning.no_new_files_dropped.content": "投入された素材は無効か、既に魔法陣に存在します。", # 新規ファイル未追加警告ヒント内容
    "infobar.warning.task_running.title": "術式進行中", # タスク実行中警告ヒントタイトル
    "infobar.warning.task_running.content": "錬成儀式はまだ終わっていません。次元空間の強制リセットは不可能です！", # タスク実行中警告ヒント内容
    "infobar.warning.invalid_cache_path.title": "座標無効", # 無効なキャッシュパス警告ヒントタイトル
    "infobar.warning.invalid_cache_path.content": "有効な魔力バッファ領域を指定してください...", # 無効なキャッシュパス警告ヒント内容
    "infobar.warning.dependency_check_skipped.title": "魔力コア再検知スキップ", # 依存関係チェックのスキップ警告ヒントタイトル
    "infobar.warning.dependency_check_skipped.content": "現在錬成中のため、任務停止後に記憶回帰を行うことで自己診断が発動します。", # 依存関係チェックのスキップ警告ヒント内容
    "infobar.warning.hardware_unsupported.title": "聖遺物拒絶反応", # ハードウェア非対応警告ヒントタイトル
    "infobar.warning.hardware_unsupported.content": "汝の聖遺物はここの魔力と同調できないようです。(ハードウェア非対応またはドライバエラー)", # ハードウェア非対応警告ヒント内容
    "infobar.warning.duplicate_dependency_check.content": "自己診断術式は既に実行中です。二重詠唱は避けてください。", # 重複依存関係チェック警告ヒント内容
    "infobar.error.vmaf_not_number.title": "術式構成エラー", # VMAF 非数値エラーヒントタイトル
    "infobar.error.vmaf_not_number.content": "視界還元度は数秘術文字 (例: 93.0) で構成されなければなりません。", # VMAF 非数値エラーヒント内容
    "infobar.error.cache_clear_failed.title": "浄化術式反動", # キャッシュクリア失敗エラーヒントタイトル
    "infobar.copy_warning.title": "虚無", # 「真理の目」ページコピー警告ヒントタイトル
    "infobar.copy_warning.content": "まだ何も物質解析されていません...", # 「真理の目」ページコピー警告ヒント内容

    # -------------------------------------------------------------------------
    # Core / Worker / Logger
    # -------------------------------------------------------------------------
    "common.unknown_error": "名状しがたきエラー", # 一般的な不明なエラー
    "dependency.ffmpeg_desc": "核心術式構築 (FFmpeg)", # FFmpeg 説明
    "dependency.ffprobe_desc": "真理の目コンポーネント (FFprobe)", # FFprobe 説明
    "dependency.ab_av1_desc": "極限詠唱触媒 (ab-av1)", # ab-av1 説明
    
    # Button States
    "button.start.in_progress": "✨ 奇跡発動中...", # 開始ボタン進行中状態
    "button.save.saved": "✅ 銘刻完了", # 保存ボタン保存済み状態
    "button.reset.restored": "✅ 回帰完了", # リセットボタン復元済み状態
    "button.start.missing_components": "🚫 コンポーネント欠落", # 開始ボタンコンポーネント欠落状態

    # Logs
    "log.system_ready": "システムスタンバイ... {kaomoji}", # システム準備完了ログ
    "log.dependency_check_start": ">>> 環境自己診断術式を起動中 (Initializing environment check)...", # 依存関係チェック開始ログ
    "log.dependency_check_finished.success": ">>> 適格者認証パス：", # 依存関係チェック成功ログ
    "log.dependency_check_finished.fail": ">>> 警告：有効なAV1ハードウェアエンコーダー (QSV/NVENC/AMF) が検知されませんでした。", # 依存関係チェック失敗ログ
    "log.autoselect_encoder": ">>> 自動的に {encoder} 術式へ切り替えました。", # エンコーダー自動選択ログ
    "log.recalibrating": ">>> 魔力コアの可用性を再校正中 (Re-calibrating)...", # 再校正ログ
    "log.list_cleared": ">>> 祭壇は空になりました。全ての因果律はリセットされました。(Voided)", # リストクリアログ
    "log.task_pause": ">>> 固有結界凍結 (Paused)...", # タスク一時停止ログ
    "log.task_resume": ">>> 時空流動再開...", # タスク再開ログ
    "log.task_stop_request": ">>> 中止要請中...", # タスク停止要求ログ
    "log.fatal_error_component_missing": ">>> 致命的エラー：重要コンポーネント欠落、システム停止。", # コンポーネント欠落致命的エラーログ
    "log.dependency.qsv_failed": ">>> Intel QSV 自己診断不合格: {error}", # QSV 自己診断失敗ログ
    "log.dependency.qsv_exception": ">>> Intel QSV 検知異常: {error}", # QSV 検知異常ログ
    "log.dependency.nvenc_unsupported_gpu": ">>> ヒント: NVIDIA グラボを検知しましたが、このモデルは AV1 ハードウェアエンコードをサポートしていません (RTX 40 シリーズが必要)。", # NVENC 非対応ログ
    "log.dependency.nvenc_failed": ">>> NVENC 自己診断不合格: {error}", # NVENC 自己診断失敗ログ
    "log.dependency.nvenc_exception": ">>> NVENC 検知異常: {error}", # NVENC 検知異常ログ
    "log.dependency.amf_failed": ">>> AMD AMF 自己診断不合格: {error}", # AMF 自己診断失敗ログ
    "log.dependency.amf_exception": ">>> AMD AMF 検知異常: {error}", # AMF 検知異常ログ
    "log.dependency.check_exception": ">>> 環境自己診断異常: {error}", # 環境自己診断異常ログ
    "log.encoder.no_files_found": "魔力残留を検知できません... (｡•ˇ‸ˇ•｡)", # ファイル未発見ログ
    "log.encoder.tasks_found": "{total_tasks} 個の浄化対象異変体を捕捉！( •̀ ω •́ )y", # タスク発見ログ
    "log.encoder.task_start": "[{i}/{total_tasks}] {fname} に対して固有結界を展開中...", # タスク開始ログ
    "log.encoder.skip_av1": " -> この物質は既に純粋形態 (AV1) です、スキップします~ (Pass)", # AV1 スキップログ
    "log.encoder.status_skipped": "✨ スキップ", # ステータス：スキップ
    "log.encoder.status_duration": "所要時間: {total_duration:.2f}s", # ステータス：所要時間
    "log.encoder.ab_av1_fallback": " -> 予備プランを試行: {desc}...", # ab-av1 予備プランログ
    "log.encoder.ab_av1_start": " -> 最強術式を推演中 (ab-av1)...", # ab-av1 開始ログ
    "log.encoder.ab_av1_probing": "    -> 探査中: {probe_crf} => VMAF: {vmaf_val}", # ab-av1 探査ログ
    "log.encoder.ab_av1_success_offset_corrected": " -> 術式解析完了 ({desc}): 原始CRF {cpu_crf} + オフセット {offset} = {raw_icq} ({reason}制限により {best_icq} に修正) [所要時間: {search_duration:.1f}s]", # ab-av1 成功(修正)ログ
    "log.encoder.ab_av1_success_offset": " -> 術式解析完了 ({desc}): 原始CRF {cpu_crf} + オフセット {offset} => 最終パラメータ {best_icq} [所要時間: {search_duration:.1f}s]", # ab-av1 成功(オフセット)ログ
    "log.encoder.ab_av1_success": " -> 術式解析完了 (ICQ): {best_icq} [所要時間: {search_duration:.1f}s] (๑•̀ㅂ•́)و✧", # ab-av1 成功ログ
    "log.encoder.ab_av1_failed": " -> 解析失敗、基礎術式を強制使用 ICQ: {best_icq} (T_T)", # ab-av1 失敗ログ
    "log.encoder.ab_av1_error_log_header": "    [ab-av1 エラー回想]:", # ab-av1 エラーヘッダーログ
    "log.encoder.icq_corrected": " -> 修正: ハードウェアエンコーダーパラメータ制限 ({icq} -> 51)", # ICQ 修正ログ
    "log.encoder.ffmpeg_exception": " -> 魔力逆流: {error} (×_×)", # FFmpeg 異常ログ
    "log.encoder.success_overwrite": " -> 浄化完了！旧世界は書き換えられました (Overwrite) (ﾉ>ω<)ﾉ [圧制: {encode_duration:.1f}s | 総時間: {total_duration:.1f}s]", # 成功(上書き)ログ
    "log.encoder.error_move_overwrite": "ソースファイルを置換できません。他のプログラムが使用中の可能性があります。", # 移動上書き失敗ログ
    "log.encoder.success_remain": " -> 浄化完了！元素は保持され、最適化体が生成されました (Remain) (ﾉ>ω<)ﾉ [圧制: {encode_duration:.1f}s | 総時間: {total_duration:.1f}s]", # 成功(保持)ログ
    "log.encoder.success_save_as": " -> 浄化完了！新世界が確立されました (Save As) (ﾉ>ω<)ﾉ [圧制: {encode_duration:.1f}s | 総時間: {total_duration:.1f}s]", # 成功(名前を付けて保存)ログ
    "log.encoder.status_done": "✅ 完了", # ステータス：完了
    "log.encoder.error_move": " -> 封印儀式失敗: {error} (T_T)", # ファイル移動失敗ログ
    "log.encoder.ffmpeg_crash": " -> 術式暴走 (Crash)... (T_T)", # FFmpeg クラッシュログ
    "log.encoder.cooling_down": " -> 魔術回路冷却中 (Cooling down GPU)...", # 冷却ログ
    "log.encoder.all_done": ">>> 奇跡達成！(๑•̀ㅂ•́)و✧", # 全完了ログ
    "log.encoder.stopped": ">>> 契約が強制切断されました。", # 停止ログ
    "log.encoder.fatal_error": "世界線変動率異常 (Fatal): {error}", # 致命的エラーログ
    "log.encoder.info_multichannel": " -> 多重音場 ({channels}ch) を感知、現状を維持します。", # 多チャンネル情報ログ
    "log.encoder.info_loudnorm_enabled": " -> 音場調和 (Loudnorm): 有効 ({mode})", # ラウドネス均一化有効ログ
    "log.encoder.info_loudnorm_skipped": " -> 音場調和 (Loudnorm): スキップ ({mode})", # ラウドネス均一化スキップログ
}