from __future__ import annotations

from pathlib import Path

import requests


class RequestsOssTransport:
    def __init__(self, http_client=None, timeout_seconds: int = 300) -> None:
        self.http_client = http_client or requests
        self.timeout_seconds = timeout_seconds

    def upload_single_part(self, file_path: Path, upload_url: str, headers: dict):
        with file_path.open("rb") as handle:
            response = self.http_client.put(
                upload_url,
                data=handle.read(),
                headers=headers,
                timeout=self.timeout_seconds,
            )
        if response.status_code != 200:
            raise RuntimeError(f"OSS 上传失败: {response.status_code} {getattr(response, 'text', '')}")
        etag = response.headers.get("etag", "").strip('"')
        return {"etag": etag}
