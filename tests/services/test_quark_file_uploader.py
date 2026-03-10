from __future__ import annotations

from pathlib import Path

from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.quark_file_uploader import QuarkFileUploader


class FakeUploadApi:
    def preupload(self, payload: dict) -> dict:
        return {
            "data": {
                "task_id": "task-1",
                "upload_id": "upload-1",
                "bucket": "bucket",
                "auth_info": "auth-info",
                "obj_key": "obj-key",
                "callback": {"callbackUrl": "https://callback"},
            }
        }

    def update_hash(self, payload: dict) -> dict:
        return {"ok": True}

    def get_upload_auth(self, payload: dict) -> dict:
        return {"data": {"auth_key": "auth"}}

    def finish(self, payload: dict) -> dict:
        return {"data": {"fid": "fid-1"}}


class FakeOssTransport:
    def upload_single_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        cancel_token=None,
        file_name: str | None = None,
    ):
        return {"etag": "etag-1"}

    def complete_multipart_upload(
        self,
        upload_url: str,
        headers: dict,
        xml_data: str,
        cancel_token=None,
        file_name: str | None = None,
    ):
        return {"ok": True}


def test_upload_file_handles_single_part_upload(tmp_path) -> None:
    file_path = tmp_path / "demo.txt"
    file_path.write_text("hello", encoding="utf-8")
    uploader = QuarkFileUploader(FakeUploadApi(), oss_transport=FakeOssTransport())
    file_entry = LocalFileEntry(
        local_name="demo",
        absolute_path=str(file_path),
        relative_path="demo.txt",
        size_bytes=file_path.stat().st_size,
    )

    result = uploader.upload_file(file_entry, target_parent_fid="root")

    assert result["task_id"] == "task-1"
    assert result["finish"]["data"]["fid"] == "fid-1"
