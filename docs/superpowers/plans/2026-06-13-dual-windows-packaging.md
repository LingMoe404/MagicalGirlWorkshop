# Windows 双发行格式实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GitHub Actions 从 Nuitka onefile 改为一次 standalone 构建，并生成便携版 7z 与用户级 Inno Setup 安装版。

**Architecture:** `build/nuitka/main.dist` 是唯一编译产物，复制到统一暂存目录并加入 `tools`。7-Zip 与 Inno Setup 分别消费该暂存目录，版本号统一从 `config.py` 读取。

**Tech Stack:** GitHub Actions、PowerShell、Nuitka standalone、7-Zip、Inno Setup

---

### Task 1: 创建安装器定义

**Files:**
- Create: `installer/MagicalGirlWorkshop.iss`

- [ ] 定义稳定 `AppId`、应用元数据和用户级安装目录。
- [ ] 递归安装工作流传入的暂存目录。
- [ ] 创建开始菜单与可选桌面快捷方式。
- [ ] 添加安装后启动项和卸载缓存清理规则。

### Task 2: 改造自动构建

**Files:**
- Modify: `.github/workflows/autobuild.yml`

- [ ] 从 `config.py` 读取版本并写入 `GITHUB_ENV`。
- [ ] 将 Nuitka 参数从 `--onefile` 改为 `--standalone`。
- [ ] 将 `main.dist` 和 `tools` 合并到统一暂存目录。
- [ ] 生成带版本号的 Portable 7z。
- [ ] 确保 Inno Setup 可用并编译 Setup.exe。
- [ ] 显示两种产物大小并分别上传 artifact。

### Task 3: 验证

- [ ] 使用 PyYAML 解析工作流文件。
- [ ] 搜索确认构建命令不再包含 `--onefile`。
- [ ] 静态检查 Inno Setup 的用户级目录、源目录、快捷方式与卸载规则。
- [ ] 运行完整 Python 测试集。
- [ ] 检查最终 diff 和 Git 工作区。
