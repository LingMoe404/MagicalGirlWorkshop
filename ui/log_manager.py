"""LogManager：日志缓冲队列与刷新管理。

将 MainWindow 中原来的 ``QMutex + list`` 日志队列替换为标准库 ``queue.Queue``，
在不持有锁的情况下分批消费并刷新日志控件。保留原有 HTML 转义、主题色、级别图标、
批量插入、cap 裁剪与异常安全行为。

LogManager 不持有 MainWindow：日志控件、主题判断函数、翻译函数均通过注入提供，
因此可独立测试，无需真实窗口或事件循环。
"""

import queue
import time

from qfluentwidgets import isDarkTheme

from config import LOG_MAX_BLOCKS
from i18n.translator import tr

# 明暗主题色表（与原 MainWindow 实现保持一致）
_COLORS = {
    "dark": {
        "ts": "#707070",
        "info": "#DCDCDC",
        "success": "#A6E22E",
        "warning": "#E6DB74",
        "error": "#FF5277",
    },
    "light": {
        "ts": "#888888",
        "info": "#333333",
        "success": "#228B22",
        "warning": "#B8860B",
        "error": "#D93652",
    },
}

# 级别图标（info 默认用圆点）
_ICONS = {"info": "💡", "success": "✨", "warning": "⚠️", "error": "💢"}

# 需要加粗的级别
_BOLD_LEVELS = ("error", "warning", "success")


def _escape_html(msg):
    """对日志消息做 HTML 转义，与主窗口原实现一致：& < > 换行与双空格。

    普通消息与 blockCount 超限时的重置文案共用同一转义规则。
    """
    return (
        str(msg)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>")
        .replace("  ", "&nbsp;&nbsp;")
    )


class LogManager:
    """线程安全的日志缓冲与刷新管理器（flush 作为主线程定时器槽）。"""

    def __init__(
        self,
        text_log=None,
        log_cap=LOG_MAX_BLOCKS,
        theme_fn=isDarkTheme,
        translate=tr,
    ):
        self._text_log = text_log
        self._log_cap = int(log_cap)
        self._theme_fn = theme_fn
        self._translate = translate
        self._queue = queue.Queue()
        self._stopped = False

    def attach(self, text_log):
        """绑定日志控件；未绑定前 flush 只消费队列而不渲染。"""
        self._text_log = text_log

    def log(self, msg, level="info"):
        """将日志消息加入队列（携带时间戳与级别）。停止后丢弃。"""
        if self._stopped:
            return
        self._queue.put((time.time(), msg, level))

    def flush(self):
        """消费队列并刷新日志控件（由 MainWindow 的定时器槽调用）。

        仅在绑定控件且未停止时渲染；异常安全：单次刷新失败不中断后续刷新循环。
        """
        batch = self._drain()

        if self._stopped or self._text_log is None or not batch:
            return

        try:
            # 将 UI 更新逻辑放在 try 块中，防止报错导致定时器循环中断
            is_dark = self._theme_fn()
            c = _COLORS["dark" if is_dark else "light"]
            ts_color = c["ts"]

            html_buffer = []
            for t, msg, level in batch:
                timestamp = time.strftime("%H:%M:%S", time.localtime(t))
                msg_color = c.get(level, c["info"])
                icon = _ICONS.get(level, "•")
                safe_msg = _escape_html(msg)
                weight = "600" if level in _BOLD_LEVELS else "normal"
                html = (
                    f"<span style=\"color:{ts_color}; font-family: 'Cascadia Code', "
                    f"'Consolas', monospace; font-size: 11px;\">[{timestamp}]</span>&nbsp;"
                    f'<span style="color:{msg_color}; font-weight: {weight};">'
                    f"{icon} {safe_msg}</span><br>"
                )
                html_buffer.append(html)

            text_log = self._text_log
            text_log.setUpdatesEnabled(False)
            try:
                cursor = text_log.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                cursor.insertHtml("".join(html_buffer))
                text_log.setTextCursor(cursor)
                text_log.ensureCursorVisible()

                # 块数超过 cap 时清空并追加一条翻译后的重置消息
                if text_log.document().blockCount() > self._log_cap:
                    text_log.clear()
                    text_log.append(
                        f"<div style=\"color:{c['info']}; font-family: 'Cascadia Code'; "
                        f'font-size: 11px;">{_escape_html(self._translate("log.reset"))}</div>'
                    )
            finally:
                # 无论 insertHtml/document/append 是否抛异常，都恢复控件更新，
                # 避免控件长期停留在 setUpdatesEnabled(False) 导致不再刷新。
                text_log.setUpdatesEnabled(True)
        except Exception as e:  # noqa: BLE001
            print(f"Log UI update error: {e}")

    def set_log_cap(self, blocks):
        """更新日志块数上限；对队列的裁剪在下次 flush 时生效。"""
        self._log_cap = int(blocks)

    def stop(self):
        """停止接收新日志并清空剩余队列（幂等）。"""
        self._stopped = True
        self._drain()

    def _drain(self):
        """取空队列并按半 cap 裁剪，仅保留最新的 ``log_cap // 2`` 条。"""
        batch = []
        try:
            while not self._queue.empty():
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
        except Exception:  # noqa: BLE001
            print("Log queue drain error")
            return batch

        if len(batch) > self._log_cap // 2:
            batch = batch[-(self._log_cap // 2) :]
        return batch
