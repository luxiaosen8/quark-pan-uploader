from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot

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

    @Slot()
    def run(self) -> None:
        executor = self._build_executor()
        total = len(self.plan.jobs)
        completed = 0
        failed = 0
        final_state = 'completed'
        for index, job in enumerate(self.plan.jobs):
            if self.cancel_token.is_cancelled():
                for pending_job in self.plan.jobs[index:]:
                    self.task_status.emit(pending_job.local_name, 'stopped', '', 0)
                final_state = 'stopped'
                break
            self.current_action.emit(f'当前任务：{job.local_name}')
            self.task_status.emit(job.local_name, 'uploading', '', 0)
            result = executor.execute_job(job, cancel_token=self.cancel_token)
            self.task_status.emit(job.local_name, getattr(result, 'status', 'completed'), getattr(result, 'share_url', ''), getattr(result, 'retry_count', 0))
            if getattr(result, 'status', 'completed') == 'failed':
                failed += 1
            elif getattr(result, 'status', 'completed') == 'stopped':
                final_state = 'stopped'
                for pending_job in self.plan.jobs[index + 1:]:
                    self.task_status.emit(pending_job.local_name, 'stopped', '', 0)
                break
            else:
                completed += 1
            self.progress_summary.emit(completed, total, failed)
        self.current_action.emit('当前动作：空闲' if final_state == 'completed' else '当前动作：已停止')
        self.run_finished.emit(final_state)


class UploadWorkerHandle:
    def __init__(self, worker: UploadWorker) -> None:
        self.worker = worker
        self._started = False

    def start(self) -> None:
        self._started = True
        self.worker.run()

    def request_stop(self) -> None:
        self.worker.cancel_token.request_stop()

    def is_running(self) -> bool:
        return self._started and not self.worker.cancel_token.is_cancelled()
