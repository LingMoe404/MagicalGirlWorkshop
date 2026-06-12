# “羁绊之证”纪念卡精简实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将“羁绊之证”从六项技术贡献列表精简为一张保留姓名、温和感谢文案和社交链接的纪念卡。

**Architecture:** 沿用现有 `CreditsInterface`、导航入口、卡片容器及语言/主题选择器，只移除贡献网格和重复页脚。界面继续通过现有翻译字典获取角色与正文，四种语言同步删除废弃键并保持键集合一致。

**Tech Stack:** Python 3.12、PySide6、QFluentWidgets、`unittest`、现有 i18n 翻译字典

---

## 文件结构

- Create: `tests/test_credits_interface.py`
  - 离屏创建 `CreditsInterface`，验证纪念卡保留项及旧结构移除。
- Modify: `ui/interfaces.py:593-744`
  - 精简 `CreditsInterface`，保留姓名、角色、正文和两个社交按钮。
- Modify: `i18n/locales/zh_CN.py:136-151`
- Modify: `i18n/locales/zh_TW.py:136-151`
- Modify: `i18n/locales/en_US.py:136-151`
- Modify: `i18n/locales/ja_JP.py:136-151`
  - 更新角色和正文，并删除六组贡献键及卡片页脚键。

### Task 1: 用界面测试锁定纪念卡结构

**Files:**
- Create: `tests/test_credits_interface.py`
- Test: `tests/test_credits_interface.py`

- [ ] **Step 1: 写入失败测试**

```python
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from i18n.translator import translator
from ui.interfaces import CreditsInterface


class CreditsInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.previous_language = translator.current_lang
        translator.current_lang = "zh_CN"

    def tearDown(self):
        translator.current_lang = self.previous_language

    def test_credits_page_is_a_compact_memorial_card(self):
        page = CreditsInterface()
        self.addCleanup(page.close)

        self.assertEqual(page.contributor_name.text(), "lose2me (REwaTLE)")
        self.assertEqual(page.role.text(), "启蒙协力")
        self.assertEqual(
            page.intro.text(),
            "感谢在工坊早期分享开发经验与工具链思路。\n\n"
            "那些最初的指引，已经成为独立探索更强术式的起点。",
        )
        self.assertEqual(page.btn_github.text(), "GitHub")
        self.assertEqual(page.btn_bili.text(), "Bilibili")
        self.assertFalse(hasattr(page, "contributions_data"))
        self.assertFalse(hasattr(page, "contribution_widgets"))
        self.assertFalse(hasattr(page, "footer_lbl"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认按预期失败**

Run:

```powershell
uv run python -m unittest discover -s tests -p test_credits_interface.py -v
```

Expected: `FAIL` 或 `ERROR`，首先指出 `CreditsInterface` 尚无 `contributor_name` 属性，或角色仍为旧文案。

### Task 2: 将贡献列表精简为纪念卡

**Files:**
- Modify: `ui/interfaces.py:593-744`
- Modify: `i18n/locales/zh_CN.py:136-151`
- Modify: `i18n/locales/zh_TW.py:136-151`
- Modify: `i18n/locales/en_US.py:136-151`
- Modify: `i18n/locales/ja_JP.py:136-151`
- Test: `tests/test_credits_interface.py`

- [ ] **Step 1: 精简姓名与社交按钮控件**

在 `CreditsInterface.init_ui()` 中将局部控件改成可测试的实例属性，并保持原链接不变：

```python
self.contributor_name = SubtitleLabel("lose2me (REwaTLE)", card)
self.role = BodyLabel(card)
self.role.setTextColor(QColor("#5f6368"), QColor("#a0a0a0"))

v_text.addWidget(self.contributor_name)
v_text.addWidget(self.role)
h_info.addLayout(v_text)
h_info.addStretch(1)

self.btn_github = PushButton(FluentIcon.GITHUB, "GitHub", card)
self.btn_github.clicked.connect(
    lambda: QDesktopServices.openUrl(QUrl("https://github.com/lose2me"))
)

self.btn_bili = PushButton(FluentIcon.VIDEO, "Bilibili", card)
self.btn_bili.clicked.connect(
    lambda: QDesktopServices.openUrl(QUrl("https://space.bilibili.com/341660795"))
)

h_info.addWidget(self.btn_github)
h_info.addWidget(self.btn_bili)
```

- [ ] **Step 2: 删除贡献网格和重复页脚**

从 `CreditsInterface.init_ui()` 删除：

- `self.contributions_data`
- `self.contribution_widgets`
- `QGridLayout` 创建及六个贡献项控件
- `self.footer_lbl`

保留正文，并启用换行：

```python
self.intro = BodyLabel(card)
self.intro.setWordWrap(True)
card_layout.addWidget(self.intro)
card_layout.addStretch(1)
```

`QGridLayout` 在同一文件的 `ProfileInterface` 中仍有使用，因此不要删除文件顶部的导入。

- [ ] **Step 3: 简化重翻译逻辑**

`CreditsInterface.retranslate_ui()` 只更新仍存在的动态文案：

```python
def retranslate_ui(self):
    """ 根据当前语言重新翻译界面文本。 """
    self.title.setText(tr("credits.title"))
    self.combo_theme.setItemText(0, tr("home.header.theme_combo.auto"))
    self.combo_theme.setItemText(1, tr("home.header.theme_combo.light"))
    self.combo_theme.setItemText(2, tr("home.header.theme_combo.dark"))
    self.role.setText(tr("credits.card.contributor_role"))
    self.intro.setText(tr("credits.card.intro"))
```

- [ ] **Step 4: 更新四种语言文案并删除废弃键**

每个语言文件只保留以下三个 `credits` 键：

```python
# i18n/locales/zh_CN.py
"credits.title": "羁绊之证",
"credits.card.contributor_role": "启蒙协力",
"credits.card.intro": "感谢在工坊早期分享开发经验与工具链思路。\n\n那些最初的指引，已经成为独立探索更强术式的起点。",
```

```python
# i18n/locales/zh_TW.py
"credits.title": "羈絆之證",
"credits.card.contributor_role": "啟蒙協力",
"credits.card.intro": "感謝在工坊早期分享開發經驗與工具鏈思路。\n\n那些最初的指引，已經成為獨立探索更強術式的起點。",
```

```python
# i18n/locales/en_US.py
"credits.title": "Proof of Bond",
"credits.card.contributor_role": "Early Guidance",
"credits.card.intro": "Thank you for sharing development experience and toolchain ideas during the workshop's early days.\n\nThose first lessons became the starting point for exploring stronger spells independently.",
```

```python
# i18n/locales/ja_JP.py
"credits.title": "絆の証",
"credits.card.contributor_role": "啓蒙協力",
"credits.card.intro": "工房の初期に、開発経験とツールチェーンの考え方を共有してくれたことに感謝します。\n\n最初の導きは、より強い術式を自ら探求するための出発点になりました。",
```

从四个文件中删除：

- `credits.contributions.item1.*` 至 `credits.contributions.item6.*`
- `credits.card.footer`

- [ ] **Step 5: 运行纪念卡测试并确认通过**

Run:

```powershell
uv run python -m unittest discover -s tests -p test_credits_interface.py -v
```

Expected: `Ran 1 test`，结果为 `OK`。

- [ ] **Step 6: 运行语言键一致性检查**

Run:

```powershell
uv run python check_lang.py
```

Expected: 四个语言文件语法均为 `OK`，并显示“所有语言文件检查通过”。

- [ ] **Step 7: 搜索并确认废弃结构已清除**

Run:

```powershell
rg -n "contributions_data|contribution_widgets|credits\.contributions|credits\.card\.footer|footer_lbl" ui/interfaces.py i18n/locales
```

Expected: 无输出，退出码为 `1`。

- [ ] **Step 8: 提交界面精简**

```powershell
git add tests/test_credits_interface.py ui/interfaces.py i18n/locales/zh_CN.py i18n/locales/zh_TW.py i18n/locales/en_US.py i18n/locales/ja_JP.py
git commit -m "feat: simplify credits into memorial card"
```

### Task 3: 完整回归验证

**Files:**
- Test: `tests/test_credits_interface.py`
- Verify: `ui/main_window.py`
- Verify: `ui/interfaces.py`
- Verify: `i18n/locales/*.py`

- [ ] **Step 1: 离屏初始化完整主窗口**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
uv run python -c "from PySide6.QtWidgets import QApplication; from ui.main_window import MainWindow; app=QApplication([]); w=MainWindow(); c=w.credits_interface; assert c.contributor_name.text() == 'lose2me (REwaTLE)'; assert c.role.text() == '启蒙协力'; assert c.btn_github.text() == 'GitHub'; assert c.btn_bili.text() == 'Bilibili'; assert not hasattr(c, 'contributions_data'); assert not hasattr(c, 'footer_lbl'); print('Credits memorial card smoke passed'); w.close(); app.processEvents()"
```

Expected: 输出 `Credits memorial card smoke passed`，进程退出码为 `0`。

- [ ] **Step 2: 运行完整测试集**

Run:

```powershell
uv run python -m unittest discover -s tests -v
```

Expected: 原有 80 项测试加新增 1 项测试，共 `Ran 81 tests`，结果为 `OK`。

- [ ] **Step 3: 检查最终差异与工作区**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` 无错误；提交完成后 `git status --short` 无输出。
