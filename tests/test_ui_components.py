"""UI component tests for DragDropMixin, DroppableListWidget, DroppableBodyLabel."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from ui.common import (
    ClickableBodyLabel,
    DroppableBodyLabel,
    DroppableListWidget,
)


class FakeMimeData:
    """Minimal MIME data mock."""

    def __init__(self, urls=None):
        self._urls = urls or []

    def hasUrls(self):
        return bool(self._urls)

    def urls(self):
        return self._urls


class FakeDragEvent:
    """Mock drag event with accept/ignore tracking."""

    def __init__(self, mime_data):
        self.mimeData = lambda: mime_data
        self._accepted = False
        self._ignored = False
        self._proposed = False

    def accept(self):
        self._accepted = True

    def acceptProposedAction(self):
        self._proposed = True

    def ignore(self):
        self._ignored = True


class FakeDropEvent(FakeDragEvent):
    pass


class FakeLeaveEvent:
    """Mock drag leave event."""

    def __init__(self):
        self._accepted = False

    def accept(self):
        self._accepted = True

    def ignore(self):
        self._accepted = False


class UIComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_clickable_label_emits_clicked_on_left_click(self):
        label = ClickableBodyLabel("Click me")
        clicked = []
        label.clicked.connect(lambda: clicked.append(True))
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPoint(10, 10),
            QPoint(10, 10),
            QPoint(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        label.mouseReleaseEvent(event)
        self.assertTrue(clicked)

    def test_drag_enter_accepts_urls(self):
        widget = DroppableBodyLabel("test")
        mime = FakeMimeData([QUrl.fromLocalFile("C:/test.mp4")])
        event = FakeDragEvent(mime)
        widget.dragEnterEvent(event)
        self.assertTrue(event._accepted)
        self.assertTrue(event._proposed)

    def test_drag_enter_without_urls_ignores(self):
        widget = DroppableBodyLabel("test")
        mime = FakeMimeData([])
        event = FakeDragEvent(mime)
        widget.dragEnterEvent(event)
        self.assertFalse(event._accepted)
        self.assertFalse(event._proposed)
        self.assertTrue(event._ignored)

    def test_drop_emits_file_paths(self):
        widget = DroppableBodyLabel("test")
        dropped = []
        widget.filesDropped.connect(dropped.append)
        mime = FakeMimeData(
            [
                QUrl.fromLocalFile("C:/test.mp4"),
                QUrl.fromLocalFile("D:/test2.mkv"),
            ]
        )
        event = FakeDropEvent(mime)
        widget.dropEvent(event)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(len(dropped[0]), 2)
        self.assertTrue(dropped[0][0].endswith("test.mp4"))
        self.assertTrue(dropped[0][1].endswith("test2.mkv"))
        self.assertTrue(event._proposed)

    def test_drop_ignores_empty(self):
        widget = DroppableBodyLabel("test")
        dropped = []
        widget.filesDropped.connect(dropped.append)
        mime = FakeMimeData([])
        event = FakeDropEvent(mime)
        widget.dropEvent(event)
        self.assertEqual(dropped, [])
        self.assertTrue(event._ignored)

    def test_drag_leave_emits_false(self):
        widget = DroppableBodyLabel("test")
        states = []
        widget.dragActiveChanged.connect(states.append)
        event = FakeLeaveEvent()
        widget.dragLeaveEvent(event)
        self.assertEqual(states, [False])

    def test_list_widget_accepts_drops(self):
        widget = DroppableListWidget()
        self.assertTrue(widget.acceptDrops())
        self.assertIsNotNone(widget.itemDelegate())

    def test_list_widget_drop_emits_paths(self):
        widget = DroppableListWidget()
        dropped = []
        widget.filesDropped.connect(dropped.append)
        mime = FakeMimeData([QUrl.fromLocalFile("C:/test.mp4")])
        event = FakeDropEvent(mime)
        widget.dropEvent(event)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(len(dropped[0]), 1)
        self.assertTrue(dropped[0][0].endswith("test.mp4"))

    def test_list_widget_mouse_press_clears_selection(self):
        widget = DroppableListWidget()
        widget.addItem("Item 1")
        widget.setCurrentRow(0)
        self.assertEqual(widget.currentRow(), 0)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(5, 5),
            QPoint(5, 5),
            QPoint(5, 5),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.mousePressEvent(event)
        self.assertEqual(widget.currentRow(), -1)


if __name__ == "__main__":
    unittest.main()
