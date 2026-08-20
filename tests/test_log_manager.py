"""LogManager 单元测试。

覆盖 brief / 计划 Task 2 要求的行为：
- 队列插入携带时间戳与级别
- queue.Queue 消费、半 cap 裁剪、HTML 转义、换行与双空格转换
- 通过注入 theme_fn 选择明/暗主题颜色
- flush() 使用 fake text edit，且具备异常安全行为（不依赖真实窗口）
- set_log_cap() 与 stop()
- 未知 level 回退到默认 info 颜色与 • 图标
- 后台线程并发 log() + 主线程反复 flush() 无异常、队列一致

不依赖真实 QTextEdit / MainWindow；使用 FakeTextEdit 与注入的 theme_fn/translate。
"""

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ui.log_manager import LogManager


# --- 桩对象 ---
class FakeCursor:
    """模拟 QTextCursor 的最小实现，记录 insertHtml 内容。"""

    class MoveOperation:
        End = "End"

    def __init__(self, owner):
        self.owner = owner
        self.inserted = []

    def movePosition(self, op):
        return True

    def insertHtml(self, html):
        self.inserted.append(html)
        self.owner.on_html_inserted(html)


class FakeDocument:
    def __init__(self, owner):
        self.owner = owner

    def blockCount(self):
        return self.owner.block_count


class FakeTextEdit:
    """模拟 LogManager.flush() 用到的 QTextEdit 接口子集。"""

    def __init__(self, block_count=0):
        self.block_count = block_count
        self.html = []
        self.appended = []
        self.cleared = False
        self.updates = []
        self.ensure_visible = 0
        self.fail_insert_html = False
        self.cursor = FakeCursor(self)

    # --- QTextEdit 兼容接口 ---
    def setUpdatesEnabled(self, value):
        self.updates.append(value)

    def textCursor(self):
        return self.cursor

    def setTextCursor(self, cursor):
        pass

    def ensureCursorVisible(self):
        self.ensure_visible += 1

    def clear(self):
        self.cleared = True
        self.block_count = 0

    def append(self, html):
        self.appended.append(html)
        self.block_count += 1

    def document(self):
        return FakeDocument(self)

    # --- 模拟辅助 ---
    def on_html_inserted(self, html):
        if self.fail_insert_html:
            raise RuntimeError("boom")
        self.html.append(html)
        # 每个 <br> 大致对应一个换行块，用于 blockCount 重置判定
        self.block_count += html.count("<br>")


TRANSLATIONS = {"log.reset": ">>> History erased, log restarts."}


def fake_translate(key, **kwargs):
    return TRANSLATIONS.get(key, key)


class LogManagerTests(unittest.TestCase):
    def make_manager(self, **kwargs):
        defaults = {
            "text_log": None,
            "log_cap": 2000,
            "theme_fn": lambda: False,
            "translate": fake_translate,
        }
        defaults.update(kwargs)
        return LogManager(**defaults)

    # --- 队列插入：时间戳与级别 ---
    def test_log_inserts_entries_with_timestamp_and_level(self):
        mgr = self.make_manager()
        mgr.log("hello", "info")
        mgr.log("boom", "error")
        items = list(mgr._queue.queue)
        self.assertEqual(len(items), 2)
        ts, msg, level = items[0]
        self.assertIsInstance(ts, float)
        self.assertAlmostEqual(ts, time.time(), delta=1)
        self.assertEqual(msg, "hello")
        self.assertEqual(level, "info")
        self.assertEqual(items[1][2], "error")

    def test_log_default_level_is_info(self):
        mgr = self.make_manager()
        mgr.log("plain")
        _, msg, level = next(iter(mgr._queue.queue))
        self.assertEqual(level, "info")
        self.assertEqual(msg, "plain")

    # --- queue.Queue 消费 ---
    def test_flush_consumes_queue_and_renders_in_order(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, theme_fn=lambda: False)
        mgr.log("first", "info")
        mgr.log("second", "warning")
        mgr.flush()
        self.assertTrue(mgr._queue.empty())
        self.assertEqual(len(text.html), 1)
        html = text.html[0]
        self.assertLess(html.index("first"), html.index("second"))
        self.assertIn("💡", html)
        self.assertIn("⚠️", html)
        self.assertIn("[", html)  # 时间戳

    def test_flush_with_empty_queue_is_noop(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text)
        mgr.flush()
        self.assertEqual(text.html, [])

    # --- HTML 转义 / 换行 / 双空格 ---
    def test_html_escaping_newline_and_double_space(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text)
        mgr.log("a & b < c > d\nline2  x", "info")
        mgr.flush()
        html = text.html[0]
        self.assertIn("a &amp; b &lt; c &gt; d", html)
        self.assertIn("<br>", html)
        self.assertIn("&nbsp;&nbsp;", html)

    # --- 明暗主题颜色 ---
    def test_dark_theme_colors(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, theme_fn=lambda: True)
        mgr.log("dark msg", "info")
        mgr.flush()
        self.assertIn("#707070", text.html[0])  # dark ts 颜色
        self.assertIn("#DCDCDC", text.html[0])  # dark info 颜色

    def test_light_theme_colors(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, theme_fn=lambda: False)
        mgr.log("light msg", "info")
        mgr.flush()
        self.assertIn("#888888", text.html[0])  # light ts 颜色
        self.assertIn("#333333", text.html[0])  # light info 颜色

    # --- 未知 level 回退（默认 info 颜色与 • 图标） ---
    def test_unknown_level_falls_back_to_info_color_and_bullet(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, theme_fn=lambda: False)
        mgr.log("mystery", "mystery-level")
        mgr.flush()
        html = text.html[0]
        # 未知级别使用 info 颜色（light 主题 #333333）
        self.assertIn("#333333", html)
        # 未知级别使用默认 • 图标，而非任何已知图标
        self.assertIn("•", html)
        for icon in ("💡", "✨", "⚠️", "💢"):
            self.assertNotIn(icon, html)
        self.assertIn("mystery", html)

    # --- attach / 未绑定 text_log ---
    def test_flush_without_text_log_is_safe(self):
        mgr = self.make_manager()  # text_log=None
        mgr.log("dropped", "info")
        mgr.flush()  # 不抛异常，队列被消费
        self.assertTrue(mgr._queue.empty())

    def test_attach_binds_text_log_and_renders(self):
        text = FakeTextEdit()
        mgr = self.make_manager()
        mgr.log("hello", "info")
        mgr.attach(text)
        mgr.flush()
        self.assertIn("hello", text.html[0])

    # --- 半 cap 裁剪 ---
    def test_half_cap_trimming_keeps_newest(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, log_cap=4)
        for i in range(6):
            mgr.log(f"msg-{i}", "info")
        mgr.flush()
        html = text.html[0]
        self.assertNotIn("msg-0", html)
        self.assertNotIn("msg-1", html)
        self.assertNotIn("msg-2", html)
        self.assertNotIn("msg-3", html)
        self.assertIn("msg-4", html)
        self.assertIn("msg-5", html)

    def test_no_trimming_when_under_cap(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, log_cap=10)
        for i in range(3):
            mgr.log(f"msg-{i}", "info")
        mgr.flush()
        self.assertIn("msg-0", text.html[0])
        self.assertIn("msg-2", text.html[0])

    # --- 重置行（blockCount 超 cap 时清空并 append 翻译消息） ---
    def test_reset_when_block_count_exceeds_cap(self):
        text = FakeTextEdit(block_count=3)
        mgr = self.make_manager(text_log=text, log_cap=4)
        mgr.log("line-a", "info")
        mgr.log("line-b", "info")
        mgr.flush()
        self.assertTrue(text.cleared)
        self.assertEqual(len(text.appended), 1)
        # 重置文案按 HTML 转义规则处理：开头的 ">>>" 被转义为 "&gt;&gt;&gt;"
        self.assertIn("&gt;&gt;&gt; History erased, log restarts.", text.appended[0])

    def test_no_reset_when_under_block_cap(self):
        text = FakeTextEdit(block_count=0)
        mgr = self.make_manager(text_log=text, log_cap=4)
        mgr.log("line-a", "info")
        mgr.log("line-b", "info")
        mgr.flush()
        self.assertFalse(text.cleared)
        self.assertEqual(text.appended, [])

    def test_reset_message_is_html_escaped(self):
        def translate_with_special(key, **kwargs):
            return "History & <Lore>  reset"

        text = FakeTextEdit(block_count=3)
        mgr = self.make_manager(
            text_log=text, log_cap=4, translate=translate_with_special
        )
        mgr.log("line-a", "info")
        mgr.log("line-b", "info")
        mgr.flush()
        self.assertEqual(len(text.appended), 1)
        appended = text.appended[0]
        # 重置文案包含 & < > 等字符时也必须按同样规则转义，避免注入 HTML
        self.assertIn("History &amp; &lt;Lore&gt;", appended)
        self.assertNotIn("<Lore>", appended)
        # 双空格同样转换为 &nbsp;&nbsp;
        self.assertIn("&lt;Lore&gt;&nbsp;&nbsp;reset", appended)

    # --- 异常安全 ---
    def test_flush_is_exception_safe(self):
        text = FakeTextEdit()
        text.fail_insert_html = True
        mgr = self.make_manager(text_log=text)
        mgr.log("will fail", "info")
        mgr.flush()  # 不向上抛异常
        # 即使 insertHtml 抛异常，setUpdatesEnabled(True) 也必须在 finally 中执行
        self.assertTrue(text.updates)
        self.assertTrue(text.updates[-1])
        text.fail_insert_html = False
        mgr.log("recovers", "info")
        mgr.flush()  # 后续调用仍正常工作
        self.assertTrue(any("recovers" in h for h in text.html))

    def test_flush_re_enables_updates_when_append_raises(self):
        """append()（重置行）抛异常时也应恢复 setUpdatesEnabled(True)。"""
        text = FakeTextEdit(block_count=5)

        def fail_append(_html):
            raise RuntimeError("append boom")

        text.append = fail_append
        mgr = self.make_manager(text_log=text, log_cap=4)
        mgr.log("over cap", "info")
        mgr.flush()  # 不向上抛异常
        # 虽然 append 失败，updates 仍以 True 结尾
        self.assertTrue(text.updates)
        self.assertTrue(text.updates[-1])

    # --- 后台线程并发 log + 主线程反复 flush ---
    def test_concurrent_log_and_flush_is_safe_and_consistent(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, log_cap=100000)
        total = 2000
        stop_flag = threading.Event()
        errors = []

        def producer():
            try:
                for i in range(total):
                    mgr.log(f"t{i}", "info")
                    if i % 10 == 0:
                        time.sleep(0.0001)  # 让出 CPU，不构成时序断言
            except Exception as e:  # noqa: BLE001
                errors.append(e)
            finally:
                stop_flag.set()

        producer_thread = threading.Thread(target=producer)
        producer_thread.start()

        try:
            # 主线程在生产者运行期间反复 flush，直到生产者结束
            while not stop_flag.is_set():
                mgr.flush()
            mgr.flush()  # 收尾消费剩余消息
        except Exception as e:  # noqa: BLE001
            errors.append(e)
        producer_thread.join(timeout=10)
        self.assertFalse(producer_thread.is_alive())

        # 生产者线程不应抛出任何异常
        self.assertEqual(errors, [])

        # 队列最终应被消费为空
        self.assertTrue(mgr._queue.empty())

        # 所有消息最终可观察到（或至少队列一致：每条消息只被消费一次）
        rendered = "".join(text.html)
        for i in range(total):
            self.assertIn(f"t{i}", rendered)

    # --- set_log_cap / stop ---
    def test_set_log_cap_updates_trimming(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text, log_cap=1000)
        mgr.set_log_cap(4)
        for i in range(6):
            mgr.log(f"msg-{i}", "info")
        mgr.flush()
        self.assertIn("msg-4", text.html[0])
        self.assertNotIn("msg-0", text.html[0])

    def test_stop_prevents_further_processing(self):
        text = FakeTextEdit()
        mgr = self.make_manager(text_log=text)
        mgr.stop()
        mgr.log("after stop", "info")
        mgr.flush()
        self.assertEqual(text.html, [])
        self.assertTrue(mgr._queue.empty())

    def test_stop_is_idempotent(self):
        mgr = self.make_manager()
        mgr.stop()
        mgr.stop()
        mgr.log("x", "info")
        self.assertTrue(mgr._queue.empty())


if __name__ == "__main__":
    unittest.main()
