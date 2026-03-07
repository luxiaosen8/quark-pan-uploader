from __future__ import annotations

from pathlib import Path

import requests


class RequestsOssTransport:
    def __init__(self, http_client=None, timeout_seconds: int = 300) -> None:
        self.http_client = http_client or requests
        self.timeout_seconds = timeout_seconds

    def upload_single_part(self, file_path: Path, upload_url: str, headers: dict):
        return self.upload_part(file_path, upload_url, headers, offset=0, size=file_path.stat().st_size)

    def upload_part(self, file_path: Path, upload_url: str, headers: dict, offset: int, size: int):
        with file_path.open("rb") as handle:
            handle.seek(offset)
            response = self.http_client.put(
                upload_url,
                data=handle.read(size),
                headers=headers,
                timeout=self.timeout_seconds,
            )
        if response.status_code != 200:
            raise RuntimeError(f"OSS 上传失败: {response.status_code} {getattr(response, 'text', '')}")
        etag = response.headers.get("etag", "").strip('"')
        return {"etag": etag}

    def complete_multipart_upload(self, upload_url: str, headers: dict, xml_data: str):
        response = self.http_client.post(
            upload_url,
            data=xml_data,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code not in {200, 204}:
            raise RuntimeError(f"OSS 合并失败: {response.status_code} {getattr(response, 'text', '')}")
        return {"ok": True}
