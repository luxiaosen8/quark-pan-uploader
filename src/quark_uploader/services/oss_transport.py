from __future__ import annotations

from pathlib import Path

import requests

from quark_uploader.services.cancellation import UploadCancellationToken


class RequestsOssTransport:
    def __init__(self, http_client=None, timeout_seconds: int = 300) -> None:
        self.http_client = http_client or requests
        self.timeout_seconds = timeout_seconds

    def upload_single_part(self, file_path: Path, upload_url: str, headers: dict, cancel_token: UploadCancellationToken | None = None):
        return self.upload_part(file_path, upload_url, headers, offset=0, size=file_path.stat().st_size, cancel_token=cancel_token)

    def upload_part(self, file_path: Path, upload_url: str, headers: dict, offset: int, size: int, cancel_token: UploadCancellationToken | None = None):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        if cancel_token is None:
            with file_path.open("rb") as handle:
                handle.seek(offset)
                data = handle.read(size)
            response = self.http_client.put(
                upload_url,
                data=data,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        else:
            def stream():
                with file_path.open("rb") as handle:
                    handle.seek(offset)
                    remaining = size
                    while remaining > 0:
                        cancel_token.raise_if_cancelled()
                        chunk = handle.read(min(262144, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            response = self.http_client.put(
                upload_url,
                data=stream(),
                headers=headers,
                timeout=self.timeout_seconds,
            )
        if response.status_code != 200:
            raise RuntimeError(f"OSS 上传失败: {response.status_code} {getattr(response, 'text', '')}")
        etag = response.headers.get("etag", "").strip('"')
        return {"etag": etag}

    def complete_multipart_upload(self, upload_url: str, headers: dict, xml_data: str, cancel_token: UploadCancellationToken | None = None):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        response = self.http_client.post(
            upload_url,
            data=xml_data,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code not in {200, 204}:
            raise RuntimeError(f"OSS 合并失败: {response.status_code} {getattr(response, 'text', '')}")
        return {"ok": True}
