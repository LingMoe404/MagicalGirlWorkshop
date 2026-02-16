from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QStyleOptionViewItem, QStyle, QAbstractItemView
from qfluentwidgets import BodyLabel, ListWidget
from qfluentwidgets.components.widgets.list_view import ListItemDelegate


class ClickableBodyLabel(BodyLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class NoHighlightItemDelegate(ListItemDelegate):
    """兼容 Fluent ListWidget 接口，同时去除 hover/selected/focus 高亮。"""

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        opt.state &= ~QStyle.StateFlag.State_Selected
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        opt.state &= ~QStyle.StateFlag.State_HasFocus

        selected_rows = self.selectedRows.copy()
        hover_row = self.hoverRow
        pressed_row = self.pressedRow

        self.selectedRows = set()
        self.hoverRow = -1
        self.pressedRow = -1
        try:
            super().paint(painter, opt, index)
        finally:
            self.selectedRows = selected_rows
            self.hoverRow = hover_row
            self.pressedRow = pressed_row


class DragDropMixin:
    """提取通用的拖拽逻辑"""
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self.dragActiveChanged.emit(True)
            e.accept()
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dragLeaveEvent(self, e):
        self.dragActiveChanged.emit(False)
        super().dragLeaveEvent(e)

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.filesDropped.emit(paths)
            self.dragActiveChanged.emit(False)
            e.acceptProposedAction()
        else:
            self.dragActiveChanged.emit(False)
            e.ignore()


class DroppableBodyLabel(DragDropMixin, BodyLabel):
    filesDropped = Signal(list)
    dragActiveChanged = Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

class DroppableListWidget(DragDropMixin, ListWidget):
    filesDropped = Signal(list)
    dragActiveChanged = Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)
        self.setItemDelegate(NoHighlightItemDelegate(self))

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.clearSelection()
        self.setCurrentRow(-1)