# 打包与发布（从 AGENTS.md §2 打包片段与 §5.2 移出）

平台仅 Windows 10/11。产物为 Nuitka standalone 目录，再封装成 7z 便携版与
Inno Setup 用户级安装版。CI 流程见 `.github/workflows/autobuild.yml`。

## 本地复现 CI 核心步骤

```bash
# 读取版本（写入便携版/安装版名与元数据）
$version = uv run python -c "from config import VERSION; print(VERSION)"

# Nuitka standalone 编译
uv run --locked --with nuitka python -m nuitka main.py `
  --standalone --windows-console-mode=disable `
  --enable-plugin=pyside6 --assume-yes-for-downloads `
  --windows-icon-from-ico=logo.ico `
  --include-data-file=logo.ico=logo.ico `
  --include-data-file=LingMoe404.ico=LingMoe404.ico `
  --include-package=i18n `
  --output-dir=build/nuitka `
  --output-filename=MagicalGirlWorkshop.exe
```

编译产物位于 `build/nuitka/main.dist`，CI 步骤七把该目录与 `tools/` 合并到
`build/package/MagicalGirlWorkshop`，再用同一份暂存目录分别产出便携版与安装版
（步骤九/步骤十），最后上传 `MagicalGirlWorkshop-Portable` 与
`MagicalGirlWorkshop-Installer` 两个 artifact。

## 打包约束（必须遵守）

- `i18n` 包必须用 `--include-package=i18n` 显式包含，否则 `pkgutil` 动态加载在编译后失效。
- 资源文件用 `resource_path()` 解析，它兼容 PyInstaller `_MEIPASS` 和 Nuitka 两种打包方式。
- `tools/` 下的 exe 在打包时由 CI 单独复制到产物目录（见 `autobuild.yml` 步骤七），
  **不进** Nuitka 编译；它们是外部二进制依赖，不要当源码修改。
- `installer/` 下是 Inno Setup 脚本；改动后运行
  `uv run python -m unittest tests.test_packaging_config`。

## 两个工作流的分工

- `.github/workflows/verify.yml`：push 到 main / 任意 PR / 手动触发时运行 lint + 单元测试 +
  i18n 校验（`QT_QPA_PLATFORM: offscreen`），**不产出任何打包资产**；这是提 PR 时的验证门槛。
- `.github/workflows/autobuild.yml`：push 到 main（非文档改动）或手动触发时执行完整编译，
  产出 Release 资产。**push 前确认不会触发非预期的全量构建。**
