from __future__ import annotations

from pathlib import Path
from time import perf_counter

import requests
from requests.adapters import HTTPAdapter

from quark_uploader.services.cancellation import UploadCancellationToken

DEFAULT_STREAM_CHUNK_BYTES = 1024 * 1024


class RequestsOssTransport:
    def __init__(
        self,
        http_client: requests.Session | None = None,
        timeout_seconds: int = 300,
        pool_maxsize: int = 8,
        stream_chunk_bytes: int = DEFAULT_STREAM_CHUNK_BYTES,
        profile_callback=None,
    ) -> None:
        self.http_client = http_client or self._build_session(pool_maxsize)
        self.timeout_seconds = timeout_seconds
        self.stream_chunk_bytes = max(64 * 1024, int(stream_chunk_bytes))
        self.profile_callback = profile_callback

    def _build_session(self, pool_maxsize: int) -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=max(2, int(pool_maxsize)),
            pool_maxsize=max(2, int(pool_maxsize)),
            max_retries=0,
            pool_block=True,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _emit_profile(
        self,
        phase: str,
        *,
        elapsed_seconds: float,
        file_name: str | None = None,
        bytes_sent: int = 0,
        **extra: object,
    ) -> None:
        if self.profile_callback is None:
            return
        payload = {
            "phase": phase,
            "elapsed_ms": round(elapsed_seconds * 1000, 2),
            "bytes_sent": bytes_sent,
        }
        if file_name:
            payload["file_name"] = file_name
        payload.update(extra)
        self.profile_callback(payload)

    def upload_single_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        cancel_token: UploadCancellationToken | None = None,
        file_name: str | None = None,
    ):
        return self.upload_part(
            file_path,
            upload_url,
            headers,
            offset=0,
            size=file_path.stat().st_size,
            cancel_token=cancel_token,
            file_name=file_name or file_path.name,
        )

    def _stream_file(
        self,
        file_path: Path,
        *,
        offset: int,
        size: int,
        cancel_token: UploadCancellationToken | None,
    ):
        with file_path.open("rb") as handle:
            handle.seek(offset)
            remaining = size
            while remaining > 0:
                if cancel_token is not None:
                    cancel_token.raise_if_cancelled()
                chunk = handle.read(min(self.stream_chunk_bytes, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    def upload_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        offset: int,
        size: int,
        cancel_token: UploadCancellationToken | None = None,
        file_name: str | None = None,
    ):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        started_at = perf_counter()
        response = self.http_client.put(
            upload_url,
            data=self._stream_file(
                file_path,
                offset=offset,
                size=size,
                cancel_token=cancel_token,
            ),
            headers=headers,
            timeout=self.timeout_seconds,
        )
        elapsed_seconds = perf_counter() - started_at
        self._emit_profile(
            "oss_part_upload",
            elapsed_seconds=elapsed_seconds,
            bytes_sent=size,
            file_name=file_name or file_path.name,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"OSS 上传失败: {response.status_code} {getattr(response, 'text', '')}"
            )
        etag = response.headers.get("etag", "").strip('"')
        return {"etag": etag}

    def complete_multipart_upload(
        self,
        upload_url: str,
        headers: dict,
        xml_data: str,
        cancel_token: UploadCancellationToken | None = None,
        file_name: str | None = None,
    ):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        started_at = perf_counter()
        response = self.http_client.post(
            upload_url,
            data=xml_data,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        elapsed_seconds = perf_counter() - started_at
        self._emit_profile(
            "oss_complete_multipart",
            elapsed_seconds=elapsed_seconds,
            bytes_sent=len(xml_data.encode("utf-8")),
            file_name=file_name,
        )
        if response.status_code not in {200, 204}:
            raise RuntimeError(
                f"OSS 合并失败: {response.status_code} {getattr(response, 'text', '')}"
            )
        return {"ok": True}
