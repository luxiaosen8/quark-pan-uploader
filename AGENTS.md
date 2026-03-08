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

## 仓库清理与发布准备

- 上传仓库前应优先清理本地构建产物、缓存目录和调试残留，避免误提交无关文件
- `debug_large/`、`debug_small/`、`debug_stop/`、`cleanup-output/`、`custom-output/` 视为本地调试/输出目录，不应纳入版本控制
- 构建产物与运行输出目录（如 `build/`、`dist/`、`output/`、`.local/`、`.pytest_cache/`）应保持本地可清理状态

## UI 约束

- 前端测试用的“清理测试目录”按钮已从正式 UI 中移除


## Debug 启动跟踪

- 正式版默认不生成 `bootstrap_trace.log`
- 仅在 debug 模式启用：
  - 环境变量：`QUARK_UPLOADER_DEBUG=1`
  - 或设置文件：`debug_mode=true`

## UI 布局

- 主界面采用“上栏全宽操作区 + 下栏标签页工作台”的专业桌面工具布局
- 上栏操作区内嵌状态摘要条与三分栏操作面板，作为默认主交互区
- 下栏通过标签页承载“上传任务 / 目标网盘目录 / 运行日志”，默认展示“上传任务”页
- 当用户从其他标签页点击“开始上传”时，界面应自动切回“上传任务”页
- `main_window.py` 中保留原有业务控件实例，主要通过卡片式容器、标签页和样式表增强表现层
- `controller.py` 只做小范围视图联动，例如当前选中远端目录摘要
- 当前选中的远端目录摘要应始终在上栏可见，避免必须切换标签页才能确认目标位置
- 操作区默认窗口高度下应尽量完整可见，优先避免滚动条与控件挤占；仅在极端窗口高度或 DPI 缩放下回退到滚动承接

## 性能与日志 UI

- 登录页 Cookie 校验采用异步执行，避免在 UI 线程中同步网络校验导致卡顿
- 主页面日志区使用 `QPlainTextEdit` 作为纯文本日志面板，并限制最大日志块数以改善性能
- 主页面中下区域使用更均衡的工作区布局，保证任务表格和日志区都具备基本可读性

## 上传模式

- 支持两种上传模式：
  - `batch_subfolders`：扫描本地根目录下一级子文件夹并批量上传
  - `single_target`：直接上传一个文件夹或一个文件
- 单文件夹模式：递归上传该文件夹内容，并分享远端文件夹
- 单文件模式：直接上传该文件，并分享远端文件本身
- 任务表格第一列统一表示为“任务名称”，以兼容文件和文件夹任务

## 单目标上传模式

- 支持 `single_target` 模式，允许直接选择一个文件夹或一个文件作为上传来源
- 单文件夹任务：递归上传该文件夹内容，远端保留文件夹名，并分享远端文件夹
- 单文件任务：直接上传文件到当前远端目标目录，并分享远端文件本身
- 结果记录会区分 `remote_item_type = folder / file`
