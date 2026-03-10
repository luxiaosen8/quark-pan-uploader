from __future__ import annotations

import base64
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
import hashlib
import json
import mimetypes
import struct
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock
from time import perf_counter

from quark_uploader.quark.upload_api import (
    build_complete_multipart_xml,
    build_hash_update_payload,
    build_post_complete_auth_meta,
    build_put_auth_meta,
    build_upload_auth_payload,
    build_upload_finish_payload,
    build_upload_pre_payload,
    parse_complete_upload_auth_result,
    parse_upload_auth_result,
)
from quark_uploader.services.cancellation import (
    UploadCancellationToken,
    UploadCancelled,
)
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.invoke import call_with_supported_kwargs
from quark_uploader.services.oss_transport import RequestsOssTransport

DEFAULT_OSS_USER_AGENT = (
    "aliyun-sdk-js/1.0.0 Chrome Mobile 139.0.0.0 on Google Nexus 5 (Android 6.0)"
)
DEFAULT_COMPLETE_USER_AGENT = (
    "aliyun-sdk-js/1.0.0 Chrome 139.0.0.0 on OS X 10.15.7 64-bit"
)
SINGLE_PART_MAX_BYTES = 5 * 1024 * 1024
MULTIPART_CHUNK_SIZE = 4 * 1024 * 1024


class QuarkFileUploader:
    def __init__(
        self,
        upload_api,
        oss_transport=None,
        logger=None,
        part_concurrency: int = 3,
        *,
        verbose_logging: bool = False,
        profile_callback=None,
    ) -> None:
        self.upload_api = upload_api
        self.oss_transport = oss_transport or RequestsOssTransport()
        if hasattr(self.oss_transport, "profile_callback"):
            self.oss_transport.profile_callback = self._emit_transport_profile
        self.logger = logger
        self.part_concurrency = max(1, int(part_concurrency))
        self.verbose_logging = verbose_logging
        self.profile_callback = profile_callback
        self._profile_lock = Lock()
        self._profile_buckets: dict[str, dict[str, object]] = {}

    def _log(self, message: str, *, verbose: bool = False) -> None:
        if self.logger is None:
            return
        if verbose and not self.verbose_logging:
            return
        self.logger(message)

    def _record_profile(
        self,
        file_key: str,
        phase: str,
        elapsed_ms: float | None,
        bytes_sent: int = 0,
    ) -> None:
        if elapsed_ms is None:
            return
        with self._profile_lock:
            bucket = self._profile_buckets.setdefault(
                file_key,
                {
                    "phases": {},
                    "total_elapsed_ms": 0.0,
                    "total_bytes_sent": 0,
                    "events": 0,
                },
            )
            phases = bucket["phases"]
            phase_stats = phases.get(phase)
            if phase_stats is None:
                phase_stats = {"count": 0, "elapsed_ms": 0.0, "bytes_sent": 0}
                phases[phase] = phase_stats
            phase_stats["count"] += 1
            phase_stats["elapsed_ms"] += float(elapsed_ms)
            if bytes_sent:
                phase_stats["bytes_sent"] += int(bytes_sent)
                bucket["total_bytes_sent"] += int(bytes_sent)
            bucket["total_elapsed_ms"] += float(elapsed_ms)
            bucket["events"] += 1

    def _consume_profile_bucket(self, file_key: str) -> dict[str, object] | None:
        with self._profile_lock:
            return self._profile_buckets.pop(file_key, None)

    def _emit_profile(self, phase: str, file_name: str, **extra: object) -> None:
        if phase != "file_summary":
            elapsed_ms = extra.get("elapsed_ms")
            bytes_sent = extra.get("bytes_sent", 0)
            self._record_profile(
                file_name,
                phase,
                elapsed_ms if isinstance(elapsed_ms, (int, float)) else None,
                bytes_sent if isinstance(bytes_sent, (int, float)) else 0,
            )
        if self.profile_callback is None:
            return
        payload = {"phase": phase, "file_name": file_name}
        payload.update(extra)
        self.profile_callback(payload)

    def _emit_transport_profile(self, payload: dict) -> None:
        phase = payload.get("phase", "transport")
        file_name = payload.get("file_name", "") or "transport"
        extra = {k: v for k, v in payload.items() if k not in {"phase", "file_name"}}
        self._emit_profile(f"transport_{phase}", file_name, **extra)

    def _elapsed_ms(self, started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 2)

    def _emit_progress(self, callback, **payload) -> None:
        if callback is not None:
            callback(payload)

    def upload_file(
        self,
        file_entry: LocalFileEntry,
        target_parent_fid: str,
        cancel_token: UploadCancellationToken | None = None,
        progress_callback=None,
    ):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        path = Path(file_entry.absolute_path)
        display_name = path.name
        profile_key = file_entry.relative_path or display_name
        file_started = perf_counter()
        success = False
        try:
            self._log(
                f"[DEBUG] 文件上传开始：name={display_name} size={file_entry.size_bytes} target_parent_fid={target_parent_fid}",
                verbose=True,
            )
            self._emit_progress(
                progress_callback,
                phase="file_start",
                file_name=display_name,
                part_number=0,
                part_total=0,
            )
            mime_type, _ = mimetypes.guess_type(str(path))
            mime_type = mime_type or "application/octet-stream"
            hash_started = perf_counter()
            md5_hash, sha1_hash, multipart_contexts = (
                self._calculate_hashes_and_multipart_contexts(path)
            )
            self._emit_profile(
                "hash_calculated",
                profile_key,
                elapsed_ms=self._elapsed_ms(hash_started),
            )
            self._log(
                f"[DEBUG] 文件哈希已计算：md5={md5_hash[:8]}... sha1={sha1_hash[:8]}...",
                verbose=True,
            )
            pre_payload = build_upload_pre_payload(
                file_name=display_name,
                file_size=file_entry.size_bytes,
                parent_fid=target_parent_fid,
                mime_type=mime_type,
            )
            self._emit_progress(
                progress_callback,
                phase="preupload",
                file_name=display_name,
                part_number=0,
                part_total=0,
            )
            pre_started = perf_counter()
            pre_result = self.upload_api.preupload(pre_payload)
            self._emit_profile(
                "preupload_request",
                profile_key,
                elapsed_ms=self._elapsed_ms(pre_started),
            )
            data = pre_result.get("data", {})
            task_id = data.get("task_id", "")
            upload_id = data.get("upload_id", "")
            bucket = data.get("bucket", "ul-zb")
            self._log(
                f"[DEBUG] 预上传成功：task_id={task_id} upload_id={upload_id} bucket={bucket}",
                verbose=True,
            )
            auth_info = data.get("auth_info", "")
            obj_key = data.get("obj_key", "")
            callback_info = data.get("callback") or {}
            update_started = perf_counter()
            self.upload_api.update_hash(
                build_hash_update_payload(task_id, md5_hash, sha1_hash)
            )
            self._emit_profile(
                "hash_update",
                profile_key,
                elapsed_ms=self._elapsed_ms(update_started),
            )
            self._log(f"[DEBUG] 更新哈希完成：task_id={task_id}", verbose=True)

            auth_result = None
            oss_upload = None
            multipart_complete = None
            if auth_info and obj_key and upload_id:
                if file_entry.size_bytes <= SINGLE_PART_MAX_BYTES:
                    auth_result, oss_upload, multipart_complete = self._upload_single_part(
                        path=path,
                        task_id=task_id,
                        auth_info=auth_info,
                        obj_key=obj_key,
                        upload_id=upload_id,
                        bucket=bucket,
                        mime_type=mime_type,
                        callback_info=callback_info,
                        cancel_token=cancel_token,
                        progress_callback=progress_callback,
                        display_name=display_name,
                        profile_key=profile_key,
                    )
                else:
                    auth_result, multipart_complete = self._upload_multiple_parts(
                        path=path,
                        task_id=task_id,
                        auth_info=auth_info,
                        obj_key=obj_key,
                        upload_id=upload_id,
                        bucket=bucket,
                        mime_type=mime_type,
                        callback_info=callback_info,
                        hash_contexts=multipart_contexts,
                        cancel_token=cancel_token,
                        progress_callback=progress_callback,
                        display_name=display_name,
                        profile_key=profile_key,
                    )

            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            self._log(f"[DEBUG] 调用 finish：task_id={task_id} obj_key={obj_key}", verbose=True)
            finish_started = perf_counter()
            self._emit_progress(
                progress_callback,
                phase="finish",
                file_name=display_name,
                part_number=0,
                part_total=0,
            )
            finish_result = self.upload_api.finish(
                build_upload_finish_payload(task_id, obj_key or None)
            )
            self._emit_profile(
                "finish",
                profile_key,
                elapsed_ms=self._elapsed_ms(finish_started),
            )
            self._log(f"[DEBUG] finish 完成：task_id={task_id}", verbose=True)
            success = True
            return {
                "task_id": task_id,
                "preupload": pre_result,
                "auth": auth_result,
                "oss_upload": oss_upload,
                "multipart_complete": multipart_complete,
                "finish": finish_result,
            }
        finally:
            summary = self._consume_profile_bucket(profile_key) or {
                "phases": {},
                "total_elapsed_ms": 0.0,
                "total_bytes_sent": 0,
                "events": 0,
            }
            self._emit_profile(
                "file_summary",
                profile_key,
                status="success" if success else "failed",
                total_elapsed_ms=self._elapsed_ms(file_started),
                total_profiled_ms=summary.get("total_elapsed_ms", 0.0),
                total_profiled_bytes=summary.get("total_bytes_sent", 0),
                phase_stats=summary.get("phases", {}),
                events=summary.get("events", 0),
            )

    def _upload_single_part(
        self,
        path: Path,
        task_id: str,
        auth_info: str,
        obj_key: str,
        upload_id: str,
        bucket: str,
        mime_type: str,
        callback_info: dict,
        cancel_token: UploadCancellationToken | None = None,
        progress_callback=None,
        display_name: str | None = None,
        profile_key: str | None = None,
    ):
        display_name = display_name or path.name
        profile_key = profile_key or display_name
        oss_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self._log(f"[DEBUG] 获取单分片上传授权：part=1 upload_id={upload_id}", verbose=True)
        self._emit_progress(
            progress_callback,
            phase="part_upload",
            file_name=display_name,
            part_number=1,
            part_total=1,
        )
        auth_meta = build_put_auth_meta(
            mime_type=mime_type,
            oss_date=oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            part_number=1,
            user_agent=DEFAULT_OSS_USER_AGENT,
        )
        auth_started = perf_counter()
        auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(task_id=task_id, auth_info=auth_info, auth_meta=auth_meta)
        )
        self._emit_profile(
            "auth_request",
            profile_key,
            elapsed_ms=self._elapsed_ms(auth_started),
            part_number=1,
            part_total=1,
        )
        parsed_auth = parse_upload_auth_result(
            auth_result=auth_result,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            mime_type=mime_type,
            oss_date=oss_date,
            user_agent=DEFAULT_OSS_USER_AGENT,
        )
        oss_upload = call_with_supported_kwargs(
            self.oss_transport.upload_single_part,
            path,
            parsed_auth["upload_url"],
            parsed_auth["headers"],
            cancel_token=cancel_token,
            file_name=profile_key,
        )
        self._log(f"[DEBUG] 单分片上传完成：etag={oss_upload.get('etag', '')}", verbose=True)
        xml_data = build_complete_multipart_xml([oss_upload["etag"]])
        complete_oss_date = datetime.now(timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        complete_auth_meta = build_post_complete_auth_meta(
            oss_date=complete_oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            xml_data=xml_data,
            callback_info=callback_info,
            user_agent=DEFAULT_COMPLETE_USER_AGENT,
        )
        self._log("[DEBUG] 获取单分片合并授权", verbose=True)
        complete_auth_started = perf_counter()
        complete_auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(
                task_id=task_id, auth_info=auth_info, auth_meta=complete_auth_meta
            )
        )
        self._emit_profile(
            "complete_auth_request",
            profile_key,
            elapsed_ms=self._elapsed_ms(complete_auth_started),
            part_total=1,
        )
        parsed_complete = parse_complete_upload_auth_result(
            auth_result=complete_auth_result,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            xml_data=xml_data,
            callback_info=callback_info,
            oss_date=complete_oss_date,
            user_agent=DEFAULT_COMPLETE_USER_AGENT,
        )
        self._log("[DEBUG] 单分片开始执行 OSS 合并完成", verbose=True)
        self._emit_progress(
            progress_callback,
            phase="complete",
            file_name=display_name,
            part_number=1,
            part_total=1,
        )
        complete_started = perf_counter()
        multipart_complete = call_with_supported_kwargs(
            self.oss_transport.complete_multipart_upload,
            parsed_complete["upload_url"],
            parsed_complete["headers"],
            xml_data,
            cancel_token=cancel_token,
            file_name=profile_key,
        )
        self._emit_profile(
            "complete_execute",
            profile_key,
            elapsed_ms=self._elapsed_ms(complete_started),
            part_total=1,
        )
        return complete_auth_result, oss_upload, multipart_complete

    def _upload_multiple_parts(
        self,
        path: Path,
        task_id: str,
        auth_info: str,
        obj_key: str,
        upload_id: str,
        bucket: str,
        mime_type: str,
        callback_info: dict,
        hash_contexts: list[str],
        cancel_token: UploadCancellationToken | None = None,
        progress_callback=None,
        display_name: str | None = None,
        profile_key: str | None = None,
    ):
        if not callback_info:
            raise NotImplementedError("多分片上传需要 callback 信息")
        display_name = display_name or path.name
        profile_key = profile_key or display_name
        auth_result = None
        file_size = path.stat().st_size
        part_total = (file_size + MULTIPART_CHUNK_SIZE - 1) // MULTIPART_CHUNK_SIZE
        self._log(
            f"[DEBUG] 进入多分片上传：file_size={file_size} chunk_size={MULTIPART_CHUNK_SIZE}",
            verbose=True,
        )
        part_jobs: list[tuple[int, int, int, str]] = []
        offset = 0
        for part_number in range(1, part_total + 1):
            part_size = min(MULTIPART_CHUNK_SIZE, file_size - offset)
            hash_ctx = hash_contexts[part_number - 2] if part_number > 1 else ""
            part_jobs.append((part_number, offset, part_size, hash_ctx))
            offset += part_size

        scoped_cancel_token = _ScopedCancellationToken(cancel_token)
        part_etags: dict[int, str] = {}
        pending: dict[Future, tuple[int, int, int, str]] = {}
        failure: Exception | None = None
        next_index = 0

        with ThreadPoolExecutor(
            max_workers=min(self.part_concurrency, part_total),
            thread_name_prefix="upload-part",
        ) as pool:
            while (
                next_index < len(part_jobs)
                and len(pending) < self.part_concurrency
                and not scoped_cancel_token.is_cancelled()
            ):
                job = part_jobs[next_index]
                pending[
                    pool.submit(
                        self._upload_single_multipart_part,
                        path,
                        task_id,
                        auth_info,
                        obj_key,
                        upload_id,
                        bucket,
                        mime_type,
                        scoped_cancel_token,
                        progress_callback,
                        part_total,
                        job,
                        display_name,
                        profile_key,
                    )
                ] = job
                next_index += 1

            while pending:
                done, _ = wait(
                    tuple(pending.keys()),
                    return_when=FIRST_COMPLETED,
                    timeout=0.1,
                )
                if not done:
                    if scoped_cancel_token.is_cancelled():
                        failure = UploadCancelled("multipart upload cancelled")
                        for queued_future in pending:
                            queued_future.cancel()
                        break
                    continue
                for future in done:
                    part_number, _, _, _ = pending.pop(future)
                    try:
                        completed_part_number, auth_result, etag = future.result()
                    except Exception as exc:
                        scoped_cancel_token.request_stop()
                        failure = exc
                        for queued_future in pending:
                            queued_future.cancel()
                        break
                    part_etags[completed_part_number] = etag

                if failure is not None:
                    break

                while (
                    next_index < len(part_jobs)
                    and len(pending) < self.part_concurrency
                    and not scoped_cancel_token.is_cancelled()
                ):
                    job = part_jobs[next_index]
                    pending[
                        pool.submit(
                            self._upload_single_multipart_part,
                            path,
                            task_id,
                            auth_info,
                            obj_key,
                            upload_id,
                            bucket,
                            mime_type,
                            scoped_cancel_token,
                            progress_callback,
                            part_total,
                            job,
                            display_name,
                            profile_key,
                        )
                    ] = job
                    next_index += 1

        if failure is not None:
            raise failure

        ordered_part_etags = [part_etags[index] for index in range(1, part_total + 1)]
        xml_data = build_complete_multipart_xml(ordered_part_etags)
        complete_oss_date = datetime.now(timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        complete_auth_meta = build_post_complete_auth_meta(
            oss_date=complete_oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            xml_data=xml_data,
            callback_info=callback_info,
            user_agent=DEFAULT_COMPLETE_USER_AGENT,
        )
        self._log(f"[DEBUG] 获取多分片合并授权：parts={len(ordered_part_etags)}", verbose=True)
        complete_auth_started = perf_counter()
        complete_auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(
                task_id=task_id, auth_info=auth_info, auth_meta=complete_auth_meta
            )
        )
        self._emit_profile(
            "complete_auth_request",
            profile_key,
            elapsed_ms=self._elapsed_ms(complete_auth_started),
            part_total=part_total,
        )
        parsed_complete = parse_complete_upload_auth_result(
            auth_result=complete_auth_result,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            xml_data=xml_data,
            callback_info=callback_info,
            oss_date=complete_oss_date,
            user_agent=DEFAULT_COMPLETE_USER_AGENT,
        )
        self._log("[DEBUG] 开始执行多分片 OSS 合并完成", verbose=True)
        complete_started = perf_counter()
        multipart_complete = call_with_supported_kwargs(
            self.oss_transport.complete_multipart_upload,
            parsed_complete["upload_url"],
            parsed_complete["headers"],
            xml_data,
            cancel_token=cancel_token,
            file_name=profile_key,
        )
        self._emit_profile(
            "complete_execute",
            profile_key,
            elapsed_ms=self._elapsed_ms(complete_started),
            part_total=part_total,
        )
        return complete_auth_result, multipart_complete

    def _upload_single_multipart_part(
        self,
        path: Path,
        task_id: str,
        auth_info: str,
        obj_key: str,
        upload_id: str,
        bucket: str,
        mime_type: str,
        cancel_token,
        progress_callback,
        part_total: int,
        part_job: tuple[int, int, int, str],
        display_name: str | None = None,
        profile_key: str | None = None,
    ) -> tuple[int, dict, str]:
        part_number, offset, part_size, hash_ctx = part_job
        cancel_token.raise_if_cancelled()
        display_name = display_name or path.name
        profile_key = profile_key or display_name
        oss_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        self._log(
            f"[DEBUG] 获取分片上传授权：part={part_number} offset={offset} size={part_size} hash_ctx={'yes' if hash_ctx else 'no'}",
            verbose=True,
        )
        self._emit_progress(
            progress_callback,
            phase="part_upload",
            file_name=display_name,
            part_number=part_number,
            part_total=part_total,
        )
        auth_meta = build_put_auth_meta(
            mime_type=mime_type,
            oss_date=oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            part_number=part_number,
            user_agent=DEFAULT_OSS_USER_AGENT,
            hash_ctx=hash_ctx,
        )
        auth_started = perf_counter()
        auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(
                task_id=task_id, auth_info=auth_info, auth_meta=auth_meta
            )
        )
        self._emit_profile(
            "auth_request",
            profile_key,
            elapsed_ms=self._elapsed_ms(auth_started),
            part_number=part_number,
            part_total=part_total,
        )
        parsed_auth = parse_upload_auth_result(
            auth_result=auth_result,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            mime_type=mime_type,
            oss_date=oss_date,
            user_agent=DEFAULT_OSS_USER_AGENT,
            part_number=part_number,
            hash_ctx=hash_ctx,
        )
        put_result = call_with_supported_kwargs(
            self.oss_transport.upload_part,
            path,
            parsed_auth["upload_url"],
            parsed_auth["headers"],
            offset=offset,
            size=part_size,
            cancel_token=cancel_token,
            file_name=profile_key,
        )
        self._log(
            f"[DEBUG] 分片上传完成：part={part_number} etag={put_result.get('etag', '')}",
            verbose=True,
        )
        return part_number, auth_result, put_result["etag"]

    def _calculate_hashes_and_multipart_contexts(
        self, path: Path
    ) -> tuple[str, str, list[str]]:
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        h0, h1, h2, h3, h4 = self._initial_sha1_state()
        processed_bytes = 0
        multipart_contexts: list[str] = []
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(MULTIPART_CHUNK_SIZE), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                full_block_length = len(chunk) - (len(chunk) % 64)
                if full_block_length:
                    h0, h1, h2, h3, h4 = self._apply_sha1_blocks(
                        h0, h1, h2, h3, h4, chunk[:full_block_length]
                    )
                processed_bytes += len(chunk)
                multipart_contexts.append(
                    self._encode_hash_context(h0, h1, h2, h3, h4, processed_bytes * 8)
                )
        if multipart_contexts:
            multipart_contexts.pop()
        return md5_hash.hexdigest(), sha1_hash.hexdigest(), multipart_contexts

    def _initial_sha1_state(self) -> tuple[int, int, int, int, int]:
        return 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0

    def _encode_hash_context(
        self, h0: int, h1: int, h2: int, h3: int, h4: int, processed_bits: int
    ) -> str:
        hash_context = {
            "hash_type": "sha1",
            "h0": str(h0),
            "h1": str(h1),
            "h2": str(h2),
            "h3": str(h3),
            "h4": str(h4),
            "Nl": str(processed_bits),
            "Nh": "0",
            "data": "",
            "num": "0",
        }
        return base64.b64encode(
            json.dumps(hash_context, separators=(",", ":")).encode("utf-8")
        ).decode("utf-8")

    def _apply_sha1_blocks(
        self, h0: int, h1: int, h2: int, h3: int, h4: int, data: bytes
    ) -> tuple[int, int, int, int, int]:
        data_len = len(data)
        for i in range(0, data_len, 64):
            block = data[i : i + 64]
            if len(block) < 64:
                break
            w = [struct.unpack(">I", block[j : j + 4])[0] for j in range(0, 64, 4)]
            for t in range(16, 80):
                value = w[t - 3] ^ w[t - 8] ^ w[t - 14] ^ w[t - 16]
                w.append(((value << 1) | (value >> 31)) & 0xFFFFFFFF)
            a, b, c, d, e = h0, h1, h2, h3, h4
            for t in range(80):
                if t < 20:
                    f = (b & c) | ((~b) & d)
                    k = 0x5A827999
                elif t < 40:
                    f = b ^ c ^ d
                    k = 0x6ED9EBA1
                elif t < 60:
                    f = (b & c) | (b & d) | (c & d)
                    k = 0x8F1BBCDC
                else:
                    f = b ^ c ^ d
                    k = 0xCA62C1D6
                temp = (((a << 5) | (a >> 27)) + f + e + k + w[t]) & 0xFFFFFFFF
                e = d
                d = c
                c = ((b << 30) | (b >> 2)) & 0xFFFFFFFF
                b = a
                a = temp
            h0 = (h0 + a) & 0xFFFFFFFF
            h1 = (h1 + b) & 0xFFFFFFFF
            h2 = (h2 + c) & 0xFFFFFFFF
            h3 = (h3 + d) & 0xFFFFFFFF
            h4 = (h4 + e) & 0xFFFFFFFF
        return h0, h1, h2, h3, h4


class _ScopedCancellationToken:
    def __init__(self, parent: UploadCancellationToken | None) -> None:
        self.parent = parent
        self._event = Event()

    def request_stop(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set() or bool(
            self.parent is not None and self.parent.is_cancelled()
        )

    def raise_if_cancelled(self, message: str = "multipart upload cancelled") -> None:
        if self.is_cancelled():
            raise UploadCancelled(message)
