# 上传并发、UI 一致性与性能优化 Tasks

## 默认决策（执行本任务清单时默认采用）

- [x] 默认 `job_concurrency = 2`
- [x] 默认 `part_concurrency = 3`
- [x] 并发参数第一阶段仅进入配置，不暴露到主界面
- [x] 登录弹窗第一阶段优先统一状态与样式，不强制立即切换 Qt 线程模型
- [x] benchmark 使用“小文件 / 大文件 / 混合”三组固定样本
- [x] `result_writer` 按非线程安全对象处理，增加并发保护
- [x] UI 节流采用聚合刷新策略
- [x] 本轮必须补建最小测试体系

---

## Phase 1：测试与配置基础

### 1. 建立测试骨架
- [ ] 创建 `tests/services/`
- [ ] 创建 `tests/gui/`
- [ ] 创建 `tests/integration/`
- [ ] 在 `pyproject.toml` 中确认测试依赖可直接运行

### 2. 固化当前串行基线
- [ ] 为 `UploadExecutionEngine.execute_job()` 添加串行行为测试
- [ ] 为 `UploadWorker.run()` 添加顺序执行与 stop 行为测试
- [ ] 为 `MainWindow._apply_styles()` 添加现有交互样式基线测试
- [ ] 记录“当前串行实现”的测试预期，作为回归基线

### 3. 引入并发配置模型
- [ ] 在 `src/quark_uploader/settings.py` 增加并发与 UI 节流字段
- [ ] 在 `src/quark_uploader/services/settings_store.py` 支持新字段读写与旧配置兼容
- [ ] 在 `src/quark_uploader/gui/controller.py` 接入配置加载
- [ ] 为默认值、异常值回退、旧配置兼容补充测试

### Phase 1 验收
- [ ] `tests/services/test_upload_settings.py` 通过
- [ ] `tests/services/test_upload_executor.py` 通过
- [ ] `tests/gui/test_upload_worker.py` 通过
- [ ] `tests/gui/test_main_window_styles.py` 通过

---

## Phase 2：任务级并发

### 4. 改造 worker 为受控 job 并发
- [ ] 重构 `src/quark_uploader/gui/workers.py`，支持多个 `UploadJob` 并发执行
- [ ] 保持所有 UI 更新通过 signal 回到主线程
- [ ] 保证 stop 后不再启动新的 job
- [ ] 保证 completed / failed / stopped 汇总统计准确

### 5. 让 controller 适配并发 worker
- [ ] 更新 `src/quark_uploader/gui/controller.py` 中 worker handle 构建逻辑
- [ ] 确保 start / stop / run_finished 行为在并发场景下语义不变
- [ ] 确保任务表初始化与状态回写在并发场景下仍然稳定

### 6. 让执行引擎适配多 job 并发
- [ ] 审查 `src/quark_uploader/services/upload_executor.py` 的共享状态
- [ ] 补充并发上下文日志字段：任务名、文件名、阶段、重试次数
- [ ] 确认分享、失败、结果写入不会跨任务串扰
- [ ] 为并发执行场景补充单元测试

### 7. 保护结果写入
- [ ] 为 `result_writer.append_event()` / `append_share_result()` 增加并发保护
- [ ] 确保并发写入下日志与结果仍然结构完整
- [ ] 为结果写入顺序和完整性补充测试

### Phase 2 验收
- [ ] `tests/gui/test_upload_worker_concurrency.py` 通过
- [ ] `tests/services/test_upload_executor_concurrency.py` 通过
- [ ] 默认 `job_concurrency = 2` 下可观察到多个 job 并发执行
- [ ] stop 后不再调度新的 job

---

## Phase 3：分片级并发

### 8. 改造 multipart 上传为并发分片池
- [ ] 重构 `src/quark_uploader/services/quark_file_uploader.py::_upload_multiple_parts`
- [ ] 建立“分片任务生成 → 并发执行 → 有序结果收集”流程
- [ ] 保证 `part_number -> etag` 映射稳定
- [ ] 保证 complete XML 顺序正确

### 9. 适配底层传输层
- [ ] 审查 `src/quark_uploader/services/oss_transport.py` 是否满足并发调用要求
- [ ] 保证 chunk 上传失败会正确上抛并触发文件级失败/重试
- [ ] 保证 stop 后不再提交新的 chunk

### 10. 补齐 multipart 并发测试
- [ ] 测试 ETag 顺序正确
- [ ] 测试单分片失败导致整文件失败
- [ ] 测试 stop 生效后不再产生新 chunk 任务
- [ ] 测试默认 `part_concurrency = 3` 下行为稳定

### Phase 3 验收
- [ ] `tests/services/test_quark_file_uploader_multipart.py` 通过
- [ ] 大文件 multipart 上传在默认配置下优于串行版本
- [ ] 未出现明显 ETag 乱序、complete 失败或分片悬空状态

---

## Phase 4：UI 一致性

### 11. 统一主窗口交互样式契约
- [ ] 更新 `src/quark_uploader/gui/main_window.py::_apply_styles`
- [ ] 为 `QLineEdit` 增加 focus 态
- [ ] 为 `QTreeWidget` 增加 focus / selected 强化规则
- [ ] 为 `QTableWidget` 增加 focus / selected 强化规则
- [ ] 为 `QPlainTextEdit` 增加 focus 态
- [ ] 保持按钮 hover / checked / disabled 语义一致

### 12. 统一登录弹窗视觉语义
- [ ] 更新 `src/quark_uploader/gui/official_login_dialog.py` 的按钮、状态文本、容器样式
- [ ] 统一 busy / validating / success / waiting 状态反馈
- [ ] 保证登录弹窗与主窗口使用同一颜色语义

### 13. 补齐 UI 一致性测试
- [ ] 新增 `tests/gui/test_ui_interaction_consistency.py`
- [ ] 校验关键选择器、objectName、动态属性规则存在
- [ ] 校验主窗口与登录弹窗都具备 hover / focus / disabled / busy 反馈

### Phase 4 验收
- [ ] `tests/gui/test_ui_interaction_consistency.py` 通过
- [ ] 主窗口与登录弹窗不再出现“有的控件有 hover / focus，有的没有”的不一致表现

---

## Phase 5：UI 性能与节流

### 14. 节流当前动作与进度刷新
- [ ] 为 `current_action` 引入聚合刷新策略
- [ ] 为 `progress_summary` 引入节流或批量更新策略
- [ ] 确保最终状态不会因节流丢失

### 15. 优化日志刷新
- [ ] 将 `MainWindow.append_log()` 改造为批量 flush 友好形式
- [ ] 避免每个 chunk 事件都立即刷新日志控件
- [ ] 保留足够的诊断信息用于排障

### 16. 优化任务表状态更新
- [ ] 改造 `MainWindow.update_task_status()`，优先更新已有 item
- [ ] 避免高频状态变化时频繁新建 `QTableWidgetItem`
- [ ] 仅在状态真实变化时更新任务行

### 17. 补齐 UI 节流测试
- [ ] 新增 `tests/gui/test_ui_update_throttling.py`
- [ ] 模拟高频事件输入
- [ ] 校验 UI 刷新频率下降且最终状态正确

### Phase 5 验收
- [ ] `tests/gui/test_ui_update_throttling.py` 通过
- [ ] 高并发下 UI 不出现明显闪烁、刷屏、卡顿或假死

---

## Phase 6：登录状态流与后台执行一致性

### 18. 统一登录弹窗状态流
- [ ] 梳理“等待登录中 / 正在验证 / 验证成功 / 继续等待”状态流
- [ ] 保证状态文本、按钮反馈、完成行为可预测
- [ ] 保证 UI 更新通过安全回调返回主线程

### 19. 评估 Qt 线程模型替换窗口
- [ ] 评估是否将 `threading.Thread` 替换为 Qt 异步执行
- [ ] 若暂不替换，明确记录原因与后续迁移点
- [ ] 保证本轮实现不依赖立即替换线程模型

### 20. 补齐登录弹窗测试
- [ ] 新增 `tests/gui/test_official_login_dialog.py`
- [ ] 测试 Cookie 变化触发校验
- [ ] 测试状态文本变化与成功 accept 行为

### Phase 6 验收
- [ ] `tests/gui/test_official_login_dialog.py` 通过
- [ ] 登录弹窗状态反馈与主窗口语义一致

---

## Phase 7：性能基线、回归与文档

### 21. 建立 benchmark 脚本与样本说明
- [ ] 创建 `scripts/benchmark_upload_modes.py`
- [ ] 创建 `docs/plans/benchmark-dataset-notes.md`
- [ ] 定义小文件 / 大文件 / 混合三组样本
- [ ] 记录总耗时、平均吞吐、失败数、UI 响应观察结果

### 22. 建立 benchmark smoke test
- [ ] 创建 `tests/integration/test_upload_benchmark_smoke.py`
- [ ] 确保 benchmark 脚本在模拟环境可跑通

### 23. 回归所有上传入口
- [ ] 单文件上传回归
- [ ] 单文件夹上传回归
- [ ] 批量子文件夹上传回归
- [ ] 停止上传回归
- [ ] 分享链接生成回归
- [ ] 登录弹窗获取 Cookie 回归

### 24. 更新对外文档
- [ ] 更新 `README.md`：说明并发上传、交互优化、性能注意事项
- [ ] 更新 `CONTRIBUTING.md`：补充并发/性能验证要求
- [ ] 创建 `docs/plans/verification-checklist-upload-concurrency.md`

### Phase 7 验收
- [ ] `python scripts/benchmark_upload_modes.py` 可运行
- [ ] `pytest tests/integration/test_upload_benchmark_smoke.py -v` 通过
- [ ] `pytest -v` 通过
- [ ] `python -m quark_uploader.main` 可启动
- [ ] 默认并发配置下总耗时优于串行实现

---

## 最终完成定义

- [ ] 默认并发配置下上传总体耗时优于当前串行版本
- [ ] 停止、重试、分享、结果写入语义保持兼容
- [ ] 主窗口与登录弹窗核心控件具备统一 hover / focus / disabled / busy 反馈
- [ ] 大量任务与日志下 UI 仍可响应
- [ ] 测试、benchmark、回归清单、README、CONTRIBUTING 全部更新完成
