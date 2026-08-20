"""home_ui_builder 结构测试。

验证 MainWindow 主页布局抽取到 ui/home_ui_builder.build_home_ui 之后：
- build_home_ui 可从独立模块导入、可调用，且不依赖 MainWindow 类
- MainWindow.init_ui 是委托 build_home_ui 的薄方法
- 构建后保留全部关键控件属性（header/左右面板卡片/状态栏/日志区/footer/子界面）
- 原 13 个 _init_* 布局方法已从 MainWindow 移除（结构化证明）
- 信号接线保留（拖放 / 转码按钮）

不依赖真实 ffprobe/ffmpeg：注入桩 worker 工厂隔离后台线程。
"""

import inspect
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from ui.config_manager import ConfigManager
from ui.home_ui_builder import build_home_ui
from ui.main_window import MainWindow


class _FakeWorker:
    """模拟 Duration/Thumbnail worker：不启动真实 QThread。"""

    def __init__(self, *args, **kwargs):
        self.result = mock.Mock()
        self.finished = mock.Mock()
        self.started = False

    def start(self):
        self.started = True

    def stop(self):
        pass

    def deleteLater(self):
        pass


class _WindowStub(QWidget):
    """最小宿主桩：仅提供 build_home_ui 需要的属性/方法，不导入 MainWindow。

    用于证明 build_home_ui 是独立可调用的布局入口（无 MainWindow 依赖）。
    构建期间被直接调用的方法给空实现；其余方法只需存在（信号连接时引用）。
    """

    def __init__(self):
        super().__init__()
        self.save_modes = ["save_as", "overwrite", "remain"]
        self.loudnorm_modes = ["auto", "always", "disable"]
        self.transcode_modes = ["auto", "manual"]

    def _populate_combo(self, combo, items):
        for item in items:
            combo.addItem(str(item), userData=item)

    def toggle_export_ui(self):
        pass

    def toggle_transcode_concurrency_ui(self):
        pass

    def sync_source_cache_card_height(self):
        pass

    def sync_settings_selected_card_height(self):
        pass

    def addSubInterface(self, *args, **kwargs):
        pass

    # 仅被信号连接引用（不会在构建期间被调用）
    def on_language_changed(self, index):
        pass

    def on_theme_changed(self, index):
        pass

    def clear_cache_files(self):
        pass

    def browse_folder(self, line_edit):
        pass

    def save_current_settings(self, show_tip=False):
        pass

    def restore_defaults(self):
        pass

    def apply_preset_light(self):
        pass

    def apply_preset_balanced(self):
        pass

    def apply_preset_heavenly(self):
        pass

    def choose_source_folder(self):
        pass

    def browse_files(self):
        pass

    def clear_all_selected_files(self):
        pass

    def handle_dropped_paths(self, paths):
        pass

    def on_selected_zone_drag_active_changed(self, active):
        pass

    def clear_selected_list_visual_state(self):
        pass

    def open_file_location(self, item):
        pass

    def start_task(self):
        pass

    def pause_task(self):
        pass

    def stop_task(self):
        pass

    def _get_thread_limit(self):
        return 4

    def _on_file_stats_text(self, speed, eta):
        pass

    def _on_file_removed(self, file_path):
        pass


# 原 MainWindow 的 13 个纯 UI 构建方法，抽取后不应再存在于主窗口
_MIGRATED_INIT_METHODS = [
    "_init_header",
    "_init_content_area",
    "_init_left_panel_content",
    "_init_cache_card",
    "_init_settings_card",
    "_init_action_card",
    "_init_right_panel_content",
    "_init_source_card",
    "_init_file_list_card",
    "_init_status_bar",
    "_init_log_area",
    "_init_footer",
    "_init_sub_interfaces",
]

# 构建后必须保留的关键控件/布局属性
_KEY_ATTRIBUTES = [
    # 布局容器
    "main_layout",
    "home_interface",
    "column_splitter",
    "left_panel",
    "left_column",
    "right_panel",
    "right_column",
    # 头部
    "title",
    "subtitle",
    "combo_lang",
    "combo_theme",
    # 缓存卡片
    "card_io",
    "cache_card_title",
    "btn_clear_cache",
    "line_cache",
    "btn_cache",
    # 设置卡片
    "card_settings",
    "combo_encoder",
    "line_vmaf",
    "line_audio",
    "combo_preset",
    "spin_offset",
    "combo_color",
    "combo_loudnorm",
    "line_loudnorm",
    "sw_nv_aq",
    "btn_preset_light",
    "btn_preset_balanced",
    "btn_preset_heavenly",
    "btn_save_conf",
    "btn_reset_conf",
    # 操作卡片
    "card_action",
    "combo_save_mode",
    "export_container",
    "line_export",
    "btn_export",
    "combo_transcode_mode",
    "spin_transcode_concurrency",
    "lbl_concurrency_status",
    "btn_start",
    "btn_pause",
    "btn_stop",
    # 源文件卡片
    "card_source",
    "btn_src",
    "btn_files",
    # 文件列表卡片
    "card_selected_files",
    "btn_clear_list",
    "lbl_selected_count_right",
    "lbl_selected_placeholder",
    "list_selected_files",
    "file_list_manager",
    # 状态栏
    "lbl_current",
    "pbar_current",
    "lbl_total",
    "pbar_total",
    # 日志区
    "text_log",
    "log_manager",
    # footer
    "footer",
    # 子界面
    "info_interface",
    "profile_interface",
    "credits_interface",
    "settings_interface",
]


class HomeUiBuilderStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cfg_path = os.path.join(self._tmp.name, "config.ini")

    def _make_window(self):
        w = MainWindow(config_manager=ConfigManager(config_path=self.cfg_path))
        # 注入桩 worker 工厂，避免真实 ffprobe/ffmpeg 线程导致 teardown 崩溃
        w.file_list_manager.duration_worker_cls = _FakeWorker
        w.file_list_manager.thumbnail_worker_cls = _FakeWorker
        self.addCleanup(w.file_list_manager.stop_workers)
        self.addCleanup(w.deleteLater)
        return w

    # --- 1. build_home_ui 可导入且可独立调用 ---
    def test_build_home_ui_is_importable_and_callable(self):
        self.assertTrue(callable(build_home_ui))

    def test_build_home_ui_works_on_independent_stub(self):
        # 在最小宿主桩上直接调用 build_home_ui（不经过 MainWindow），
        # 证明它是独立可调用的布局入口且不依赖 MainWindow 类。
        stub = _WindowStub()
        build_home_ui(stub)
        for attr in _KEY_ATTRIBUTES:
            self.assertTrue(hasattr(stub, attr), f"build_home_ui 后缺少 {attr}")

    # --- 2. init_ui 委托给 build_home_ui ---
    def test_init_ui_source_delegates_to_build_home_ui(self):
        src = inspect.getsource(MainWindow.init_ui)
        self.assertIn("build_home_ui", src)

    # --- 3. 关键控件属性在构造后保留 ---
    def test_key_attributes_preserved_after_init(self):
        w = self._make_window()
        for attr in _KEY_ATTRIBUTES:
            self.assertTrue(hasattr(w, attr), f"MainWindow 缺少 {attr}")

    # --- 4. 原 _init_* 布局方法已从 MainWindow 移除 ---
    def test_layout_init_methods_migrated_out_of_main_window(self):
        for name in _MIGRATED_INIT_METHODS:
            self.assertFalse(
                hasattr(MainWindow, name), f"MainWindow.{name} 应已迁移到 builder"
            )

    # --- 5. builder 模块不导入 MainWindow（避免循环依赖） ---
    def test_builder_module_does_not_import_main_window(self):
        import ui.home_ui_builder as builder

        src = inspect.getsource(builder)
        self.assertNotIn("import MainWindow", src)
        self.assertNotIn("from ui.main_window", src)
        self.assertNotIn("from .main_window", src)

    # --- 6. 信号接线保留：拖放与转码按钮 ---
    def test_drop_signals_wired_to_handler(self):
        with mock.patch.object(MainWindow, "handle_dropped_paths") as handler:
            w = self._make_window()
            paths = [os.path.join(self._tmp.name, "a.mkv")]
            w.lbl_selected_placeholder.filesDropped.emit(paths)
            handler.assert_called_once_with(paths)
            handler.reset_mock()
            w.list_selected_files.filesDropped.emit(paths)
            handler.assert_called_once_with(paths)

    def test_transcode_buttons_wired_to_slots(self):
        with (
            mock.patch.object(MainWindow, "start_task") as start,
            mock.patch.object(MainWindow, "pause_task") as pause,
            mock.patch.object(MainWindow, "stop_task") as stop,
        ):
            w = self._make_window()
            # pause/stop 初始禁用，.click() 无效，需先启用再触发
            w.btn_start.click()
            start.assert_called_once_with()
            w.btn_pause.setEnabled(True)
            w.btn_pause.click()
            pause.assert_called_once_with()
            w.btn_stop.setEnabled(True)
            w.btn_stop.click()
            stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
