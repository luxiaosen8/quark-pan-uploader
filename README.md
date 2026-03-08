# Quark Uploader

一个基于 **Python 3.12 + PySide6** 的 Windows 桌面工具，用于批量上传本地内容到夸克网盘并生成分享链接。

## 功能概览

- 使用 Cookie 或官方登录流程连接夸克网盘
- 刷新并选择目标网盘目录
- 支持两种上传模式：
  - `batch_subfolders`：扫描本地根目录下一级子文件夹并逐项上传
  - `single_target`：直接上传单个文件夹或单个文件
- 为上传完成的远端项目创建分享链接
- 输出根目录汇总结果与按运行归档的详细结果
- 主界面采用“上栏操作区 + 下栏标签页工作台”布局，便于查看任务、目录与日志

## 环境要求

- Windows 10 / 11
- Python 3.12+
- 建议使用虚拟环境运行

## 安装

### 方式一：使用项目虚拟环境

```bat
python -m venv .venv
.\.venv\Scriptsctivate
python -m pip install -e .
```

### 方式二：使用 uv

```bat
uv sync
```

## 启动应用

```bat
python -m quark_uploader.main
```

如果你在虚拟环境中运行，也可以显式使用虚拟环境解释器：

```bat
.\.venv\Scripts\python.exe -m quark_uploader.main
```

## 使用流程

1. 输入 Cookie，或点击 **官方登录**
2. 点击 **刷新网盘** 获取远端目录
3. 选择本地来源（批量子文件夹 / 单文件夹 / 单文件）
4. 在远端目录中选择上传目标
5. 点击 **开始上传** 执行任务
6. 在任务页、目录页与日志页查看执行结果

## 输出与配置

默认输出目录为 `output/`。

运行时会使用：

- `output/`：结果与日志输出目录
- `.local/app_settings.json`：本地设置文件

程序会在运行时自动创建所需目录与文件；这些本地产物默认不应提交到版本控制。

## 打包

仓库已提供以下 Windows 打包文件：

- `scripts/build_windows.ps1`
- `quark_uploader.spec`
- `windows_version_info.txt`

执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scriptsuild_windows.ps1
```

## 安全说明

- 不要提交真实 Cookie、令牌、日志、`.env`、`.local/`、`output/` 或构建产物
- 如果需要共享问题样例，请先对 Cookie、链接、目录名和日志内容进行脱敏
- 调试模式下可能生成额外日志，请在公开分享前确认已清理

## 公开仓库说明

当前公开仓库聚焦于：

- 应用源码
- 打包脚本
- 面向公开协作的基础文档

内部测试资产、过程性设计草案和本地协作文档不包含在公开发布版本中。

## 许可证

本项目采用 [MIT License](./LICENSE)。

## 相关文档

- [SECURITY.md](./SECURITY.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
