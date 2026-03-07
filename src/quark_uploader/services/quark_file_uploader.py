from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from quark_uploader.quark.upload_api import (
    build_hash_update_payload,
    build_upload_finish_payload,
    build_upload_pre_payload,
)
from quark_uploader.services.file_manifest import LocalFileEntry


class QuarkFileUploader:
    def __init__(self, upload_api) -> None:
        self.upload_api = upload_api

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
        self.upload_api.update_hash(build_hash_update_payload(task_id, md5_hash, sha1_hash))
        finish_result = self.upload_api.finish(build_upload_finish_payload(task_id, data.get("obj_key")))
        return {"task_id": task_id, "preupload": pre_result, "finish": finish_result}

    def _calculate_hashes(self, path: Path) -> tuple[str, str]:
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
        return md5_hash.hexdigest(), sha1_hash.hexdigest()
