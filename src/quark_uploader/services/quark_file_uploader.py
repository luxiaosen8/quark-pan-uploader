from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import struct
from datetime import datetime, timezone
from pathlib import Path

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
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.oss_transport import RequestsOssTransport


DEFAULT_OSS_USER_AGENT = "aliyun-sdk-js/1.0.0 Chrome Mobile 139.0.0.0 on Google Nexus 5 (Android 6.0)"
DEFAULT_COMPLETE_USER_AGENT = "aliyun-sdk-js/1.0.0 Chrome 139.0.0.0 on OS X 10.15.7 64-bit"
SINGLE_PART_MAX_BYTES = 5 * 1024 * 1024
MULTIPART_CHUNK_SIZE = 4 * 1024 * 1024


class QuarkFileUploader:
    def __init__(self, upload_api, oss_transport=None) -> None:
        self.upload_api = upload_api
        self.oss_transport = oss_transport or RequestsOssTransport()

    def upload_file(self, file_entry: LocalFileEntry, target_parent_fid: str):
        path = Path(file_entry.absolute_path)
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"
        md5_hash, sha1_hash = self._calculate_hashes(path)
        pre_payload = build_upload_pre_payload(
            file_name=path.name,
            file_size=file_entry.size_bytes,
            parent_fid=target_parent_fid,
            mime_type=mime_type,
        )
        pre_result = self.upload_api.preupload(pre_payload)
        data = pre_result.get("data", {})
        task_id = data.get("task_id", "")
        auth_info = data.get("auth_info", "")
        obj_key = data.get("obj_key", "")
        upload_id = data.get("upload_id", "")
        bucket = data.get("bucket", "ul-zb")
        callback_info = data.get("callback") or {}
        self.upload_api.update_hash(build_hash_update_payload(task_id, md5_hash, sha1_hash))

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
                )

        finish_result = self.upload_api.finish(build_upload_finish_payload(task_id, obj_key or None))
        return {
            "task_id": task_id,
            "preupload": pre_result,
            "auth": auth_result,
            "oss_upload": oss_upload,
            "multipart_complete": multipart_complete,
            "finish": finish_result,
        }

    def _upload_single_part(self, path: Path, task_id: str, auth_info: str, obj_key: str, upload_id: str, bucket: str, mime_type: str, callback_info: dict):
        oss_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        auth_meta = build_put_auth_meta(
            mime_type=mime_type,
            oss_date=oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            part_number=1,
            user_agent=DEFAULT_OSS_USER_AGENT,
        )
        auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(task_id=task_id, auth_info=auth_info, auth_meta=auth_meta)
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
        oss_upload = self.oss_transport.upload_single_part(path, parsed_auth["upload_url"], parsed_auth["headers"])
        xml_data = build_complete_multipart_xml([oss_upload["etag"]])
        complete_oss_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        complete_auth_meta = build_post_complete_auth_meta(
            oss_date=complete_oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            xml_data=xml_data,
            callback_info=callback_info,
            user_agent=DEFAULT_COMPLETE_USER_AGENT,
        )
        complete_auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(task_id=task_id, auth_info=auth_info, auth_meta=complete_auth_meta)
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
        multipart_complete = self.oss_transport.complete_multipart_upload(
            parsed_complete["upload_url"], parsed_complete["headers"], xml_data
        )
        return complete_auth_result, oss_upload, multipart_complete

    def _upload_multiple_parts(self, path: Path, task_id: str, auth_info: str, obj_key: str, upload_id: str, bucket: str, mime_type: str, callback_info: dict):
        if not callback_info:
            raise NotImplementedError("多分片上传需要 callback 信息")
        part_etags: list[str] = []
        auth_result = None
        file_size = path.stat().st_size
        offset = 0
        part_number = 1
        while offset < file_size:
            part_size = min(MULTIPART_CHUNK_SIZE, file_size - offset)
            oss_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
            hash_ctx = self._calculate_incremental_hash_context(path, part_number) if part_number > 1 else ""
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
            auth_result = self.upload_api.get_upload_auth(
                build_upload_auth_payload(task_id=task_id, auth_info=auth_info, auth_meta=auth_meta)
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
            put_result = self.oss_transport.upload_part(path, parsed_auth["upload_url"], parsed_auth["headers"], offset=offset, size=part_size)
            part_etags.append(put_result["etag"])
            offset += part_size
            part_number += 1
        xml_data = build_complete_multipart_xml(part_etags)
        complete_oss_date = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        complete_auth_meta = build_post_complete_auth_meta(
            oss_date=complete_oss_date,
            bucket=bucket,
            obj_key=obj_key,
            upload_id=upload_id,
            xml_data=xml_data,
            callback_info=callback_info,
            user_agent=DEFAULT_COMPLETE_USER_AGENT,
        )
        complete_auth_result = self.upload_api.get_upload_auth(
            build_upload_auth_payload(task_id=task_id, auth_info=auth_info, auth_meta=complete_auth_meta)
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
        multipart_complete = self.oss_transport.complete_multipart_upload(
            parsed_complete["upload_url"], parsed_complete["headers"], xml_data
        )
        return complete_auth_result, multipart_complete

    def _calculate_incremental_hash_context(self, path: Path, part_number: int) -> str:
        processed_bytes = (part_number - 1) * MULTIPART_CHUNK_SIZE
        processed_bits = processed_bytes * 8
        with path.open("rb") as handle:
            previous_data = handle.read(processed_bytes)
        h0, h1, h2, h3, h4 = self._calculate_sha1_incremental_state(previous_data)
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
        return base64.b64encode(json.dumps(hash_context, separators=(",", ":")).encode("utf-8")).decode("utf-8")

    def _calculate_sha1_incremental_state(self, data: bytes) -> tuple[int, int, int, int, int]:
        h0 = 0x67452301
        h1 = 0xEFCDAB89
        h2 = 0x98BADCFE
        h3 = 0x10325476
        h4 = 0xC3D2E1F0
        data_len = len(data)
        for i in range(0, data_len - (data_len % 64), 64):
            block = data[i:i + 64]
            w = [struct.unpack('>I', block[j:j + 4])[0] for j in range(0, 64, 4)]
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

    def _calculate_hashes(self, path: Path) -> tuple[str, str]:
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
        return md5_hash.hexdigest(), sha1_hash.hexdigest()
