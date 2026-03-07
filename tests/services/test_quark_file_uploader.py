from pathlib import Path

from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.quark_file_uploader import QuarkFileUploader


class FakeUploadApi:
    def __init__(self):
        self.calls = []

    def preupload(self, payload):
        self.calls.append(("preupload", payload))
        return {"data": {"task_id": "task-1", "auth_info": "auth", "obj_key": "obj-key"}}

    def update_hash(self, payload):
        self.calls.append(("update_hash", payload))
        return {"data": {"ok": True}}

    def finish(self, payload):
        self.calls.append(("finish", payload))
        return {"data": {"fid": "file-fid"}}


def test_quark_file_uploader_executes_metadata_upload_flow(tmp_path: Path):
    file_path = tmp_path / "cover.txt"
    file_path.write_text("12", encoding="utf-8")
    uploader = QuarkFileUploader(upload_api=FakeUploadApi())
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="cover.txt", size_bytes=2)

    result = uploader.upload_file(entry, target_parent_fid="root-fid")

    assert [name for name, _ in uploader.upload_api.calls] == ["preupload", "update_hash", "finish"]
    assert result["task_id"] == "task-1"
    assert result["finish"]["data"]["fid"] == "file-fid"
