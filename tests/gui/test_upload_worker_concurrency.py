from __future__ import annotations

from threading import Event, Lock
from time import monotonic, sleep
from types import SimpleNamespace

from quark_uploader.gui.workers import UploadWorker
from quark_uploader.models import FolderTaskStatus, TaskSourceType
from quark_uploader.services.cancellation import UploadCancellationToken
from quark_uploader.services.upload_workflow import UploadExecutionPlan, UploadJob


def test_upload_worker_starts_multiple_jobs_concurrently() -> None:
    started_at: list[float] = []
    started_lock = Lock()
    all_started = Event()
    plan = UploadExecutionPlan(
        remote_parent_fid="root",
        jobs=[
            UploadJob(
                local_name="job-a",
                local_path="a",
                file_count=1,
                total_size=1,
                remote_parent_fid="root",
                source_type=TaskSourceType.FILE,
            ),
            UploadJob(
                local_name="job-b",
                local_path="b",
                file_count=1,
                total_size=1,
                remote_parent_fid="root",
                source_type=TaskSourceType.FILE,
            ),
        ],
    )

    class FakeExecutor:
        def execute_job(self, job, **kwargs):
            with started_lock:
                started_at.append(monotonic())
                if len(started_at) == 2:
                    all_started.set()
            all_started.wait(1)
            sleep(0.05)
            return SimpleNamespace(
                status=FolderTaskStatus.COMPLETED.value, share_url="", retry_count=0
            )

    worker = UploadWorker(
        plan=plan,
        executor_factory=lambda **kwargs: FakeExecutor(),
        cancel_token=UploadCancellationToken(),
        job_concurrency=2,
    )

    worker.run()

    assert len(started_at) == 2
    assert max(started_at) - min(started_at) < 0.05
