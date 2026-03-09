from __future__ import annotations

from quark_uploader.models import FolderTaskStatus, TaskSourceType
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.upload_executor import UploadExecutionEngine
from quark_uploader.services.upload_workflow import UploadJob


class FakeDirectorySyncService:
    def ensure_job_directories(self, job: UploadJob) -> ResolvedRemoteDirectory:
        return ResolvedRemoteDirectory(root_folder_fid="root", relative_dir_fids={})


class FakeUploader:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.attempts: dict[str, int] = {}

    def upload_file(self, entry, parent_fid, cancel_token=None, progress_callback=None):
        self.calls.append(entry.relative_path)
        self.attempts[entry.relative_path] = (
            self.attempts.get(entry.relative_path, 0) + 1
        )
        if entry.relative_path == "b.txt" and self.attempts[entry.relative_path] == 1:
            raise RuntimeError("retry me")
        return {"finish": {"data": {"fid": f"fid-{entry.relative_path}"}}}


class FakeShareService:
    def create_share_for_item(self, fid: str, title: str, cancel_token=None):
        return type(
            "ShareResult",
            (),
            {"share_id": f"share-{fid}", "share_url": f"https://share/{title}"},
        )()


class FakeResultWriter:
    def __init__(self) -> None:
        self.run_id = "run-1"
        self.events: list[tuple[str, str, str, dict]] = []
        self.share_results: list[dict] = []

    def append_event(self, level: str, phase: str, message: str, **extra) -> None:
        self.events.append((level, phase, message, extra))

    def append_share_result(self, record: dict) -> None:
        self.share_results.append(record)


def test_execute_job_retries_failed_file_and_keeps_share_flow() -> None:
    uploader = FakeUploader()
    result_writer = FakeResultWriter()
    statuses: list[str] = []
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        share_service=FakeShareService(),
        result_writer=result_writer,
        file_retry_limit=1,
        share_retry_limit=0,
        retry_backoff_base_seconds=0,
    )
    job = UploadJob(
        local_name="demo-job",
        local_path="demo-job",
        file_count=2,
        total_size=2,
        remote_parent_fid="root",
        source_type=TaskSourceType.FILE,
        file_entries=[
            LocalFileEntry(
                local_name="demo-job",
                absolute_path="a",
                relative_path="a.txt",
                size_bytes=1,
            ),
            LocalFileEntry(
                local_name="demo-job",
                absolute_path="b",
                relative_path="b.txt",
                size_bytes=1,
            ),
        ],
    )

    result = engine.execute_job(
        job, status_callback=lambda status, **_: statuses.append(status)
    )

    assert uploader.calls == ["a.txt", "b.txt", "b.txt"]
    assert result.status == FolderTaskStatus.COMPLETED.value
    assert result.retry_count == 1
    assert result.share_url == "https://share/demo-job"
    assert FolderTaskStatus.RETRYING.value in statuses
    assert FolderTaskStatus.SHARING.value in statuses
    assert result_writer.share_results[0]["local_folder_name"] == "demo-job"
