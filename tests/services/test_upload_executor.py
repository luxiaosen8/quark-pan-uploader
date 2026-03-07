from pathlib import Path

from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.remote_folder_plan import RemoteFolderRequirement
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


class FakeShareService:
    def __init__(self):
        self.calls = []

    def create_share_for_folder(self, fid: str, title: str):
        self.calls.append((fid, title))
        return type("ShareResult", (), {"share_id": "share-1", "share_url": "https://pan.quark.cn/s/abc123"})()


def test_upload_execution_engine_maps_files_to_correct_remote_parent():
    uploader = FakeUploader()
    engine = UploadExecutionEngine(directory_sync_service=FakeDirectorySyncService(), uploader=uploader)
    job = UploadJob(
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

    result = engine.execute_job(job)

    assert uploader.calls == [("chapter1/video.mp4", "chapter1-fid"), ("cover.txt", "root-fid")]
    assert result.uploaded_files == 2
    assert result.root_folder_fid == "root-fid"


def test_upload_execution_engine_can_create_share_after_upload():
    uploader = FakeUploader()
    share_service = FakeShareService()
    engine = UploadExecutionEngine(
        directory_sync_service=FakeDirectorySyncService(),
        uploader=uploader,
        share_service=share_service,
    )
    job = UploadJob(
        local_name="课程A",
        local_path="C:/课程A",
        remote_parent_fid="remote-root",
        file_entries=[
            LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/cover.txt", relative_path="cover.txt", size_bytes=5),
        ],
        remote_dir_requirements=[],
    )

    result = engine.execute_job(job)

    assert share_service.calls == [("root-fid", "课程A")]
    assert result.share_url == "https://pan.quark.cn/s/abc123"
