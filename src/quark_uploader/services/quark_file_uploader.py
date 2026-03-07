from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from quark_uploader.quark.upload_api import (
    build_hash_update_payload,
    build_put_auth_meta,
    build_upload_auth_payload,
    build_upload_finish_payload,
    build_upload_pre_payload,
    parse_upload_auth_result,
)
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.oss_transport import RequestsOssTransport


DEFAULT_OSS_USER_AGENT = "aliyun-sdk-js/1.0.0 Chrome Mobile 139.0.0.0 on Google Nexus 5 (Android 6.0)"
SINGLE_PART_MAX_BYTES = 5 * 1024 * 1024


class QuarkFileUploader:
    def __init__(self, upload_api, oss_transport=None) -> None:
        self.upload_api = upload_api
        self.oss_transport = oss_transport or RequestsOssTransport()

    def upload_file(self, file_entry: LocalFileEntry, target_parent_fid: str):
        path = Path(file_entry.absolute_path)
        if file_entry.size_bytes > SINGLE_PART_MAX_BYTES:
            raise NotImplementedError("当前仅实现 5MB 以内单分片上传")
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
        self.upload_api.update_hash(build_hash_update_payload(task_id, md5_hash, sha1_hash))

        oss_upload = None
        auth_result = None
        if auth_info and obj_key and upload_id:
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

        finish_result = self.upload_api.finish(build_upload_finish_payload(task_id, obj_key or None))
        return {
            "task_id": task_id,
            "preupload": pre_result,
            "auth": auth_result,
            "oss_upload": oss_upload,
            "finish": finish_result,
        }

    def _calculate_hashes(self, path: Path) -> tuple[str, str]:
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
        return md5_hash.hexdigest(), sha1_hash.hexdigest()
