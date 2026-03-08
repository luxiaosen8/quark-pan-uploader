from pathlib import Path
import csv
import json

from quark_uploader.models import TaskSourceType
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.remote_folder_plan import RemoteFolderRequirement
from quark_uploader.services.result_writer import ResultWriter
from quark_uploader.services.upload_executor import UploadExecutionEngine
from quark_uploader.services.upload_workflow import UploadJob


class FakeDirectorySyncService:
    def ensure_job_directories(self, job: UploadJob):
        return ResolvedRemoteDirectory(
            root_folder_fid="root-fid",
            relative_dir_fids={"chapter1": "chapter1-fid"},
        )


class FakeUploader:
    def __init__(self):
        self.calls = []

    def upload_file(self, file_entry, target_parent_fid: str):
        self.calls.append((file_entry.relative_path, target_parent_fid))
        return {"ok": True, "target_parent_fid": target_parent_fid}


class FlakyUploader:
    def __init__(self):
        self.calls = 0

    def upload_file(self, file_entry, target_parent_fid: str):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary upload error")
        return {"ok": True}


class AlwaysFailUploader:
    def __init__(self):
        self.calls = 0

    def upload_file(self, file_entry, target_parent_fid: str):
        self.calls += 1
        raise RuntimeError("permanent upload error")


class FakeShareService:
    def __init__(self):
        self.calls = []

    def create_share_for_folder(self, fid: str, title: str):
        self.calls.append((fid, title))
        return type("ShareResult", (), {"share_id": "share-1", "share_url": "https://pan.quark.cn/s/abc123"})()


class FlakyShareService(FakeShareService):
    def __init__(self):
        super().__init__()
        self.attempts = 0

    def create_share_for_folder(self, fid: str, title: str):
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("temporary share error")
        return super().create_share_for_folder(fid, title)


def build_job():
    return UploadJob(
        local_name="课程A",
        local_path="C:/课程A",
        remote_parent_fid="remote-root",
        file_entries=[
            LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/chapter1/video.mp4", relative_path="chapter1/video.mp4", size_bytes=10),
            LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/cover.txt", relative_path="cover.txt", size_bytes=5),
        ],
        remote_dir_requirements=[
            RemoteFolderRequirement(local_name="课程A", relative_dir="chapter1", remote_parent_fid="remote-root"),
        ],
    )


def test_upload_execution_engine_maps_files_to_correct_remote_parent():
    uploader = FakeUploader()
    engine = UploadExecutionEngine(directory_sync_service=FakeDirectorySyncService(), uploader=uploader)

    result = engine.execute_job(build_job())

    assert uploader.calls == [("chapter1/video.mp4", "chapter1-fid"), ("cover.txt", "root-fid")]
    assert result.uploaded_files == 2
    assert result.root_folder_fid == "root-fid"
    assert result.retry_count == 0


def test_upload_execution_engine_retries_file_upload_once_then_succeeds():
    uploader = FlakyUploader()
    logs = []
    engine = UploadExecutionEngine(directory_sync_service=FakeDirectorySyncService(), uploader=uploader, logger=logs.append)

    result = engine.execute_job(build_job())

    assert uploader.calls == 3
    assert result.retry_count == 1
    assert any("重试上传文件" in item for item in logs)


def test_upload_execution_engine_records_failure_result(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-1")
    uploader = AlwaysFailUploader()
    engine = UploadExecutionEngine(directory_sync_service=FakeDirectorySyncService(), uploader=uploader, result_writer=writer)

    try:
        engine.execute_job(build_job())
        raised = False
    except RuntimeError:
        raised = True

    assert raised is True
    rows = (tmp_path / "runs" / "run-1" / "share_results.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    assert payload["status"] == "failed"
    assert payload["error_message"] == "permanent upload error"
    assert payload["retry_count"] >= 1


def test_upload_execution_engine_can_retry_share_after_upload():
    uploader = FakeUploader()
    share_service = FlakyShareService()
    logs = []
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        share_service=share_service,
        logger=logs.append,
    )

    result = engine.execute_job(build_job())

    assert share_service.attempts == 2
    assert result.share_url == "https://pan.quark.cn/s/abc123"
    assert result.retry_count == 1
    assert any("重试创建分享" in item for item in logs)



def test_upload_execution_engine_writes_normal_flow_events(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-2")
    uploader = FakeUploader()
    share_service = FakeShareService()
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        share_service=share_service,
        result_writer=writer,
    )

    engine.execute_job(build_job())

    rows = (tmp_path / "runs" / "run-2" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert any('job start' in row for row in rows)
    assert any('job completed' in row for row in rows)



def test_upload_execution_engine_returns_stopped_when_cancel_requested_before_start():
    from quark_uploader.services.cancellation import UploadCancellationToken
    uploader = FakeUploader()
    token = UploadCancellationToken()
    token.request_stop()
    engine = UploadExecutionEngine(directory_sync_service=FakeDirectorySyncService(), uploader=uploader)

    result = engine.execute_job(build_job(), cancel_token=token)

    assert result.status == "stopped"
    assert result.uploaded_files == 0


def test_upload_execution_engine_returns_stopped_when_uploader_raises_cancelled():
    from quark_uploader.services.cancellation import UploadCancelled, UploadCancellationToken

    class CancelUploader:
        def upload_file(self, file_entry, target_parent_fid: str, cancel_token=None, progress_callback=None):
            raise UploadCancelled("stopped by user")

    token = UploadCancellationToken()
    engine = UploadExecutionEngine(directory_sync_service=FakeDirectorySyncService(), uploader=CancelUploader())

    result = engine.execute_job(build_job(), cancel_token=token)

    assert result.status == "stopped"
    assert result.error_message == "stopped by user"



def test_upload_execution_engine_emits_retrying_and_sharing_statuses():
    uploader = FlakyUploader()
    share_service = FakeShareService()
    statuses = []
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        share_service=share_service,
    )

    engine.execute_job(build_job(), status_callback=lambda status, share_url="", retry_count=0: statuses.append((status, retry_count)))

    assert ("retrying", 1) in statuses
    assert any(status == "sharing" for status, _ in statuses)


def test_upload_execution_engine_uses_backoff_before_retry():
    uploader = FlakyUploader()
    delays = []
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        retry_backoff_base_seconds=0.25,
        sleep_fn=delays.append,
    )

    engine.execute_job(build_job())

    assert delays == [0.25]



class SingleFileUploader:
    def __init__(self):
        self.calls = []

    def upload_file(self, file_entry, target_parent_fid: str, cancel_token=None, progress_callback=None):
        self.calls.append((file_entry.relative_path, target_parent_fid))
        return {"finish": {"data": {"fid": "file-fid-1"}}}


class RecordingShareService:
    def __init__(self):
        self.calls = []

    def create_share_for_item(self, fid: str, title: str, cancel_token=None):
        self.calls.append((fid, title))
        return type("ShareResult", (), {"share_id": "share-file-1", "share_url": "https://pan.quark.cn/s/file123"})()


def build_file_job():
    return UploadJob(
        local_name="cover.txt",
        local_path="C:/cover.txt",
        file_count=1,
        total_size=5,
        remote_parent_fid="remote-root",
        source_type=TaskSourceType.FILE,
        file_entries=[LocalFileEntry(local_name="cover.txt", absolute_path="C:/cover.txt", relative_path="cover.txt", size_bytes=5)],
        remote_dir_requirements=[],
    )


def test_upload_execution_engine_supports_single_file_task_and_shares_file(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-file")
    uploader = SingleFileUploader()
    share_service = RecordingShareService()
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        share_service=share_service,
        result_writer=writer,
    )

    result = engine.execute_job(build_file_job())

    assert uploader.calls == [("cover.txt", "remote-root")]
    assert share_service.calls == [("file-fid-1", "cover.txt")]
    assert result.share_url == "https://pan.quark.cn/s/file123"
    rows = (tmp_path / "runs" / "run-file" / "share_results.jsonl").read_text(encoding="utf-8").splitlines()
    assert any('"remote_item_type": "file"' in row for row in rows)
