# Security Policy

## Supported Scope

当前公开仓库主要维护应用源码、打包脚本与基础文档。

## Reporting Guidance

如果你发现安全问题，请遵循以下原则：

- **不要**在公开 Issue 中粘贴真实 Cookie、令牌、日志或个人隐私数据
- 提交问题前先完成脱敏，至少移除：
  - Cookie / Token
  - 本地绝对路径
  - 分享链接中的敏感参数
  - 个人目录名、账号信息、日志中的隐私字段
- 如果问题依赖真实凭据，请先自行轮换或作废相关凭据，再进行报告

## Sensitive Data That Must Not Be Committed

以下内容不得提交到仓库：

- `.env` 与 `.env.*`
- `.local/`
- `output/`
- `build/` / `dist/`
- `bootstrap_trace.log` 与其他运行日志
- 任何真实 Cookie、访问令牌、分享密钥或个人隐私数据
