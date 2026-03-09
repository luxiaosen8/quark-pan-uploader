# 上传并发、UI 一致性与性能优化 Analyze

## 1. 分析目标

本分析聚焦四个问题：

1. 当前仓库里，真正限制上传吞吐的瓶颈在哪里。
2. 如果引入 job 并发与 multipart 分片并发，最容易出问题的共享状态是什么。
3. 当前 PySide6 UI 的一致性缺口和性能热点在哪里。
4. 在不扩大变更面、不引入新依赖的前提下，最稳妥的实现路径是什么。

## 2. 分析范围

### 2.1 主要代码文件

- `src/quark_uploader/gui/workers.py`
- `src/quark_uploader/gui/controller.py`
- `src/quark_uploader/gui/main_window.py`
- `src/quark_uploader/gui/official_login_dialog.py`
- `src/quark_uploader/services/upload_executor.py`
- `src/quark_uploader/services/quark_file_uploader.py`
- `src/quark_uploader/services/oss_transport.py`
- `src/quark_uploader/services/result_writer.py`
- `src/quark_uploader/settings.py`
- `src/quark_uploader/services/settings_store.py`

### 2.2 既定前提

基于前序 clarify，当前分析默认以下决策已经成立：

- 默认 `job_concurrency = 2`
- 默认 `part_concurrency = 3`
- 并发参数第一阶段仅进入配置，不暴露到 UI
- 登录弹窗第一阶段先统一状态与样式，不强制立即切换 Qt 线程模型
- `result_writer` 必须按非线程安全对象处理
- UI 节流采用聚合刷新策略

## 3. 当前实现现状

### 3.1 上传链路拓扑清晰，但执行粒度全是串行

当前上传主链路是：

`controller -> worker -> executor -> uploader -> transport`

对应证据：

- `gui/controller.py` 负责构建计划、创建 worker、连接 UI 信号
- `gui/workers.py` 负责后台执行入口
- `services/upload_executor.py` 负责单个 job 的上传和分享生成
- `services/quark_file_uploader.py` 负责单文件上传与 multipart 流程
- `services/oss_transport.py` 负责 PUT / POST 到 OSS

但当前真正的执行粒度仍是三级串行：

1. `UploadWorker.run()` 对 `plan.jobs` 串行执行。
2. `UploadExecutionEngine.execute_job()` 对 `job.file_entries` 串行执行。
3. `QuarkFileUploader._upload_multiple_parts()` 对 multipart chunk 串行执行。

结论：当前只有“后台线程避免阻塞 UI”，没有真正的吞吐并发。

### 3.2 远端接口语义已经为并发留口子，但本地实现未兑现

`quark/upload_api.py` 的 `build_upload_pre_payload()` 已经包含：

- `ccp_hash_update = True`
- `parallel_upload = True`

这说明远端上传协议并不排斥并发语义；问题主要在本地调度层没有把它实现出来。

### 3.3 UI 主线程边界基本正确，但信号粒度过细

当前 UI 更新主路径相对安全：

- `UploadWorker` 运行在 `QThread`
- worker 通过 `task_status`、`progress_summary`、`current_action`、`log_message` 发信号
- `controller.py` 把这些信号连接到 `MainWindow` 的 UI 更新方法

这意味着：

- 主要问题不是“后台线程直接改 UI”
- 而是“后台线程把过于细粒度的事件不断推给 UI”

## 4. 关键瓶颈与风险点

### 4.1 第一风险：`ResultWriter` 不是线程安全的

`services/result_writer.py` 当前行为：

- `append_share_url()` 直接追加文本文件
- `append_share_result()` 同时写 JSONL 和 CSV
- `append_event()` 直接写 events JSONL，并调用 `StructuredLogger.log()`
- `StructuredLogger.log()` 也是直接追加 JSONL

这些方法都没有锁、没有单写入队列、没有串行保护。

**结论：** 一旦 job 并发打开，这里是最明确的共享可变资源风险点。它会带来：

- JSONL 行交叉或写入顺序混乱
- CSV 头/行竞争
- 同一任务终态和中间事件交错，影响诊断

### 4.2 第二风险：取消语义会在并发后失去一致性

当前 `UploadCancellationToken` 只是一个 `threading.Event` 包装，语义是：

- 发出停止请求后，执行链在安全点 `raise_if_cancelled()`

这对串行流程足够，但并发后会出现新的竞态：

1. 用户点停止时，某些 chunk 已提交，某些尚未提交。
2. 某个 job 已写成功结果，但协调层还没汇总。
3. UI 先显示“已停止”，底层某些请求随后又回来了成功结果。

**结论：** 并发后必须把“最终终态裁决权”收拢到协调层，不能让任意局部成功/失败直接决定最终状态。

### 4.3 第三风险：UI 高频更新会抵消并发收益

`main_window.py` 中几个关键热点：

- `append_log()`：直接 `appendPlainText()`
- `update_task_status()`：每次线性扫描整张表，再新建 `QTableWidgetItem`
- `set_progress_summary()`：同时更新文本和进度条
- `set_current_action()`：直接更新 label 文本

`workers.py` 中几个高频发射点：

- 每个 job 开始发 `task_status`
- 每个失败/完成都会再发 `task_status`
- `_emit_progress_action()` 会按文件/阶段/分片发 `current_action`
- 执行器 logger 通过 `log_message` 直接推 UI

**结论：** 如果在并发后继续让每个 chunk 都触发 UI 刷新，主线程会被日志和文本重绘拖慢，最终吞吐提升会被部分吃掉。

### 4.4 第四风险：UI 视觉规则分散且跨窗口割裂

`MainWindow._apply_styles()` 集中管理主窗口 QSS，但 `OfficialLoginDialog`：

- 没有复用主窗口样式契约
- 几乎没有 objectName / 状态态样式规则

此外：

- 主窗口状态 chip 使用 `state` 属性切换样式
- 任务表状态颜色使用 `_status_color()` 另一套映射
- 任务表状态文本直接显示枚举值，和中文 UI 其他部分不一致

**结论：** 当前 UI 的主要问题不是“控件少样式”，而是“状态文案、状态颜色、状态反馈入口是分散的”。

## 5. 模块级实现切入点

### 5.1 `gui/workers.py`：并发协调层

这是 job 并发的第一落点，适合承担：

- job 调度上限控制
- stop 后不再派发新 job
- 任务结果聚合
- UI 更新事件聚合出口

不建议在第一轮就把太多业务逻辑压到 controller 或 executor；worker 更适合作为“协调层”。

### 5.2 `services/upload_executor.py`：job 级边界层

这里最适合保证：

- 单个 job 的状态隔离
- 单个 job 的重试逻辑
- 单个 job 的分享生成语义
- 向 result writer 写入前的最终结果整形

它不应该成为“全局并发管理器”，否则职责会迅速膨胀。

### 5.3 `services/quark_file_uploader.py`：multipart 并发层

这里最适合只做一件事：

- 对一个文件内部的分片上传做受控并发

必须保持的关键不变量：

- `part_number -> etag` 映射稳定
- complete XML 顺序正确
- 失败时整文件失败
- stop 后不再创建新 chunk 任务

### 5.4 `services/result_writer.py`：单写入通道

这是最需要先加保护的模块。第一版建议：

- 不把它开放给多个并发执行上下文“自由写”
- 要么内部加锁
- 要么通过单 writer 队列/单写入线程串行化

对当前代码体量而言，**最小可落地方案**是：

- 先在 `ResultWriter` 内部加最小串行保护
- 后续若 benchmark 证明 I/O 成为瓶颈，再升级为专门 writer 通道

## 6. 外部实践对本仓库的适用结论

基于 Qt 官方线程基础文档和公开社区经验，可归纳出三条对本仓库最有用的规则：

1. **UI 只能在主线程更新**
   - 后台线程应通过 signal/slot 或投递事件让主线程更新控件
   - 这与当前 `worker -> controller -> main_window` 的主路径一致，应保持

2. **QThread / Qt 信号机制更适合长期 UI 协调任务；Python `threading.Thread` 可存在，但不应直接碰 UI**
   - 这意味着 `OfficialLoginDialog` 第一阶段可以保留 Python 线程，只要结果仍通过信号或主线程回调收束

3. **`QPlainTextEdit` 适合日志场景，但高频 `appendPlainText()` 仍会造成重绘压力**
   - 当前代码已经设置了 `setMaximumBlockCount(1000)`，这是正确方向
   - 但仍需要批量 flush 或节流，不能把“块数限制”当作性能优化的全部

## 7. 推荐实现顺序

### 阶段 A：先稳定，不先追求最大吞吐

1. 补齐测试骨架
2. 引入设置模型（`job_concurrency=2`, `part_concurrency=3`, UI 节流参数）
3. 给 `ResultWriter` 增加串行保护

### 阶段 B：先做 job 并发，再做 chunk 并发

4. 重构 `workers.py` 为受控 job 并发调度
5. 确保 stop / 汇总 / run_finished 语义稳定
6. 确保 `upload_executor.py` 在多 job 并发下仍保持状态隔离

### 阶段 C：再引入 multipart 并发

7. 重构 `_upload_multiple_parts()` 为受限 chunk 池
8. 用测试锁死 ETag 顺序、失败传播、停止语义

### 阶段 D：最后做 UI 节流与一致性收敛

9. 优化 `update_task_status()` 为 O(1) 行定位
10. 对 `append_log()` / `current_action` / `progress_summary` 做聚合刷新
11. 抽离主窗口样式契约，并让登录弹窗复用

## 8. 第一版最应该避免的做法

1. 不要同时改：
   - job 并发
   - chunk 并发
   - result writer 模式
   - 登录弹窗线程模型

2. 不要让后台线程直接调用 `MainWindow` 方法。

3. 不要采用“每个 chunk 一条日志 / 一次 UI 刷新”的策略。

4. 不要把 result writer 只做“随手加锁”然后开放给任意层滥用；第一版要明确它是单写入通道。

5. 不要在 phase 1 引入动态并发调节、复杂优先级队列或更大范围 UI 重构。

## 9. 关键不变量

实现期间必须始终保证：

1. 任意 QWidget 更新都只能在主线程执行。
2. 一个 job 只能有一个最终终态：`completed` / `failed` / `stopped` 三选一。
3. stop 后不得再派发新的 job 或新的 chunk。
4. `ResultWriter` 任一时刻只能被单一写入上下文触达。
5. UI 展示应来源于聚合后的快照，而不是底层每一个细粒度事件。

## 10. 最终判断

当前仓库**完全适合**做这轮优化，但第一阶段应坚持“稳态优先”的工程策略。

最核心的判断是：

- 真正的首要风险不是 multipart 并发本身，
- 而是 **并发后状态一致性、结果落盘串行化、以及主线程 UI 压力控制**。

只要先解决这三个问题，再逐步打开 `job_concurrency=2` 和 `part_concurrency=3`，这次改造大概率能在不扩大风险面的前提下，拿到可见吞吐提升和更稳定的 UI 体验。
