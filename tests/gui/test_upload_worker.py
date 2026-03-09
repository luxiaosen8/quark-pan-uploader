from __future__ import annotations

from types import SimpleNamespace

from quark_uploader.models import FolderTaskStatus, TaskSourceType
from quark_uploader.services.cancellation import UploadCancellationToken
from quark_uploader.services.upload_workflow import UploadExecutionPlan, UploadJob
from quark_uploader.gui.workers import UploadWorker


def _build_plan(names: list[str]) -> UploadExecutionPlan:
    return UploadExecutionPlan(
        remote_parent_fid="root",
        jobs=[
            UploadJob(
                local_name=name,
                local_path=name,
                file_count=1,
                total_size=1,
                remote_parent_fid="root",
                source_type=TaskSourceType.FILE,
            )
            for name in names
        ],
    )


def test_upload_worker_runs_jobs_serially_when_concurrency_is_one() -> None:
    order: list[str] = []

    class FakeExecutor:
        def execute_job(self, job, **kwargs):
            order.append(job.local_name)
            return SimpleNamespace(
                status=FolderTaskStatus.COMPLETED.value, share_url="", retry_count=0
            )

    worker = UploadWorker(
        plan=_build_plan(["job-a", "job-b", "job-c"]),
        executor_factory=lambda **kwargs: FakeExecutor(),
        cancel_token=UploadCancellationToken(),
        job_concurrency=1,
    )

    worker.run()

    assert order == ["job-a", "job-b", "job-c"]


def test_upload_worker_marks_remaining_jobs_stopped_after_stop_request() -> None:
    stopped: list[tuple[str, str]] = []
    cancel_token = UploadCancellationToken()

    class FakeExecutor:
        def execute_job(self, job, **kwargs):
            cancel_token.request_stop()
            return SimpleNamespace(
                status=FolderTaskStatus.STOPPED.value, share_url="", retry_count=0
            )

    worker = UploadWorker(
        plan=_build_plan(["job-a", "job-b", "job-c"]),
        executor_factory=lambda **kwargs: FakeExecutor(),
        cancel_token=cancel_token,
        job_concurrency=1,
    )
    worker.task_status.connect(
        lambda local_name, status, share_url, retry_count: stopped.append(
            (local_name, status)
        )
    )

    worker.run()

    assert ("job-b", FolderTaskStatus.STOPPED.value) in stopped
    assert ("job-c", FolderTaskStatus.STOPPED.value) in stopped
