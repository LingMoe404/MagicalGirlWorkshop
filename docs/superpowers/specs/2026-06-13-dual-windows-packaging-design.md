# Windows 便携版与安装版双发行设计

## 目标

GitHub Actions 只编译一次 Windows 程序，同时发布：

- 无运行时解包的便携版 7z。
- 无运行时解包的用户级安装版 Setup.exe。

## 构建架构

Nuitka 从 `--onefile` 改为 `--standalone`，生成完整运行目录。工作流把 Nuitka 目录与外置 `tools` 目录合并为同一份暂存目录：

```text
build/package/MagicalGirlWorkshop/
  MagicalGirlWorkshop.exe
  Qt 与 Python 运行组件
  logo.ico
  LingMoe404.ico
  tools/
```

便携版和安装版都以该目录为唯一输入，避免两种发行物包含不同程序文件。

## 便携版

使用 7-Zip 将暂存目录压缩为：

```text
MagicalGirlWorkshop-v<版本>-Portable.7z
```

用户只需解压一次。启动程序时不会再释放到系统临时目录。

## 安装版

使用 Inno Setup 生成：

```text
MagicalGirlWorkshop-v<版本>-Setup.exe
```

默认安装到：

```text
%LOCALAPPDATA%\Programs\MagicalGirlWorkshop
```

该目录由当前用户拥有，现有 `config.ini` 和 `cache` 写入程序目录的逻辑无需迁移，也不要求管理员权限。

安装器行为：

- 创建开始菜单快捷方式。
- 提供可选桌面快捷方式。
- 支持覆盖升级和标准卸载。
- 安装完成后可选择启动程序。
- 卸载时删除程序生成的 `cache` 与 `config.ini`。

## 自动构建

工作流从 `config.py` 读取 `VERSION`，用于两种发行文件名和安装器版本。

构建完成后上传两个独立 artifact：

- `MagicalGirlWorkshop-Portable`
- `MagicalGirlWorkshop-Installer`

## 非目标

- 不继续提供 Nuitka onefile 版本。
- 不制作 MSI 或 MSIX。
- 不迁移应用配置目录。
- 不改变程序运行逻辑或外置工具查找方式。

## 验证

- YAML 可被标准解析器加载。
- 工作流不再包含 `--onefile`，并包含 `--standalone`。
- 暂存目录完整复制 Nuitka standalone 内容与 `tools`。
- Inno Setup 脚本使用用户级安装目录并递归安装暂存目录。
- 工作流分别生成和上传 Portable 与 Setup 产物。
- 现有 Python 自动化测试继续通过。
