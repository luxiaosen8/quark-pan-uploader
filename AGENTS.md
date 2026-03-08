# AGENTS.md

## 项目概览

- 名称：夸克网盘批量上传分享工具
- 技术栈：Python 3.12、PySide6、requests、pydantic、pytest、pytest-qt
- 入口：`src/quark_uploader/main.py`

## 主要目录

- `src/quark_uploader/gui/`：桌面 GUI 与控制器
- `src/quark_uploader/services/`：上传、分享、目录同步、结果写入等服务层
- `src/quark_uploader/quark/`：夸克 HTTP API 封装
- `tests/`：单元测试与 GUI 测试
- `docs/plans/`：设计文档与计划文档

## 常用命令

### 启动应用

```bat
C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m quark_uploader.main
```

### 运行测试

```bat
C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest -q
```

### Windows 打包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

## 本次修复后的关键规则

- 空一级子文件夹会标记为 `skipped`，不会进入上传或分享流程
- 异步上传时，单个任务失败会正确标记为 `failed`，并继续后续任务
- 刷新网盘失败会回退连接态，避免 UI 残留错误状态
- 输出目录同时保留根目录汇总结果与 `runs/<run_id>` 归档
- 设置文件中的持久化 Cookie 不以明文字段落盘

## 运行时路径

- 源码模式：输出目录和设置文件相对仓库根目录解析
- 打包 EXE 模式：输出目录和设置文件相对 EXE 所在目录解析
- 首次启动会自动创建：
  - `.local/app_settings.json`
  - `output/`
  - `output/logs/YYYY-MM-DD.jsonl` 中的 startup 日志

## UI 约束

- 前端测试用的“清理测试目录”按钮已从正式 UI 中移除


## Debug 启动跟踪

- 正式版默认不生成 `bootstrap_trace.log`
- 仅在 debug 模式启用：
  - 环境变量：`QUARK_UPLOADER_DEBUG=1`
  - 或设置文件：`debug_mode=true`

## UI 布局

- 主界面采用“顶部摘要 + 中区双栏 + 任务区 + 底部日志”的专业桌面工具布局
- `main_window.py` 中保留原有业务控件实例，主要通过卡片式容器和样式表增强表现层
- `controller.py` 只做小范围视图联动，例如当前选中远端目录摘要

- 操作区默认窗口高度下应尽量完整可见，优先避免滚动条与控件挤占；仅在极端窗口高度或 DPI 缩放下回退到滚动承接
