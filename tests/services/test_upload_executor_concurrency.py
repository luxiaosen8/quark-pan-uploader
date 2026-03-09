from __future__ import annotations

from threading import Lock, Thread
from time import sleep

from quark_uploader.models import FolderTaskStatus, TaskSourceType
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.upload_executor import UploadExecutionEngine
from quark_uploader.services.upload_workflow import UploadJob


class FakeDirectorySyncService:
    def ensure_job_directories(self, job: UploadJob) -> ResolvedRemoteDirectory:
        return ResolvedRemoteDirectory(root_folder_fid="root", relative_dir_fids={})


class FakeConcurrentUploader:
    def upload_file(self, entry, parent_fid, cancel_token=None, progress_callback=None):
        sleep(0.02)
        return {"finish": {"data": {"fid": f"fid-{entry.relative_path}"}}}


class FakeShareService:
    def create_share_for_item(self, fid: str, title: str, cancel_token=None):
        return type(
            "ShareResult",
            (),
            {"share_id": f"share-{fid}", "share_url": f"https://share/{title}"},
        )()


class ThreadSafeResultWriter:
    def __init__(self) -> None:
        self.run_id = "run-concurrent"
        self._lock = Lock()
        self.events: list[dict] = []
        self.share_results: list[dict] = []

    def append_event(self, level: str, phase: str, message: str, **extra) -> None:
        with self._lock:
            self.events.append(
                {"level": level, "phase": phase, "message": message, **extra}
            )

    def append_share_result(self, record: dict) -> None:
        with self._lock:
            self.share_results.append(record)


def _build_job(name: str) -> UploadJob:
    return UploadJob(
        local_name=name,
        local_path=name,
        file_count=1,
        total_size=1,
        remote_parent_fid="root",
        source_type=TaskSourceType.FILE,
        file_entries=[
            LocalFileEntry(
                local_name=name,
                absolute_path=name,
                relative_path=f"{name}.txt",
                size_bytes=1,
            )
        ],
    )


def test_execute_job_keeps_results_isolated_under_parallel_calls() -> None:
    result_writer = ThreadSafeResultWriter()
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=FakeConcurrentUploader(),
        share_service=FakeShareService(),
        result_writer=result_writer,
        file_retry_limit=0,
        share_retry_limit=0,
        retry_backoff_base_seconds=0,
    )
    results = []

    threads = [
        Thread(
            target=lambda job=_build_job(name): results.append(engine.execute_job(job)),
            daemon=True,
        )
        for name in ("job-a", "job-b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 2
    assert {result.status for result in results} == {FolderTaskStatus.COMPLETED.value}
    assert {record["local_folder_name"] for record in result_writer.share_results} == {
        "job-a",
        "job-b",
    }
