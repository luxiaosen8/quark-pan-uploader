from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter, sleep

from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.quark_file_uploader import (
    MULTIPART_CHUNK_SIZE,
    QuarkFileUploader,
)

DATASETS: dict[str, list[int]] = {
    "small": [384 * 1024] * 8,
    "large": [MULTIPART_CHUNK_SIZE * 2 + 512 * 1024] * 3,
    "mixed": [
        384 * 1024,
        MULTIPART_CHUNK_SIZE + 256 * 1024,
        MULTIPART_CHUNK_SIZE * 2,
        768 * 1024,
        MULTIPART_CHUNK_SIZE * 3,
    ],
}


class BenchmarkUploadApi:
    def __init__(
        self,
        *,
        metadata_delay_seconds: float = 0.01,
        auth_delay_seconds: float = 0.015,
    ) -> None:
        self.metadata_delay_seconds = metadata_delay_seconds
        self.auth_delay_seconds = auth_delay_seconds
        self._counter = 0

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def preupload(self, payload: dict) -> dict:
        sleep(self.metadata_delay_seconds)
        job_id = self._next_id()
        return {
            "data": {
                "task_id": f"task-{job_id}",
                "upload_id": f"upload-{job_id}",
                "bucket": "bench",
                "auth_info": "auth",
                "obj_key": f"object-{job_id}",
                "callback": {"callbackUrl": "https://callback"},
            }
        }

    def update_hash(self, payload: dict) -> dict:
        sleep(self.metadata_delay_seconds)
        return {"ok": True}

    def get_upload_auth(self, payload: dict) -> dict:
        sleep(self.auth_delay_seconds)
        return {"data": {"auth_key": "auth"}}

    def finish(self, payload: dict) -> dict:
        sleep(self.metadata_delay_seconds)
        return {"data": {"fid": f"fid-{payload['task_id']}"}}


class BenchmarkTransport:
    def __init__(
        self,
        *,
        bandwidth_bytes_per_second: int = 8 * 1024 * 1024,
        latency_seconds: float = 0.01,
    ) -> None:
        self.bandwidth_bytes_per_second = bandwidth_bytes_per_second
        self.latency_seconds = latency_seconds

    def upload_single_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        cancel_token=None,
        file_name: str | None = None,
    ):
        return self.upload_part(
            file_path,
            upload_url,
            headers,
            offset=0,
            size=file_path.stat().st_size,
            cancel_token=cancel_token,
            file_name=file_name,
        )

    def upload_part(
        self,
        file_path: Path,
        upload_url: str,
        headers: dict,
        offset: int,
        size: int,
        cancel_token=None,
        file_name: str | None = None,
    ):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        transmit_seconds = size / self.bandwidth_bytes_per_second
        sleep(self.latency_seconds + transmit_seconds)
        return {"etag": f"etag-{offset}-{size}"}

    def complete_multipart_upload(
        self,
        upload_url: str,
        headers: dict,
        xml_data: str,
        cancel_token=None,
        file_name: str | None = None,
    ):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        sleep(self.latency_seconds)
        return {"ok": True}


def _build_entries(base: Path, sizes: list[int]) -> list[LocalFileEntry]:
    entries: list[LocalFileEntry] = []
    for index, size in enumerate(sizes):
        file_path = base / f"dataset-{index}.bin"
        with file_path.open("wb") as handle:
            if size > 0:
                handle.seek(size - 1)
                handle.write(b"\0")
        entries.append(
            LocalFileEntry(
                local_name=file_path.name,
                absolute_path=str(file_path),
                relative_path=file_path.name,
                size_bytes=size,
            )
        )
    return entries


def _total_parts(sizes: list[int]) -> int:
    total = 0
    for size in sizes:
        if size <= 0:
            continue
        total += max(1, (size + MULTIPART_CHUNK_SIZE - 1) // MULTIPART_CHUNK_SIZE)
    return total


def _measure_dataset(
    sizes: list[int],
    *,
    job_concurrency: int,
    part_concurrency: int,
) -> dict:
    with TemporaryDirectory() as tmp:
        base = Path(tmp)
        entries = _build_entries(base, sizes)
        uploader = QuarkFileUploader(
            upload_api=BenchmarkUploadApi(),
            oss_transport=BenchmarkTransport(),
            part_concurrency=part_concurrency,
        )

        def _upload(entry: LocalFileEntry) -> None:
            uploader.upload_file(entry, target_parent_fid="remote-root")

        started_at = perf_counter()
        with ThreadPoolExecutor(max_workers=job_concurrency) as pool:
            futures = [pool.submit(_upload, entry) for entry in entries]
            for future in as_completed(futures):
                future.result()
        elapsed = perf_counter() - started_at
        total_parts = _total_parts(sizes)
        total_bytes = sum(max(0, size) for size in sizes)
        return {
            "duration_seconds": elapsed,
            "jobs": len(entries),
            "parts": total_parts,
            "total_bytes": total_bytes,
            "average_parts_per_second": 0.0
            if elapsed == 0
            else round(total_parts / elapsed, 2),
        }


def run_benchmark_suite() -> dict:
    serial: dict[str, dict] = {}
    concurrent: dict[str, dict] = {}
    for name, dataset in DATASETS.items():
        serial[name] = _measure_dataset(
            dataset,
            job_concurrency=1,
            part_concurrency=1,
        )
        concurrent[name] = _measure_dataset(
            dataset,
            job_concurrency=2,
            part_concurrency=3,
        )
    return {"serial": serial, "concurrent": concurrent}


def main() -> int:
    print(json.dumps(run_benchmark_suite(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
