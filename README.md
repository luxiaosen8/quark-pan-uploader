# 夸克网盘批量上传分享工具

一个基于 **Python + PySide6** 的 Windows 桌面工具，用于：

- 使用夸克网盘 Cookie 刷新网盘目录
- 选择本地根目录后，按 **一级子文件夹** 构建上传任务
- 将每个一级子文件夹递归上传到选定的网盘目录
- 在每个子文件夹上传完成后创建分享链接
- 实时写入 `share_links.txt`、汇总结果 CSV 和按运行归档的明细结果

## 环境要求

- Windows 10 / 11
- Python 3.12+
- 已安装项目依赖（推荐使用仓库内 `.venv`）

## 安装与运行

### 1. 安装依赖

如果你已经有仓库内虚拟环境，可以直接复用；否则请先按项目习惯安装依赖。

### 2. 启动 GUI

```bat
C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m quark_uploader.main
```

## 使用说明

1. 在主界面粘贴 Cookie，或点击 **官方登录**
2. 点击 **刷新网盘**，确认目录树加载成功
3. 点击 **选择本地文件夹**，扫描本地一级子文件夹
4. 在网盘目录树中选择目标目录
5. 点击 **开始上传**
6. 上传完成后，在输出目录查看分享链接和明细结果

### 空目录规则

- 本地根目录下的空一级子文件夹会显示在任务表格中
- 这类任务会被标记为 `skipped`
- 不会进入远端创建目录、上传或分享流程

## 输出文件

默认输出目录：`output`

### 根目录汇总产物

- `output/share_links.txt`：一行一个分享链接
- `output/share_results.csv`：跨运行汇总的结果 CSV
- `output/logs/YYYY-MM-DD.jsonl`：按日期写入的结构化日志

### 单次运行归档

- `output/runs/<run_id>/share_results.jsonl`
- `output/runs/<run_id>/share_results.csv`
- `output/runs/<run_id>/events.jsonl`
- `output/runs/<run_id>/cleanup_results.jsonl`
- `output/runs/<run_id>/cleanup_results.csv`

## 配置与安全

设置文件路径：`.local/app_settings.json`

当前支持的主要配置项：

- `output_dir`
- `request_timeout_seconds`
- `file_retry_limit`
- `share_retry_limit`
- `share_poll_max_retries`
- `retry_backoff_base_seconds`
- `share_poll_interval_seconds`

> 注意：持久化 Cookie 时，不会以明文字段直接写入设置文件。

## 测试

运行全量测试：

```bat
C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest -q
```

运行重点测试：

```bat
C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\services -q
C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui -q
```

## 打包

仓库已提供：

- `scripts/build_windows.ps1`
- `quark_uploader.spec`

执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

如果本地尚未安装 PyInstaller，脚本会提示你先安装。

## 常见问题

### 刷新网盘失败

常见原因：

- Cookie 失效
- 网络异常
- 接口返回异常

程序会回退连接状态，并保留本地目录扫描结果，便于重试。

### 任务显示 `retrying`

表示上传或分享在失败后进入重试流程，系统会按配置进行退避等待。

### 任务显示 `failed`

表示该一级子文件夹任务最终失败，可查看：

- 表格状态
- 日志面板
- `share_results.csv` / `share_results.jsonl`
