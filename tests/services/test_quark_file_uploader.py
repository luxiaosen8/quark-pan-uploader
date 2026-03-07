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
                "callback": {"callbackUrl": "https://example.com/callback", "callbackBody": "x"},
            }
        }

    def update_hash(self, payload):
        self.calls.append(("update_hash", payload))
        return {"data": {"ok": True}}

    def get_upload_auth(self, payload):
        auth_meta = payload["auth_meta"]
        phase = "get_upload_auth_complete" if auth_meta.startswith("POST") else "get_upload_auth"
        self.calls.append((phase, payload))
        return {"data": {"auth_key": "AUTH"}}

    def finish(self, payload):
        self.calls.append(("finish", payload))
        return {"data": {"fid": "file-fid"}}


class FakeOssTransport:
    def __init__(self):
        self.put_calls = []
        self.post_calls = []

    def upload_single_part(self, file_path, upload_url: str, headers: dict):
        self.put_calls.append((str(file_path), upload_url, headers.get("authorization"), headers.get("X-Oss-Hash-Ctx")))
        return {"etag": "etag-1"}

    def upload_part(self, file_path, upload_url: str, headers: dict, offset: int, size: int):
        self.put_calls.append((str(file_path), upload_url, headers.get("authorization"), headers.get("X-Oss-Hash-Ctx"), offset, size))
        return {"etag": f"etag-{len(self.put_calls)}"}

    def complete_multipart_upload(self, upload_url: str, headers: dict, xml_data: str):
        self.post_calls.append((upload_url, headers.get("authorization"), xml_data))
        return {"ok": True}


def test_quark_file_uploader_executes_single_part_upload_flow(tmp_path: Path):
    file_path = tmp_path / "cover.txt"
    file_path.write_text("12", encoding="utf-8")
    upload_api = FakeUploadApi()
    oss_transport = FakeOssTransport()
    uploader = QuarkFileUploader(upload_api=upload_api, oss_transport=oss_transport)
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="cover.txt", size_bytes=2)

    result = uploader.upload_file(entry, target_parent_fid="root-fid")

    assert [name for name, _ in upload_api.calls] == ["preupload", "update_hash", "get_upload_auth", "get_upload_auth_complete", "finish"]
    assert oss_transport.put_calls[0][1] == "https://ul-zb.pds.quark.cn/obj-key?partNumber=1&uploadId=upload-1"
    assert oss_transport.put_calls[0][2] == "AUTH"
    assert len(oss_transport.post_calls) == 1
    assert result["multipart_complete"] == {"ok": True}
    assert result["task_id"] == "task-1"
    assert result["finish"]["data"]["fid"] == "file-fid"


def test_quark_file_uploader_executes_multipart_upload_flow(tmp_path: Path):
    file_path = tmp_path / "large.bin"
    file_path.write_bytes(b"0" * (5 * 1024 * 1024 + 1))
    upload_api = FakeUploadApi()
    oss_transport = FakeOssTransport()
    uploader = QuarkFileUploader(upload_api=upload_api, oss_transport=oss_transport)
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="large.bin", size_bytes=file_path.stat().st_size)

    result = uploader.upload_file(entry, target_parent_fid="root-fid")

    assert [name for name, _ in upload_api.calls] == [
        "preupload",
        "update_hash",
        "get_upload_auth",
        "get_upload_auth",
        "get_upload_auth_complete",
        "finish",
    ]
    assert len(oss_transport.put_calls) == 2
    assert oss_transport.put_calls[0][4:] == (0, 4 * 1024 * 1024)
    assert oss_transport.put_calls[1][4:] == (4 * 1024 * 1024, 1024 * 1024 + 1)
    assert oss_transport.put_calls[1][3] is not None
    assert "x-oss-hash-ctx:" in upload_api.calls[3][1]["auth_meta"]
    assert len(oss_transport.post_calls) == 1
    assert result["multipart_complete"] == {"ok": True}



def test_quark_file_uploader_emits_debug_logs_for_single_part_flow(tmp_path: Path):
    file_path = tmp_path / "cover.txt"
    file_path.write_text("12", encoding="utf-8")
    upload_api = FakeUploadApi()
    oss_transport = FakeOssTransport()
    logs = []
    uploader = QuarkFileUploader(upload_api=upload_api, oss_transport=oss_transport, logger=logs.append)
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="cover.txt", size_bytes=2)

    uploader.upload_file(entry, target_parent_fid="root-fid")

    assert any("文件上传开始" in line for line in logs)
    assert any("预上传成功" in line for line in logs)
    assert any("单分片上传完成" in line for line in logs)
    assert any("finish 完成" in line for line in logs)



def test_quark_file_uploader_emits_progress_events_for_multipart_flow(tmp_path: Path):
    file_path = tmp_path / "large.bin"
    file_path.write_bytes(b"0" * (5 * 1024 * 1024 + 1))
    upload_api = FakeUploadApi()
    oss_transport = FakeOssTransport()
    events = []
    uploader = QuarkFileUploader(upload_api=upload_api, oss_transport=oss_transport)
    entry = LocalFileEntry(local_name="课程A", absolute_path=str(file_path), relative_path="large.bin", size_bytes=file_path.stat().st_size)

    uploader.upload_file(entry, target_parent_fid="root-fid", progress_callback=events.append)

    assert any(evt.get("phase") == "preupload" for evt in events)
    assert any(evt.get("phase") == "part_upload" and evt.get("part_number") == 1 for evt in events)
    assert any(evt.get("phase") == "part_upload" and evt.get("part_number") == 2 for evt in events)
    assert any(evt.get("phase") == "finish" for evt in events)
