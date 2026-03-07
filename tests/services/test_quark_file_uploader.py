from pathlib import Path

from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.quark_file_uploader import QuarkFileUploader


class FakeUploadApi:
    def __init__(self):
        self.calls = []

    def preupload(self, payload):
        self.calls.append(("preupload", payload))
        return {
            "data": {
                "task_id": "task-1",
                "auth_info": "auth-info",
                "obj_key": "obj-key",
                "upload_id": "upload-1",
                "bucket": "ul-zb",
            }
        }

    def update_hash(self, payload):
        self.calls.append(("update_hash", payload))
        return {"data": {"ok": True}}

    def get_upload_auth(self, payload):
        self.calls.append(("get_upload_auth", payload))
        return {"data": {"auth_key": "AUTH"}}

    def finish(self, payload):
        self.calls.append(("finish", payload))
        return {"data": {"fid": "file-fid"}}


class FakeOssTransport:
    def __init__(self):
        self.calls = []

    def upload_single_part(self, file_path, upload_url: str, headers: dict):
        self.calls.append((str(file_path), upload_url, headers.get("authorization")))
        return {"etag": "etag-1"}


def test_quark_file_uploader_executes_single_part_upload_flow(tmp_path: Path):
    file_path = tmp_path / "cover.txt"
    file_path.write_text("12", encoding="utf-8")
    upload_api = FakeUploadApi()
    oss_transport = FakeOssTransport()
    uploader = QuarkFileUploader(upload_api=upload_api, oss_transport=oss_transport)
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="cover.txt", size_bytes=2)

    result = uploader.upload_file(entry, target_parent_fid="root-fid")

    assert [name for name, _ in upload_api.calls] == ["preupload", "update_hash", "get_upload_auth", "finish"]
    assert oss_transport.calls[0][1] == "https://ul-zb.pds.quark.cn/obj-key?partNumber=1&uploadId=upload-1"
    assert oss_transport.calls[0][2] == "AUTH"
    assert result["task_id"] == "task-1"
    assert result["finish"]["data"]["fid"] == "file-fid"



def test_quark_file_uploader_rejects_large_file_for_single_part_mode(tmp_path: Path):
    file_path = tmp_path / "large.bin"
    file_path.write_bytes(b"0" * (5 * 1024 * 1024 + 1))
    upload_api = FakeUploadApi()
    oss_transport = FakeOssTransport()
    uploader = QuarkFileUploader(upload_api=upload_api, oss_transport=oss_transport)
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="large.bin", size_bytes=file_path.stat().st_size)

    try:
        uploader.upload_file(entry, target_parent_fid="root-fid")
        raised = False
    except NotImplementedError:
        raised = True

    assert raised is True
    assert upload_api.calls == []
    assert oss_transport.calls == []
