"""FileListManager：文件列表状态与后台 worker 队列的独立管理器。

从 MainWindow 中解耦出来的文件列表逻辑（扫描去重、列表行构建、时长/缩略图
worker 队列、进度/状态更新、清理与 snapshot）。通过显式注入的控件与回调与宿主
交互，不持有 MainWindow 引用，便于单元测试与后续 MainWindow 瘦身。

- 线程模型：与项目一致使用 QThread + Signal，管理器本身运行在主线程，
  worker 在各自线程中，跨线程通信仅通过 Signal。
- worker 工厂属性（duration_worker_cls / thumbnail_worker_cls）可被测试替换为
  桩对象，避免依赖真实 ffprobe / ffmpeg。
"""

import copy
import os
from collections import OrderedDict

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QListWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, FluentIcon, IconWidget, ProgressBar

from config import (
    MAX_DURATION_WORKERS,
    MAX_THUMBNAIL_CACHE_SIZE,
    MAX_THUMBNAIL_WORKERS,
    VIDEO_EXTS,
)
from i18n.translator import tr
from ui.common import ClickableBodyLabel
from workers import DurationWorker, ThumbnailWorker


class FileListManager:
    """管理源文件列表：状态、列表行、后台 worker 队列与清理。"""

    def __init__(
        self,
        list_widget,
        placeholder,
        count_label,
        thread_limit_getter,
        status_text_callback=None,
        remove_callback=None,
    ):
        # 注入的控件与回调（不持有 MainWindow）
        self.list_widget = list_widget
        self.placeholder = placeholder
        self.count_label = count_label
        self.thread_limit_getter = thread_limit_getter
        self.status_text_callback = status_text_callback
        self.remove_callback = remove_callback

        # 列表状态
        self.selected_files = []  # 待处理的文件列表（顺序与列表行一致）
        self.path_to_item = {}  # 文件路径到列表项的映射
        self.file_metadata = {}  # 媒体元数据缓存

        # worker 队列
        self.active_dur_workers = {}  # 正在运行的时长线程
        self.pending_dur_tasks = []  # 等待中的时长任务
        self.active_thumb_workers = {}  # 正在运行的缩略图线程
        self.pending_thumb_tasks = []  # 等待中的缩略图任务

        # 缓存
        self.cached_durations = {}  # 视频时长缓存
        self.cached_thumbnails = OrderedDict()  # 视频缩略图LRU缓存
        self.MAX_THUMBNAIL_CACHE = MAX_THUMBNAIL_CACHE_SIZE

        # 拖拽边框状态
        self._drag_over_source_zone = False

        # worker 工厂（测试可替换为桩对象）
        self.duration_worker_cls = DurationWorker
        self.thumbnail_worker_cls = ThumbnailWorker

    # --- 扫描 / 添加 ---
    def add_source_paths(self, paths):
        """将给定的路径（文件或文件夹）添加到待处理文件列表中。"""
        existing = set(self.selected_files)
        added = 0

        for raw in paths:
            if not raw:
                continue
            p = os.path.normpath(raw)

            if os.path.isdir(p):
                for dp, _, filenames in os.walk(p):
                    for f in filenames:
                        fp = os.path.join(dp, f)
                        if fp.lower().endswith(VIDEO_EXTS) and fp not in existing:
                            self.selected_files.append(fp)
                            existing.add(fp)
                            added += 1
            elif (
                os.path.isfile(p)
                and p.lower().endswith(VIDEO_EXTS)
                and p not in existing
            ):
                self.selected_files.append(p)
                existing.add(p)
                added += 1

        if added > 0:
            self.update_selected_count()
        return added

    # --- snapshot ---
    def snapshot(self):
        """返回 (文件列表副本, 元数据深拷贝)，不会暴露内部可变状态。"""
        return list(self.selected_files), copy.deepcopy(self.file_metadata)

    # --- 清理 ---
    def clear(self):
        """清空所有已选择的文件、列表行、队列与缓存。"""
        self.selected_files.clear()
        self.path_to_item.clear()
        self.list_widget.clear()
        self.pending_dur_tasks.clear()
        self.pending_thumb_tasks.clear()
        self.cached_durations.clear()
        self.cached_thumbnails.clear()
        self.file_metadata.clear()
        self.update_selected_count()

    def remove_selected_file(self, file_path):
        """从文件列表中移除指定的文件。"""
        self.selected_files = [p for p in self.selected_files if p != file_path]

        if file_path in self.path_to_item:
            item = self.path_to_item.pop(file_path)
            row = self.list_widget.row(item)
            taken_item = self.list_widget.takeItem(row)
            del taken_item

        self.cached_durations.pop(file_path, None)
        self.cached_thumbnails.pop(file_path, None)
        self.file_metadata.pop(file_path, None)

        if file_path in self.pending_dur_tasks:
            self.pending_dur_tasks.remove(file_path)
        self.pending_thumb_tasks = [
            t for t in self.pending_thumb_tasks if t[0] != file_path
        ]

        if self.remove_callback:
            self.remove_callback(file_path)

        self.update_selected_count()

    # --- worker 停止（closeEvent 调用）---
    def stop_workers(self):
        """停止所有活动的时长/缩略图线程并清空待处理队列。"""
        self.pending_dur_tasks.clear()
        self.pending_thumb_tasks.clear()

        for worker in list(self.active_dur_workers.values()):
            try:
                worker.stop()
            except RuntimeError:
                pass

        for worker in list(self.active_thumb_workers.values()):
            try:
                worker.stop()
            except RuntimeError:
                pass

    # --- 时长 worker 队列 ---
    def _thread_limit(self, fallback):
        """读取当前线程限制；无 getter 或返回空值时回落到默认。"""
        if not self.thread_limit_getter:
            return fallback
        limit = self.thread_limit_getter()
        return limit if limit else fallback

    def process_duration_queue(self):
        """处理等待中的视频时长分析任务。"""
        limit = self._thread_limit(fallback=MAX_DURATION_WORKERS)
        while len(self.active_dur_workers) < limit and self.pending_dur_tasks:
            path = self.pending_dur_tasks.pop(0)
            self.start_duration_worker(path)

    def start_duration_worker(self, path):
        """启动一个新的线程来分析视频时长。"""
        worker = self.duration_worker_cls(path)
        worker.result.connect(self.update_file_duration_label)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self.on_duration_worker_finished(path))
        self.active_dur_workers[path] = worker
        worker.start()
        self.set_duration_text_in_list(path, "...")

    def on_duration_worker_finished(self, path):
        """视频时长分析线程完成时的清理工作。"""
        self.active_dur_workers.pop(path, None)
        self.process_duration_queue()

    def get_file_duration(self, path):
        """请求获取指定文件的视频时长。"""
        if path in self.pending_dur_tasks:
            return
        if path in self.active_dur_workers:
            return

        self.pending_dur_tasks.append(path)
        self.process_duration_queue()

    def update_file_duration_label(self, path, duration_str, duration_sec, meta=None):
        """更新文件列表中的视频时长标签。"""
        self.cached_durations[path] = (duration_str, duration_sec)
        if meta:
            self.file_metadata[path] = {**meta, "duration": duration_sec}

        self.set_duration_text_in_list(path, duration_str)

        if path not in self.cached_thumbnails:
            self.get_file_thumbnail(path, duration_sec)

    def set_duration_text_in_list(self, path, text):
        """在文件列表中设置指定文件的时长文本。"""
        for i in range(self.list_widget.count()):
            if i < len(self.selected_files) and self.selected_files[i] == path:
                item = self.list_widget.item(i)
                widget = self.list_widget.itemWidget(item)
                if widget:
                    btn = widget.findChild(ClickableBodyLabel, "btn_duration")
                    if btn:
                        btn.setText(text)
                        if text not in ["...", tr("list.item.duration_button")]:
                            btn.setEnabled(False)
                            btn.setCursor(Qt.CursorShape.ArrowCursor)

    # --- 缩略图 worker 队列 ---
    def process_thumbnail_queue(self):
        """处理等待中的视频缩略图生成任务。"""
        limit = self._thread_limit(fallback=MAX_THUMBNAIL_WORKERS)
        while len(self.active_thumb_workers) < limit and self.pending_thumb_tasks:
            path, duration = self.pending_thumb_tasks.pop(0)
            self.start_thumbnail_worker(path, duration)

    def start_thumbnail_worker(self, path, duration_sec):
        """启动一个新的线程来生成视频缩略图。"""
        worker = self.thumbnail_worker_cls(path, duration_sec)
        worker.result.connect(self.update_file_thumbnail)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self.on_thumbnail_worker_finished(path))
        self.active_thumb_workers[path] = worker
        worker.start()

    def on_thumbnail_worker_finished(self, path):
        """视频缩略图生成线程完成时的清理工作。"""
        self.active_thumb_workers.pop(path, None)
        self.process_thumbnail_queue()

    def get_file_thumbnail(self, path, duration_sec):
        """请求获取指定文件的视频缩略图。"""
        if path in self.active_thumb_workers:
            return
        for p, _ in self.pending_thumb_tasks:
            if p == path:
                return

        self.pending_thumb_tasks.append((path, duration_sec))
        self.process_thumbnail_queue()

    def update_file_thumbnail(self, path, image):
        """更新文件列表中的视频缩略图。"""
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)

            rounded = QPixmap(pixmap.size())
            rounded.fill(Qt.GlobalColor.transparent)

            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter_path = QPainterPath()
            painter_path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 6, 6)
            painter.setClipPath(painter_path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            if path in self.cached_thumbnails:
                self.cached_thumbnails.move_to_end(path)
            self.cached_thumbnails[path] = QIcon(rounded)

            if len(self.cached_thumbnails) > self.MAX_THUMBNAIL_CACHE:
                self.cached_thumbnails.popitem(last=False)

            item = self.path_to_item.get(path)
            if item:
                widget = self.list_widget.itemWidget(item)
                if widget:
                    icon_w = widget.findChild(IconWidget, "video_icon")
                    if icon_w:
                        icon_w.setIcon(self.cached_thumbnails[path])

    # --- 列表行构建 ---
    def update_selected_count(self):
        """更新文件数量显示，并切换占位符和列表的可见性。"""
        count = len(self.selected_files)
        self.count_label.setText(str(count))

        is_empty = count == 0
        self.placeholder.setVisible(is_empty)
        self.list_widget.setVisible(not is_empty)
        self.update_selected_zone_border()

        if is_empty:
            self.list_widget.clear()
            self.path_to_item.clear()
            return

        for p in self.selected_files:
            if p in self.path_to_item:
                continue

            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, 60))
            self.path_to_item[p] = item

            item_widget = QWidget(self.list_widget)
            item_widget.setObjectName("item_tile")
            item_widget.setStyleSheet("""
                QWidget#item_tile {
                    background-color: rgba(251, 114, 153, 0.05);
                    border: 1px solid rgba(251, 114, 153, 0.1);
                    border-radius: 8px;
                    margin: 2px 4px;
                }
                QWidget#item_tile:hover {
                    background-color: rgba(251, 114, 153, 0.12);
                    border: 1px solid rgba(251, 114, 153, 0.3);
                }
            """)
            container = QVBoxLayout(item_widget)
            container.setContentsMargins(4, 2, 4, 2)
            container.setSpacing(0)

            row = QWidget(item_widget)
            row.setFixedHeight(44)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(0)

            status_icon = IconWidget(FluentIcon.HISTORY, row)
            status_icon.setFixedSize(16, 16)
            status_icon.setObjectName("status_icon")

            display_icon = self.cached_thumbnails.get(p, FluentIcon.VIDEO)
            icon_widget = IconWidget(display_icon, row)
            icon_widget.setFixedSize(24, 24)
            icon_widget.setObjectName("video_icon")

            row_layout.addWidget(status_icon)
            row_layout.addSpacing(4)
            row_layout.addWidget(icon_widget)
            row_layout.addSpacing(8)

            try:
                f_size = os.path.getsize(p)
                size_str = self.format_file_size(f_size)
            except Exception:  # noqa: BLE001
                size_str = "Unknown"

            name_label = BodyLabel(os.path.basename(p) or p, row)
            name_label.setToolTip(p)

            btn_remove = ClickableBodyLabel(tr("list.item.remove_button"), row)
            btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_remove.setStyleSheet("font-weight: 700; background: transparent;")
            btn_remove.setTextColor(QColor("#D93652"), QColor("#FF8FA1"))
            btn_remove.clicked.connect(lambda path=p: self.remove_selected_file(path))

            dur_text = tr("list.item.duration_button")
            if p in self.cached_durations:
                dur_text = self.cached_durations[p][0]

            btn_duration = ClickableBodyLabel(dur_text, row)
            btn_duration.setObjectName("btn_duration")
            btn_duration.setFixedWidth(60)
            btn_duration.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            size_label = BodyLabel(size_str, row)
            size_label.setTextColor(QColor("#999999"), QColor("#999999"))
            size_label.setFixedWidth(80)
            size_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            row_layout.addWidget(name_label, 1)
            row_layout.addSpacing(12)
            row_layout.addWidget(btn_duration)
            row_layout.addSpacing(0)
            row_layout.addWidget(size_label)
            row_layout.addSpacing(12)
            row_layout.addWidget(btn_remove)

            container.addWidget(row)

            stats_layout = QHBoxLayout()
            stats_layout.setContentsMargins(6, 0, 12, 4)
            stats_layout.setSpacing(10)

            pbar = ProgressBar(item_widget)
            pbar.setFixedHeight(4)
            pbar.setValue(0)
            pbar.hide()
            pbar.setObjectName("pbar")

            lbl_stats = BodyLabel("", item_widget)
            lbl_stats.setObjectName("lbl_stats")
            lbl_stats.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #FB7299;"
            )
            lbl_stats.hide()

            stats_layout.addWidget(pbar, 1)
            stats_layout.addWidget(lbl_stats)

            container.addLayout(stats_layout)

            self.list_widget.setItemWidget(item, item_widget)
            if p not in self.cached_durations:
                self.get_file_duration(p)

        self.clear_selected_list_visual_state()

    def format_file_size(self, size_bytes):
        """格式化文件大小为可读字符串。"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def clear_selected_list_visual_state(self):
        """清除文件列表的视觉选择状态。"""
        self.list_widget.clearSelection()
        self.list_widget.setCurrentRow(-1)

    # --- 拖拽边框状态 ---
    def set_drag_active(self, active):
        """设置拖拽状态（宿主在拖拽进入/离开时调用）。"""
        self._drag_over_source_zone = bool(active)
        self.update_selected_zone_border()

    def update_selected_zone_border(self):
        """更新文件列表区域的边框样式，以响应拖拽状态。"""
        show_hint_border = self._drag_over_source_zone or (
            len(self.selected_files) == 0
        )
        border_css = (
            "2px dashed rgba(251, 114, 153, 0.90)"
            if show_hint_border
            else "1px solid transparent"
        )
        bg_css = (
            "rgba(251, 114, 153, 0.1)"
            if show_hint_border
            else "rgba(128, 128, 128, 0.05)"
        )

        self.placeholder.setStyleSheet(
            f"border: {border_css}; border-radius: 10px; background: {bg_css}; padding: 8px; color: #FB7299; font-size: 18px; font-weight: 700;"
        )

        self.list_widget.setStyleSheet(f"""
            ListWidget {{
                background: {bg_css};
                border: {border_css};
                border-radius: 10px;
                outline: none;
            }}
            ListWidget::item {{
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            ListWidget::item:hover {{
                background: transparent;
            }}
            ListWidget::item:selected {{
                background: transparent;
            }}
            QListWidget {{
                background: {bg_css};
                border: {border_css};
                border-radius: 10px;
                outline: none;
            }}
            QListWidget::item {{
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }}
            QListWidget::item:hover {{
                background: transparent;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """)

    # --- 进度 / 状态更新 ---
    def update_file_progress(self, filepath, percent):
        """更新指定文件的进度条。"""
        item = self.path_to_item.get(filepath)
        if not item:
            return
        widget = self.list_widget.itemWidget(item)
        if widget:
            pbar = widget.findChild(ProgressBar, "pbar")
            if pbar:
                if pbar.isHidden():
                    pbar.show()
                pbar.setValue(percent)

    def update_file_stats(self, filepath, speed, eta):
        """更新指定文件的统计信息（速度和剩余时间）。"""
        item = self.path_to_item.get(filepath)
        if not item:
            return
        widget = self.list_widget.itemWidget(item)
        if widget:
            lbl = widget.findChild(BodyLabel, "lbl_stats")
            pbar = widget.findChild(ProgressBar, "pbar")
            if lbl:
                if lbl.isHidden():
                    lbl.show()
                lbl.setText(f"{speed} | {eta}")
            if pbar and pbar.isHidden():
                pbar.show()

        # 将探测阶段文本交给宿主（如状态栏探针文本）决定
        if self.status_text_callback:
            self.status_text_callback(speed, eta)

    def update_file_status(self, filepath, status):
        """更新指定文件的状态图标。"""
        item = self.path_to_item.get(filepath)
        if not item:
            return
        widget = self.list_widget.itemWidget(item)
        if widget:
            icon_w = widget.findChild(IconWidget, "status_icon")
            pbar = widget.findChild(ProgressBar, "pbar")
            lbl_stats = widget.findChild(BodyLabel, "lbl_stats")
            if icon_w:
                if status == "processing":
                    icon_w.setIcon(FluentIcon.SYNC)
                    if lbl_stats:
                        lbl_stats.setStyleSheet(
                            "font-size: 11px; font-weight: bold; color: #FB7299;"
                        )
                elif status == "success":
                    icon_w.setIcon(FluentIcon.ACCEPT)
                    if pbar:
                        pbar.hide()
                    if lbl_stats:
                        lbl_stats.setStyleSheet(
                            "font-size: 11px; font-weight: bold; color: #55E555;"
                        )
                        lbl_stats.show()
                elif status == "error":
                    icon_w.setIcon(FluentIcon.CANCEL)
                    if pbar:
                        pbar.hide()
                    if lbl_stats:
                        lbl_stats.hide()
