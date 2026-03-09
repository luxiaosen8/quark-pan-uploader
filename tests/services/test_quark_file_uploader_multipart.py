from __future__ import annotations

from pathlib import Path

import pytest

from quark_uploader.services.cancellation import (
    UploadCancellationToken,
    UploadCancelled,
)
from quark_uploader.services.quark_file_uploader import (
    MULTIPART_CHUNK_SIZE,
    QuarkFileUploader,
)


class FakeUploadApi:
    def get_upload_auth(self, payload: dict) -> dict:
        return {"data": {"auth_key": "auth"}}


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[int] = []
        self.complete_payload: str = ""

    def upload_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        offset: int,
        size: int,
        cancel_token=None,
    ):
        part_number = int(upload_url.split("partNumber=")[1].split("&")[0])
        self.calls.append(part_number)
        return {"etag": f"etag-{part_number}"}

    def complete_multipart_upload(
        self, upload_url: str, headers: dict, xml_data: str, cancel_token=None
    ):
        self.complete_payload = xml_data
        return {"ok": True}


class FailingTransport(RecordingTransport):
    def upload_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        offset: int,
        size: int,
        cancel_token=None,
    ):
        part_number = int(upload_url.split("partNumber=")[1].split("&")[0])
        if part_number == 2:
            raise RuntimeError("part failed")
        return super().upload_part(
            file_path, upload_url, headers, offset, size, cancel_token=cancel_token
        )


class StopAfterFirstPartTransport(RecordingTransport):
    def upload_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        offset: int,
        size: int,
        cancel_token=None,
    ):
        part_number = int(upload_url.split("partNumber=")[1].split("&")[0])
        self.calls.append(part_number)
        if part_number == 1 and cancel_token is not None:
            cancel_token.request_stop()
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        return {"etag": f"etag-{part_number}"}


def _create_large_file(path: Path) -> None:
    with path.open("wb") as handle:
        handle.seek(MULTIPART_CHUNK_SIZE * 2)
        handle.write(b"!")


def test_multipart_upload_preserves_etag_order(tmp_path) -> None:
    file_path = tmp_path / "large.bin"
    _create_large_file(file_path)
    transport = RecordingTransport()
    uploader = QuarkFileUploader(
        FakeUploadApi(), oss_transport=transport, part_concurrency=3
    )

    uploader._upload_multiple_parts(
        path=file_path,
        task_id="task-1",
        auth_info="auth-info",
        obj_key="obj-key",
        upload_id="upload-id",
        bucket="bucket",
        mime_type="application/octet-stream",
        callback_info={"callbackUrl": "https://callback"},
        hash_contexts=["ctx-1", "ctx-2"],
    )

    assert (
        '<PartNumber>1</PartNumber><ETag>"etag-1"</ETag>' in transport.complete_payload
    )
    assert (
        '<PartNumber>2</PartNumber><ETag>"etag-2"</ETag>' in transport.complete_payload
    )
    assert (
        '<PartNumber>3</PartNumber><ETag>"etag-3"</ETag>' in transport.complete_payload
    )


def test_multipart_upload_fails_when_any_part_fails(tmp_path) -> None:
    file_path = tmp_path / "large.bin"
    _create_large_file(file_path)
    uploader = QuarkFileUploader(
        FakeUploadApi(), oss_transport=FailingTransport(), part_concurrency=3
    )

    with pytest.raises(RuntimeError, match="part failed"):
        uploader._upload_multiple_parts(
            path=file_path,
            task_id="task-1",
            auth_info="auth-info",
            obj_key="obj-key",
            upload_id="upload-id",
            bucket="bucket",
            mime_type="application/octet-stream",
            callback_info={"callbackUrl": "https://callback"},
            hash_contexts=["ctx-1", "ctx-2"],
        )


def test_multipart_upload_does_not_schedule_new_parts_after_stop(tmp_path) -> None:
    file_path = tmp_path / "large.bin"
    _create_large_file(file_path)
    transport = StopAfterFirstPartTransport()
    uploader = QuarkFileUploader(
        FakeUploadApi(), oss_transport=transport, part_concurrency=1
    )

    with pytest.raises(UploadCancelled):
        uploader._upload_multiple_parts(
            path=file_path,
            task_id="task-1",
            auth_info="auth-info",
            obj_key="obj-key",
            upload_id="upload-id",
            bucket="bucket",
            mime_type="application/octet-stream",
            callback_info={"callbackUrl": "https://callback"},
            hash_contexts=["ctx-1", "ctx-2"],
            cancel_token=UploadCancellationToken(),
        )

    assert transport.calls == [1]
