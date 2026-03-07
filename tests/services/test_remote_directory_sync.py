from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_directory_sync import RemoteDirectorySyncService
from quark_uploader.services.remote_folder_plan import RemoteFolderRequirement
from quark_uploader.services.upload_workflow import UploadJob


class FakeFileApi:
    def __init__(self):
        self.tree = {
            "remote-root": [{"fid": "existing-root", "file_name": "课程A", "dir": True}],
            "existing-root": [{"fid": "existing-ch1", "file_name": "chapter1", "dir": True}],
            "existing-ch1": [],
        }
        self.created = []

    def list_directory(self, parent_fid: str):
        return {"data": {"list": self.tree.get(parent_fid, [])}}

    def create_directory(self, parent_fid: str, name: str):
        fid = f"created-{len(self.created)+1}"
        self.created.append((parent_fid, name, fid))
        self.tree.setdefault(parent_fid, []).append({"fid": fid, "file_name": name, "dir": True})
        self.tree.setdefault(fid, [])
        return {"data": {"fid": fid}}


def test_remote_directory_sync_reuses_existing_and_creates_missing_nested_dirs():
    service = RemoteDirectorySyncService(FakeFileApi())
    job = UploadJob(
        local_name="课程A",
        local_path="C:/课程A",
        remote_parent_fid="remote-root",
        file_entries=[
            LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/chapter1/video.mp4", relative_path="chapter1/video.mp4", size_bytes=10),
            LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/chapter1/docs/readme.txt", relative_path="chapter1/docs/readme.txt", size_bytes=5),
        ],
        remote_dir_requirements=[
            RemoteFolderRequirement(local_name="课程A", relative_dir="chapter1", remote_parent_fid="remote-root"),
            RemoteFolderRequirement(local_name="课程A", relative_dir="chapter1/docs", remote_parent_fid="remote-root"),
        ],
    )

    resolved = service.ensure_job_directories(job)

    assert resolved.root_folder_fid == "existing-root"
    assert resolved.relative_dir_fids["chapter1"] == "existing-ch1"
    assert resolved.relative_dir_fids["chapter1/docs"].startswith("created-")
