from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from PySide6.QtCore import QObject, QThread, Signal, Slot

from quark_uploader.models import FolderTaskStatus
from quark_uploader.services.cancellation import UploadCancellationToken
from quark_uploader.services.invoke import call_with_supported_kwargs


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

    def __init__(
        self,
        plan,
        executor_factory,
        cancel_token: UploadCancellationToken,
        job_concurrency: int = 1,
        ui_update_interval_ms: int = 120,
        shared_result_writer=None,
    ) -> None:
        super().__init__()
        self.plan = plan
        self.executor_factory = executor_factory
        self.cancel_token = cancel_token
        self.job_concurrency = max(1, int(job_concurrency))
        self.ui_update_interval_seconds = max(0.05, ui_update_interval_ms / 1000)
        self.shared_result_writer = shared_result_writer
        self._pending_current_action: str | None = None
        self._pending_logs: list[str] = []
        self._last_action_emit = 0.0
        self._last_log_emit = 0.0
        self._buffer_lock = Lock()

    def _build_executor(self):
        return call_with_supported_kwargs(
            self.executor_factory,
            logger_callback=self._buffer_log_message,
            result_writer=self.shared_result_writer,
        )

    def _flush_current_action(self, force: bool = False) -> None:
        text: str | None = None
        with self._buffer_lock:
            if self._pending_current_action is None:
                return
            now = monotonic()
            if (
                not force
                and now - self._last_action_emit < self.ui_update_interval_seconds
            ):
                return
            text = self._pending_current_action
            self._pending_current_action = None
            self._last_action_emit = now
        if text is not None:
            self.current_action.emit(text)

    def _buffer_log_message(self, message: str) -> None:
        with self._buffer_lock:
            self._pending_logs.append(message)
        self._flush_logs()

    def _flush_logs(self, force: bool = False) -> None:
        buffered: list[str] = []
        with self._buffer_lock:
            if not self._pending_logs:
                return
            now = monotonic()
            if (
                not force
                and len(self._pending_logs) < 8
                and now - self._last_log_emit < self.ui_update_interval_seconds
            ):
                return
            buffered = self._pending_logs[:]
            self._pending_logs.clear()
            self._last_log_emit = now
        if len(buffered) == 1:
            self.log_message.emit(buffered[0])
        else:
            self.log_message.emit("\n".join(buffered))

    def _emit_progress_action(self, payload: dict) -> None:
        file_name = payload.get("file_name", "")
        phase = payload.get("phase", "")
        part_number = payload.get("part_number", 0)
        part_total = payload.get("part_total", 0)
        with self._buffer_lock:
            if part_total:
                self._pending_current_action = f"当前文件：{file_name} | 阶段：{phase} | 分片 {part_number}/{part_total}"
            else:
                self._pending_current_action = f"当前文件：{file_name} | 阶段：{phase}"
        self._flush_current_action()

    def _run_single_job(self, job):
        executor = self._build_executor()
        with self._buffer_lock:
            self._pending_current_action = f"当前任务：{job.local_name}"
        self._flush_current_action(force=True)
        self.task_status.emit(job.local_name, FolderTaskStatus.UPLOADING.value, "", 0)
        status_callback = (
            lambda status,
            share_url="",
            retry_count=0,
            local_name=job.local_name: self.task_status.emit(
                local_name,
                status,
                share_url,
                retry_count,
            )
        )
        return call_with_supported_kwargs(
            executor.execute_job,
            job,
            cancel_token=self.cancel_token,
            progress_callback=self._emit_progress_action,
            status_callback=status_callback,
        )

    @Slot()
    def run(self) -> None:
        total = len(self.plan.jobs)
        completed = 0
        failed = 0
        final_state = "completed"
        try:
            next_index = 0
            pending: dict[Future, object] = {}
            with ThreadPoolExecutor(
                max_workers=self.job_concurrency, thread_name_prefix="upload-job"
            ) as pool:
                while (
                    next_index < total
                    and len(pending) < self.job_concurrency
                    and not self.cancel_token.is_cancelled()
                ):
                    job = self.plan.jobs[next_index]
                    pending[pool.submit(self._run_single_job, job)] = job
                    next_index += 1

                while pending:
                    done, _ = wait(
                        tuple(pending.keys()),
                        return_when=FIRST_COMPLETED,
                        timeout=self.ui_update_interval_seconds,
                    )
                    if not done:
                        if self.cancel_token.is_cancelled():
                            final_state = "stopped"
                        self._flush_logs()
                        self._flush_current_action()
                        continue
                    for future in done:
                        job = pending.pop(future)
                        try:
                            result = future.result()
                        except Exception as exc:
                            failed += 1
                            self.task_status.emit(
                                job.local_name, FolderTaskStatus.FAILED.value, "", 0
                            )
                            self._buffer_log_message(
                                f"[ERROR] 后台任务失败：{job.local_name} -> {exc}"
                            )
                            self.progress_summary.emit(completed, total, failed)
                            final_state = "completed_with_errors"
                            continue

                        state = getattr(
                            result, "status", FolderTaskStatus.COMPLETED.value
                        )
                        self.task_status.emit(
                            job.local_name,
                            state,
                            getattr(result, "share_url", ""),
                            getattr(result, "retry_count", 0),
                        )
                        if state == FolderTaskStatus.FAILED.value:
                            failed += 1
                            final_state = "completed_with_errors"
                        elif state == FolderTaskStatus.STOPPED.value:
                            final_state = "stopped"
                        else:
                            completed += 1
                        self.progress_summary.emit(completed, total, failed)

                    while (
                        next_index < total
                        and len(pending) < self.job_concurrency
                        and not self.cancel_token.is_cancelled()
                    ):
                        job = self.plan.jobs[next_index]
                        pending[pool.submit(self._run_single_job, job)] = job
                        next_index += 1

                if self.cancel_token.is_cancelled():
                    for pending_job in self.plan.jobs[next_index:]:
                        self.task_status.emit(
                            pending_job.local_name,
                            FolderTaskStatus.STOPPED.value,
                            "",
                            0,
                        )
                    final_state = "stopped"

            if final_state == "completed" and failed:
                final_state = "completed_with_errors"
        except Exception as exc:
            final_state = "failed"
            self._buffer_log_message(f"[ERROR] 后台上传线程异常：{exc}")
        self._flush_logs(force=True)
        with self._buffer_lock:
            self._pending_current_action = (
                "当前动作：空闲"
                if final_state in {"completed", "completed_with_errors"}
                else (
                    "当前动作：已停止" if final_state == "stopped" else "当前动作：失败"
                )
            )
        self._flush_current_action(force=True)
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
