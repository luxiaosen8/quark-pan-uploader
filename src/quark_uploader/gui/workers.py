from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Signal, Slot

from quark_uploader.services.cancellation import UploadCancellationToken


@dataclass
class WorkerState:
    running: bool = False
    stop_requested: bool = False


class UploadWorker(QObject):
    task_status = Signal(str, str, str, int)
    progress_summary = Signal(int, int, int)
    current_action = Signal(str)
    log_message = Signal(str)
    run_finished = Signal(str)

    def __init__(self, plan, executor_factory, cancel_token: UploadCancellationToken) -> None:
        super().__init__()
        self.plan = plan
        self.executor_factory = executor_factory
        self.cancel_token = cancel_token

    def _build_executor(self):
        try:
            executor = self.executor_factory(self.log_message.emit)
        except TypeError:
            executor = self.executor_factory()
            if hasattr(executor, 'logger'):
                executor.logger = self.log_message.emit
            if hasattr(executor, 'uploader') and hasattr(executor.uploader, 'logger'):
                executor.uploader.logger = self.log_message.emit
            if hasattr(executor, 'share_service') and hasattr(executor.share_service, 'logger'):
                executor.share_service.logger = self.log_message.emit
        return executor


    def _emit_progress_action(self, payload: dict) -> None:
        file_name = payload.get("file_name", "")
        phase = payload.get("phase", "")
        part_number = payload.get("part_number", 0)
        part_total = payload.get("part_total", 0)
        if part_total:
            self.current_action.emit(f"当前文件：{file_name} | 阶段：{phase} | 分片 {part_number}/{part_total}")
        else:
            self.current_action.emit(f"当前文件：{file_name} | 阶段：{phase}")

    @Slot()
    def run(self) -> None:
        executor = self._build_executor()
        total = len(self.plan.jobs)
        completed = 0
        failed = 0
        final_state = 'completed'
        try:
            for index, job in enumerate(self.plan.jobs):
                if self.cancel_token.is_cancelled():
                    for pending_job in self.plan.jobs[index:]:
                        self.task_status.emit(pending_job.local_name, 'stopped', '', 0)
                    final_state = 'stopped'
                    break
                self.current_action.emit(f'当前任务：{job.local_name}')
                self.task_status.emit(job.local_name, 'uploading', '', 0)
                try:
                    result = executor.execute_job(job, cancel_token=self.cancel_token, progress_callback=self._emit_progress_action)
                except TypeError:
                    result = executor.execute_job(job, cancel_token=self.cancel_token)
                self.task_status.emit(job.local_name, getattr(result, 'status', 'completed'), getattr(result, 'share_url', ''), getattr(result, 'retry_count', 0))
                state = getattr(result, 'status', 'completed')
                if state == 'failed':
                    failed += 1
                elif state == 'stopped':
                    final_state = 'stopped'
                    for pending_job in self.plan.jobs[index + 1:]:
                        self.task_status.emit(pending_job.local_name, 'stopped', '', 0)
                    break
                else:
                    completed += 1
                self.progress_summary.emit(completed, total, failed)
        except Exception as exc:
            final_state = 'failed'
            self.log_message.emit(f'[ERROR] 后台上传线程异常：{exc}')
        self.current_action.emit('当前动作：空闲' if final_state == 'completed' else ('当前动作：已停止' if final_state == 'stopped' else '当前动作：失败'))
        self.run_finished.emit(final_state)


class UploadWorkerHandle:
    def __init__(self, worker: UploadWorker) -> None:
        self.worker = worker
        self.thread: QThread | None = None

    def start(self) -> None:
        if self.thread is not None and self.thread.isRunning():
            return
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.run_finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._on_thread_finished)
        self.thread.start()

    def _on_thread_finished(self) -> None:
        self.thread = None

    def request_stop(self) -> None:
        self.worker.cancel_token.request_stop()

    def is_running(self) -> bool:
        if self.thread is None:
            return False
        try:
            return self.thread.isRunning()
        except RuntimeError:
            return False
