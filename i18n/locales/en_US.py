language_name = "English"

# This is a language file full of "Chunibyo" style (Anime/Magic settings).
# The comments on the right correspond to the actual technical functions.
translation = {
    # -------------------------------------------------------------------------
    # Main Window (main.py)
    # -------------------------------------------------------------------------
    "app.title": "Magical Girl Workshop", # Application Main Title
    "app.subtitle": "AV1 Hardware Acceleration Mana Drive · Absolute Territory Edition", # Application Subtitle
    "app.welcome": "Welcome to the Magical Girl Workshop ✨", # Welcome Message
    "app.designed_by": "Designed by <a href='https://space.bilibili.com/136850' style='color: #FB7299; text-decoration: none; font-weight: bold;'>LingMoe404</a> | Powered by Python, PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # Designer and Tech Support Info

    # -------------------------------------------------------------------------
    # Home Interface (view/home_interface.py)
    # -------------------------------------------------------------------------
    "home.title": "Alchemy Altar", # Home
    "home.header.title": "Alchemy Altar", # Home Title
    "home.header.subtitle": "AV1 Hardware Acceleration Mana Drive · Absolute Territory Edition", # Home Subtitle
    "home.header.theme_combo.auto": "World Line Convergence (Auto)", # Theme: Follow System
    "home.header.theme_combo.light": "Blessing of Light (Light)", # Theme: Light Mode
    "home.header.theme_combo.dark": "Abyssal Gaze (Dark)", # Theme: Dark Mode
    
    # Cache Card
    "home.cache_card.title": "Mana Circuit Buffer (Cache)", # Cache Settings
    "home.cache_card.clear_button": "🧹 Purify Residue", # Clear Cache
    "home.cache_card.path_placeholder": "ab-av1 temporary file storage...", # Cache Path Placeholder
    "home.cache_card.browse_button": "Lock Coordinates", # Browse Cache Path Button
    
    # Settings Card
    "home.settings_card.encoder.label": "Mana Core (Encoder)", # Encoder Selection (QSV/NVENC/AMF)
    "home.settings_card.vmaf.label": "Vision Restoration (VMAF)", # VMAF Target Quality Score
    "home.settings_card.bitrate.label": "Resonance Freq (Bitrate)", # Bitrate Control
    "home.settings_card.preset.label": "Chanting Speed (Preset)", # Encoding Preset (Speed vs Quality)
    "home.settings_card.offset.label": "Spiritual Offset (Offset)", # Hardware Encoding Parameter Fine-tuning
    "home.settings_card.loudnorm.label": "Loudness Spell (Loudnorm)", # Audio Loudness Normalization
    "home.settings_card.nv_aq.label.nvidia": "NVIDIA Perception Boost (AQ)", # NVIDIA AQ Setting Label
    "home.settings_card.nv_aq.label.amd": "AMD Pre-Analysis", # AMD PreAnalysis Setting Label
    "home.settings_card.nv_aq.label.intel": "Intel Deep Analysis (Lookahead)", # Intel Lookahead Setting Label
    "home.settings_card.nv_aq.on": "Deploy", # Enable
    "home.settings_card.nv_aq.off": "Converge", # Disable
    "home.settings_card.save_button": "💾 Inscribe Memory (Save)", # Save Settings
    "home.settings_card.reset_button": "↩️ Time Reversal (Reset)", # Reset Settings
    "home.settings_card.loudnorm_mode.auto": "Harmonic Chant (Smart Bypass)", # Auto (Auto: 5.1/7.1 do not normalize)
    "home.settings_card.loudnorm_mode.always": "Unified Chant (Forced Sync)", # Force Enable (Always)
    "home.settings_card.loudnorm_mode.disable": "Silent Chant (Original Form)", # Disable
    "home.settings_card.color_mode.label": "Color Vision (Color Mode)",
    "home.settings_card.color_mode.auto": "Preserve HDR (Auto)",
    "home.settings_card.color_mode.tonemap": "Color Harmony (Tone Map)",
    "home.settings_card.color_mode.sdr": "Force regular SDR (Force SDR)",
    
    # Action Card
    "home.action_card.save_mode.save_as": "Create New World (Save As)", # Save As
    "home.action_card.save_mode.overwrite": "Element Overwrite (Overwrite)", # Overwrite Original File
    "home.action_card.save_mode.remain": "Element Remain (Remain)", # Keep Source File
    "home.action_card.export_path_placeholder": "New World Coordinates...", # Export Path Placeholder
    "home.action_card.choose_button": "Designate Coords", # Choose Export Path Button
    "home.action_card.start_button": "✨ Form Pact (Start)", # Start Transcoding
    "home.action_card.pause_button": "⏳ Time Freeze (Pause)", # Pause
    "home.action_card.stop_button": " Break Pact (Stop)", # Stop
    "home.action_card.concurrency.mode_label": "Transcode Concurrency",
    "home.action_card.concurrency.count_label": "Manual Workers",
    "home.action_card.concurrency.auto": "Automatic",
    "home.action_card.concurrency.manual": "Manual",
    "home.action_card.concurrency.idle": "Concurrency scheduler ready",
    
    # Source Card
    "home.source_card.title": "Material Dimension (Source)", # Input Source Settings
    "home.source_card.folder_button": "In Name of Folder", # Choose Folder
    "home.source_card.file_button": "In Name of File", # Choose File
    
    # File List Card
    "home.file_list_card.title": "Dimensional Space (List)", # Task List
    "home.file_list_card.clear_button": "Return to Void", # Clear List
    "home.file_list_card.placeholder": "Cast materials into the transmutation circle...", # File List Placeholder
    "list.item.remove_button": "Banish", # Remove File Button
    "list.item.duration_button": "Peek Timeline", # View Duration Button
    
    # Status Bar
    "home.status_bar.current_label": "Current Alchemy:", # Status Bar Current Task Label
    "home.status_bar.total_label": "Total Progress:", # Status Bar Total Progress Label

    # -------------------------------------------------------------------------
    # Media Info Interface (view/info_interface.py)
    # -------------------------------------------------------------------------
    "info.title": "Eye of Truth", # "Eye of Truth" Page Title
    "info.drop_card.title": "Eye of Truth · Material Analysis", # "Eye of Truth" Page Drop Card Title
    "info.drop_card.hint": "Cast unknown relics here to peek at the truth... (Drop File)", # "Eye of Truth" Page Drop Card Hint
    "info.text_edit.placeholder": "Awaiting Mana Injection... (Waiting for file drop)", # "Eye of Truth" Page Text Box Placeholder
    "info.buttons.add_to_list": "Offer to Altar", # "Eye of Truth" Page Add to List Button
    "info.buttons.clear": "Sever Causality", # "Eye of Truth" Page Clear Button
    "info.buttons.copy": "Transcribe Report", # "Eye of Truth" Page Copy Report Button
    "info.analysis.in_progress": "✨ Peeking at the truth, please wait...", # "Eye of Truth" Page Analysis In Progress Hint
    "info.infobar.copy_success.title": "Transcription Complete", # "Eye of Truth" Page Copy Success Title
    "info.infobar.copy_success.content": "Appraisal report transcribed to Memory Crystal (Clipboard).", # "Eye of Truth" Page Copy Success Content
    
    # Report Content
    "info.report.title": "📜 Material Truth Appraisal",
    "info.report.perfect_form": "✨ Already in Perfect Form",
    "info.report.parse_error": "💥 Analysis Failed (Error):",
    "info.report.container_title": "📦 Container Structure (Container)",
    "info.report.format": "• Seal Spell (Format):",
    "info.report.size": "• Material Mass (Size):",
    "info.report.duration": "• Timeline Span (Duration):",
    "info.report.total_bitrate": "• Total Mana Flow (Total Bitrate):",
    "info.report.stream_count": "• Element Count (Stream Count):",
    "info.report.video_title": "👁️ Visual Projection (Stream #{idx} - Video)",
    "info.report.codec": "• Construction Spell (Codec):",
    "info.report.profile_level": "• Spell Tier (Profile/Level):",
    "info.report.resolution": "• Vision Resolution (Resolution):",
    "info.report.pix_fmt": "• Particle Array (Pixel Format):",
    "info.report.color_space": "• Color Domain (Color Space):",
    "info.report.bitrate": "• Mana Flow (Bitrate):",
    "info.report.audio_title": "🔊 Auditory Resonance (Stream #{idx} - Audio)",
    "info.report.sample_rate": "• Resonance Freq (Sample Rate):",
    "info.report.sample_fmt": "• Waveform Precision (Sample Format):",
    "info.report.channel_layout": "• Spatial Sound Field (Channel Layout):",
    "info.report.subtitle_title": "📝 Inscription Record (Stream #{idx} - Subtitle)",
    "info.report.language": "• Inscription Language (Language):",

    # -------------------------------------------------------------------------
    # Profile Interface (view/profile_interface.py)
    # -------------------------------------------------------------------------
    "profile.title": "Observer Archives", # "Observer Archives" Page Title
    "profile.card.author_desc": "「 🌙 Salaryman | 🎥 Content Creator | 🛠️ Tech Enthusiast 」", # "Observer Archives" Page Author Description
    "profile.card.author_motto": "“Seeking magic in the sea of code, observing truth in the digital world.”", # "Observer Archives" Page Author Motto
    "profile.buttons.bilibili": "📺 Bilibili", # "Observer Archives" Page Bilibili Button
    "profile.buttons.youtube": "▶️ YouTube", # "Observer Archives" Page YouTube Button
    "profile.buttons.douyin": "🎵 Douyin", # "Observer Archives" Page Douyin Button
    "profile.buttons.github": "🐙 GitHub", # "Observer Archives" Page GitHub Button
    "profile.buttons.show_wizard": "✨ Revisit Induction Guide", # "Observer Archives" Page Show Welcome Wizard Button

    # -------------------------------------------------------------------------
    # Credits Interface (view/credits_interface.py)
    # -------------------------------------------------------------------------
    "credits.title": "Proof of Bond", # "Proof of Bond" Page Title
    "credits.card.contributor_role": "Spell Construction Co-op", # "Proof of Bond" Page Contributor Role
    "credits.card.intro": "Workshop Upgrade Contributors, their feats are as follows:", # "Proof of Bond" Page Intro
    "credits.contributions.item1.title": "New Mana Cycle System", # "Proof of Bond" Page Contribution Item 1 Title
    "credits.contributions.item1.desc": "Optimized Mana Flow Stability", # "Proof of Bond" Page Contribution Item 1 Description
    "credits.contributions.item2.title": "Solidified Core Chant Base", # "Proof of Bond" Page Contribution Item 2 Title
    "credits.contributions.item2.desc": "Improved Ritual Stability", # "Proof of Bond" Page Contribution Item 2 Description
    "credits.contributions.item3.title": "Relic Framework Upgrade", # "Proof of Bond" Page Contribution Item 3 Title
    "credits.contributions.item3.desc": "Embracing Open Source & Greater Power", # "Proof of Bond" Page Contribution Item 3 Description
    "credits.contributions.item4.title": "Portable Alchemy Encapsulation", # "Proof of Bond" Page Contribution Item 4 Title
    "credits.contributions.item4.desc": "Smaller Spirits, Faster Summoning", # "Proof of Bond" Page Contribution Item 4 Description
    "credits.contributions.item5.title": "Reforged Alchemy Toolchain", # "Proof of Bond" Page Contribution Item 5 Title
    "credits.contributions.item5.desc": "Supporting Flexible Spell Distribution", # "Proof of Bond" Page Contribution Item 5 Description
    "credits.contributions.item6.title": "Automated Alchemy Workshop", # "Proof of Bond" Page Contribution Item 6 Title
    "credits.contributions.item6.desc": "Cloud Automated Construction & Distribution", # "Proof of Bond" Page Contribution Item 6 Description
    "credits.card.footer": "Special Thanks: PySide6, QFluentWidgets, FFmpeg, ab-av1, Gemini", # "Proof of Bond" Page Footer

    # -------------------------------------------------------------------------
    # Welcome Wizard (view/welcome_wizard.py)
    # -------------------------------------------------------------------------
    "welcome.wizard.title": "Welcome to Magical Girl Workshop ✨", # Welcome Wizard Title
    "welcome.wizard.page1.title": "Nice to meet you, Chosen One!", # Welcome Wizard Page 1 Title
    "welcome.wizard.page1.content": "This is an AV1 hardware transcoding tool built for NAS hoarders.\n\nIt utilizes the computing power of Intel/NVIDIA/AMD graphics cards to reduce video size by 30%-50% while maintaining visually lossless quality.\n\nNext, let me introduce a few key settings...", # Welcome Wizard Page 1 Content
    "welcome.wizard.page2.title": "1. Mana Core (Encoder)", # Welcome Wizard Page 2 Title
    "welcome.wizard.page2.content": "This is the choice of transcoding engine.\n\n• Intel QSV: For Arc dGPU / Ultra iGPU.\n• NVIDIA NVENC: For RTX 40 series.\n• AMD AMF: For RX 7000 series / RDNA 3 iGPU.\n\nThe program automatically detects your hardware on startup, usually no manual change needed.", # Welcome Wizard Page 2 Content
    "welcome.wizard.page3.title": "2. Vision Restoration (VMAF)", # Welcome Wizard Page 3 Title
    "welcome.wizard.page3.content": "The core indicator determining image quality (0-100).\n\n• 95+: Extreme quality, for archiving.\n• 93 (Default): Golden balance, visually lossless, significant size reduction.\n• 90: High compression, for mobile viewing.\n\nRecommended to keep default 93.0.", # Welcome Wizard Page 3 Content
    "welcome.wizard.page4.title": "3. Chanting Speed (Preset)", # Welcome Wizard Page 4 Title
    "welcome.wizard.page4.content": "Balance between encoding speed and compression efficiency (1-7).\n\n• Lower number (1-3): Slower speed, smaller size, better quality.\n• Higher number (5-7): Faster speed, slightly larger size.\n• Default 4: Balanced choice.\n\nRecommended 3 or 4 for overnight batch processing.", # Welcome Wizard Page 4 Content
    "welcome.wizard.page5.title": "4. Spiritual Offset (Offset)", # Welcome Wizard Page 5 Title
    "welcome.wizard.page5.content": "Fine-tuning parameter for hardware encoders.\n\nSince hardware encoders vary in efficiency, we need to correct the parameters detected by CPU.\n• AMD Default -6\n• NVIDIA Default -4\n• Intel Default -2\n\nThis ensures final quality matches your VMAF expectations.", # Welcome Wizard Page 5 Content
    "welcome.wizard.next_button": "Read Grimoire", # Welcome Wizard Next Button
    "welcome.wizard.skip_button": "Instant Deploy", # Welcome Wizard Skip Button
    "welcome.wizard.start_button": "Start Alchemy", # Welcome Wizard Start Button

    # -------------------------------------------------------------------------
    # Dialogs
    # -------------------------------------------------------------------------
    "dialog.clear_list.title": "Confirm Return to Void?", # Clear List Confirm Dialog Title
    "dialog.clear_list.content": "This operation will remove all anomalies from the altar, resetting causality. Are you sure?", # Clear List Confirm Dialog Content
    "dialog.clear_list.yes_button": "Confirm (Void)", # Clear List Confirm Dialog "Yes" Button
    "dialog.clear_list.cancel_button": "Cancel (Stay)", # Clear List Confirm Dialog "Cancel" Button
    "dialog.clear_cache.title": "Confirm Purge of Mana Residue?", # Clear Cache Confirm Dialog Title
    "dialog.clear_cache.content": "These are chaotic fragments (*.temp.mkv) generated during alchemy. Keeping them might disturb the world line stability.\n\nTarget Area: {path}\n\nOnce purged, these fragments will return to void forever. Invoke purification spell?", # Clear Cache Confirm Dialog Content
    "dialog.clear_cache.yes_button": "Invoke Purification (Purify)", # Clear Cache Confirm Dialog "Yes" Button
    "dialog.clear_cache.cancel_button": "Maintain Barrier", # Clear Cache Confirm Dialog "Cancel" Button
    "dialog.error.skip_button": "Skip & Continue (Skip)", # Error Dialog "Skip" Button
    "dialog.error.stop_button": "Emergency Halt", # Error Dialog "Stop" Button
    "dialog.dependency_missing.title": "⚠️ Barrier Breach Warning (Critical Error)", # Dependency Missing Dialog Title
    "dialog.dependency_missing.content": "Whoa! Bad news! (>_<)\nThe workshop's mana circuits detected a severe rupture!\n\nThe following core relics seem to have run away from home:\n{missing_files}\n\nWithout them, the alchemy ritual cannot proceed!\nPlease summon them back to the workshop directory ASAP!", # Dependency Missing Dialog Content
    "dialog.dependency_missing.yes_button": "Summon Support", # Dependency Missing Dialog "Yes" Button
    "dialog.dependency_missing.cancel_button": "Understood", # Dependency Missing Dialog "Cancel" Button
    "dialog.language_change.title": "World Line Shift Confirmation", # Language Change Dialog Title
    "dialog.language_change.content": "To converge the world line to the new linguistic domain, restarting the observation terminal is recommended.", # Language Change Dialog Content
    "dialog.language_change.yes_button": "As You Command", # Language Change Dialog "Yes" Button
    "dialog.language_change.cancel_button": "In a Moment", # Language Change Dialog "Cancel" Button
    "dialog.encoder.crash_title": "Spell Collapse Warning", # Encoder Crash Warning Title
    "dialog.encoder.crash_content": "Task {fname} encountered an unknown error.\nSkip this task and continue?", # Encoder Crash Warning Content

    # -------------------------------------------------------------------------
    # InfoBars / Notifications
    # -------------------------------------------------------------------------
    "infobar.success.settings_saved.title": "Memory Inscribed", # Settings Saved Success Title
    "infobar.success.settings_saved.content": "Current spell parameters inscribed to Void Memory (config.ini)", # Settings Saved Success Content
    "infobar.success.files_added.title": "Material Input Success", # Files Added Success Title
    "infobar.success.files_added.content": "Cast {count} materials into the transmutation circle.", # Files Added Success Content
    "infobar.success.drag_drop_added.content": "Input {count} materials via spatial teleportation.", # Drag Drop Files Added Success Content
    "infobar.success.cache_cleared.title": "Purification Complete", # Cache Cleared Success Title
    "infobar.success.cache_cleared.content": "Purged {count} mana residues!", # Cache Cleared Success Content
    "infobar.success.synced.title": "Sync Successful", # Sync Success Title
    "infobar.success.synced.content": "The substance has been successfully integrated into the altar!", # Sync Success Content
    "infobar.info.settings_reset.title": "Memory Reversal Successful", # Settings Reset Title
    "infobar.info.settings_reset.content": "Parameters reset to initial form", # Settings Reset Content
    "infobar.warning.no_files_selected.title": "Insufficient Mana", # No Files Selected Warning Title
    "infobar.warning.no_files_selected.content": "Please designate targets for purification first!", # No Files Selected Warning Content
    "infobar.warning.no_export_dir.title": "Coordinates Lost", # No Export Directory Warning Title
    "infobar.warning.no_export_dir.content": "Currently in 'Create New World' mode, please designate coordinates for the new world!", # No Export Directory Warning Content
    "infobar.warning.no_files_found.title": "Material Detection Failed", # No Files Found Warning Title
    "infobar.warning.no_files_found.content": "No transmutable materials found in this dimension.", # No Files Found Warning Content
    "infobar.warning.no_new_files_dropped.title": "Input Failed", # No New Files Dropped Warning Title
    "infobar.warning.no_new_files_dropped.content": "Input materials are invalid or already exist in the magic circle.", # No New Files Dropped Warning Content
    "infobar.warning.task_running.title": "Spell in Progress", # Task Running Warning Title
    "infobar.warning.task_running.content": "Alchemy ritual is not over, cannot forcibly reset dimensional space!", # Task Running Warning Content
    "infobar.warning.invalid_cache_path.title": "Invalid Coordinates", # Invalid Cache Path Warning Title
    "infobar.warning.invalid_cache_path.content": "Please designate a valid mana buffer zone...", # Invalid Cache Path Warning Content
    "infobar.warning.dependency_check_skipped.title": "Mana Core Re-check Skipped", # Dependency Check Skipped Warning Title
    "infobar.warning.dependency_check_skipped.content": "Alchemy in progress. Perform memory reversal after stopping task to trigger self-check.", # Dependency Check Skipped Warning Content
    "infobar.warning.hardware_unsupported.title": "Relic Rejection Reaction", # Hardware Unsupported Warning Title
    "infobar.warning.hardware_unsupported.content": "Thy relic seems unable to synchronize with the mana here. (Hardware unsupported or driver error)", # Hardware Unsupported Warning Content
    "infobar.warning.duplicate_dependency_check.content": "Self-check spell already running, do not double chant.", # Duplicate Dependency Check Warning Content
    "infobar.error.vmaf_not_number.title": "Spell Composition Error", # VMAF Not Number Error Title
    "infobar.error.vmaf_not_number.content": "Vision Restoration Level must be composed of numeric runes (e.g. 93.0)", # VMAF Not Number Error Content
    "infobar.error.cache_clear_failed.title": "Purification Spell Backfire", # Cache Clear Failed Error Title
    "infobar.copy_warning.title": "Void", # Copy Warning Title
    "infobar.copy_warning.content": "No material analyzed yet...", # Copy Warning Content

    # -------------------------------------------------------------------------
    # Core / Worker / Logger
    # -------------------------------------------------------------------------
    "common.unknown_error": "Unspeakable Error", # Common Unknown Error
    "dependency.ffmpeg_desc": "Core Spell Construction (FFmpeg)", # FFmpeg Description
    "dependency.ffprobe_desc": "Eye of Truth Component (FFprobe)", # FFprobe Description
    "dependency.ab_av1_desc": "Limit Chant Catalyst (ab-av1)", # ab-av1 Description
    
    # Button States
    "button.start.in_progress": "✨ Miracle in Progress...", # Start Button In Progress State
    "button.save.saved": "✅ Inscribed", # Save Button Saved State
    "button.reset.restored": "✅ Reversed", # Reset Button Restored State
    "button.start.missing_components": "🚫 Missing Components", # Start Button Missing Components State

    # Logs
    "log.system_ready": "System Ready... {kaomoji}", # System Ready Log
    "log.dependency_check_start": ">>> Initializing environment check spell...", # Dependency Check Start Log
    "log.dependency_check_finished.success": ">>> Chosen One Certification Passed:", # Dependency Check Success Log
    "log.dependency_check_finished.fail": ">>> Warning: No valid AV1 hardware encoder (QSV/NVENC/AMF) detected.", # Dependency Check Fail Log
    "log.autoselect_encoder": ">>> Automatically switched to {encoder} spell.", # Auto Select Encoder Log
    "log.recalibrating": ">>> Re-calibrating Mana Core availability...", # Recalibrating Log
    "log.list_cleared": ">>> Altar emptied, all causality reset. (Voided)", # List Cleared Log
    "log.task_pause": ">>> Reality Marble Frozen (Paused)...", # Task Pause Log
    "log.task_resume": ">>> Time Flow Resumed...", # Task Resume Log
    "log.task_stop_request": ">>> Requesting Abort...", # Task Stop Request Log
    "log.fatal_error_component_missing": ">>> Fatal Error: Key component missing, system halted.", # Component Missing Fatal Error Log
    "log.dependency.qsv_failed": ">>> Intel QSV Self-check Failed: {error}", # QSV Failed Log
    "log.dependency.qsv_exception": ">>> Intel QSV Detection Exception: {error}", # QSV Exception Log
    "log.dependency.nvenc_unsupported_gpu": ">>> Hint: NVIDIA GPU detected, but model does not support AV1 hardware encoding (RTX 40 series required).", # NVENC Unsupported Log
    "log.dependency.nvenc_failed": ">>> NVENC Self-check Failed: {error}", # NVENC Failed Log
    "log.dependency.nvenc_exception": ">>> NVENC Detection Exception: {error}", # NVENC Exception Log
    "log.dependency.amf_failed": ">>> AMD AMF Self-check Failed: {error}", # AMF Failed Log
    "log.dependency.amf_exception": ">>> AMD AMF Detection Exception: {error}", # AMF Exception Log
    "log.dependency.check_exception": ">>> Environment Self-check Exception: {error}", # Check Exception Log
    "log.encoder.no_files_found": "No mana residue detected... (｡•ˇ‸ˇ•｡)", # No Files Found Log
    "log.encoder.tasks_found": "Captured {total_tasks} anomalies to purify! ( •̀ ω •́ )y", # Tasks Found Log
    "log.encoder.task_start": "[{i}/{total_tasks}] Unfolding Reality Marble on {fname}...", # Task Start Log
    "log.encoder.skip_av1": " -> This substance is already in pure form (AV1), skipping~ (Pass)", # Skip AV1 Log
    "log.encoder.status_skipped": "✨ Skipped", # Status: Skipped
    "log.encoder.status_duration": "Time: {total_duration:.2f}s", # Status: Duration
    "log.encoder.ab_av1_fallback": " -> Attempting backup plan: {desc}...", # ab-av1 Fallback Log
    "log.encoder.ab_av1_start": " -> Deducing strongest spell (ab-av1)...", # ab-av1 Start Log
    "log.encoder.ab_av1_probing": "    -> Probing: {probe_crf} => VMAF: {vmaf_val}", # ab-av1 Probing Log
    "log.encoder.ab_av1_success_offset_corrected": " -> Spell Analysis Complete ({desc}): Raw CRF {cpu_crf} + Offset {offset} = {raw_icq} (Corrected to {reason} limit {best_icq}) [Time: {search_duration:.1f}s]", # ab-av1 Success Corrected Log
    "log.encoder.ab_av1_success_offset": " -> Spell Analysis Complete ({desc}): Raw CRF {cpu_crf} + Offset {offset} => Final Param {best_icq} [Time: {search_duration:.1f}s]", # ab-av1 Success Offset Log
    "log.encoder.ab_av1_success": " -> Spell Analysis Complete (ICQ): {best_icq} [Time: {search_duration:.1f}s] (๑•̀ㅂ•́)و✧", # ab-av1 Success Log
    "log.encoder.ab_av1_failed": " -> Analysis failed; encoding will not start without a trustworthy CRF. (T_T)", # ab-av1 Failed Log
    "log.encoder.ab_av1_error_log_header": "    [ab-av1 Error Traceback]:", # ab-av1 Error Header Log
    "log.encoder.icq_corrected": " -> Correction: Hardware encoder param limit ({icq} -> 51)", # ICQ Corrected Log
    "log.encoder.ffmpeg_exception": " -> Mana Backflow: {error} (×_×)", # FFmpeg Exception Log
    "log.encoder.success_overwrite": " -> Purification Complete! Old world rewritten (Overwrite) (ﾉ>ω<)ﾉ [Encode: {encode_duration:.1f}s | Total: {total_duration:.1f}s]", # Success Overwrite Log
    "log.encoder.error_move_overwrite": "Cannot replace source file, might be in use by another program.", # Move Overwrite Error Log
    "log.encoder.success_remain": " -> Purification Complete! Element retained, optimized form generated (Remain) (ﾉ>ω<)ﾉ [Encode: {encode_duration:.1f}s | Total: {total_duration:.1f}s]", # Success Remain Log
    "log.encoder.success_save_as": " -> Purification Complete! New world established (Save As) (ﾉ>ω<)ﾉ [Encode: {encode_duration:.1f}s | Total: {total_duration:.1f}s]", # Success Save As Log
    "log.encoder.status_done": "✅ Done", # Status: Done
    "log.encoder.error_move": " -> Sealing Ritual Failed: {error} (T_T)", # Move Error Log
    "log.encoder.ffmpeg_crash": " -> Spell Out of Control (Crash)... (T_T)", # FFmpeg Crash Log
    "log.encoder.cooling_down": " -> Cooling down Magic Circuits (Cooling down GPU)...", # Cooling Down Log
    "log.encoder.all_done": ">>> Miracle Achieved! (๑•̀ㅂ•́)و✧", # All Done Log
    "log.encoder.stopped": ">>> Pact forcibly severed.", # Stopped Log
    "log.encoder.fatal_error": "World Line Divergence Anomaly (Fatal): {error}", # Fatal Error Log
    "log.encoder.info_multichannel": " -> Multi-channel ({channels}ch) detected, maintaining status quo.", # Multichannel Info Log
    "log.encoder.info_loudnorm_enabled": " -> Sound Field Harmonization (Loudnorm): Enabled ({mode})", # Loudnorm Enabled Log
    "log.encoder.info_loudnorm_skipped": " -> Sound Field Harmonization (Loudnorm): Skipped ({mode})", # Loudnorm Skipped Log
    
    # Settings Interface
    "settings.title": "Settings", # System settings title
    "settings.gpu_timeout_label": "Hardware Probing Timeout (s)", # GPU detection timeout
    "settings.gpu_cooling_time_label": "GPU Cooling Interval (s)",
    "settings.hw_decoding_label": "GPU Decoding Acceleration",
    "settings.auto_clean_label": "Auto Clean Cache on Startup",
    "settings.thread_limit_label": "Metadata Concurrency Limit",
    "settings.log_cap_label": "Log Buffer Retention Cap",
    "settings.save_button": "💾 Save Settings", # Save settings button

    # Quick Presets Row
    "home.settings_card.presets_title": "Grimoire Templates:",
    "home.settings_card.preset_light": "Light Compression",
    "home.settings_card.preset_balanced": "Golden Balance",
    "home.settings_card.preset_heavenly": "Temple Archive",

    # Preset Success InfoBars
    "infobar.success.preset_light.title": "Light Template Activated",
    "infobar.success.preset_light.content": "Quality aligned to 91.0 (Highly compressed, perfect for mobile Crystal playback)",
    "infobar.success.preset_balanced.title": "Golden Balance Activated",
    "infobar.success.preset_balanced.content": "Quality aligned to 93.0 (黄金 ratio visually lossless, excellent size reduction)",
    "infobar.success.preset_heavenly.title": "Temple Archive Activated",
    "infobar.success.preset_heavenly.content": "Quality aligned to 95.5 (Temple-grade ultra HD lossless archive template)",

    # Close Warning Dialog
    "dialog.close_warning.title": "⚠️ Barrier Force Severed Warning",
    "dialog.close_warning.content": "The alchemy ritual (transcoding) is currently in a state of miracle creation. Forcibly closing the terminal might cause a mana backflow (FFmpeg ghost process remains in background).\n\nAre you sure you want to break the pact and exit immediately?",
    "dialog.close_warning.yes_button": "Confirm Break (Quit)",
    "dialog.close_warning.cancel_button": "Maintain Ritual (Stay)",
}