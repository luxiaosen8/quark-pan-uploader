from __future__ import annotations

from time import time

from quark_uploader.quark.session import BASE_URL, QuarkSession


def build_upload_pre_url() -> str:
    return f"{BASE_URL}/1/clouddrive/file/upload/pre"


def build_upload_finish_url() -> str:
    return f"{BASE_URL}/1/clouddrive/file/upload/finish"


def build_upload_pre_payload(
    file_name: str,
    file_size: int,
    parent_fid: str,
    mime_type: str,
    current_time_ms: int | None = None,
) -> dict:
    now_ms = int(time() * 1000) if current_time_ms is None else current_time_ms
    return {
        "ccp_hash_update": True,
        "parallel_upload": True,
        "pdir_fid": parent_fid,
        "dir_name": "",
        "size": file_size,
        "file_name": file_name,
        "format_type": mime_type,
        "l_updated_at": now_ms,
        "l_created_at": now_ms,
    }


def build_hash_update_payload(task_id: str, md5: str, sha1: str) -> dict:
    return {"task_id": task_id, "md5": md5, "sha1": sha1}


def build_upload_auth_payload(task_id: str, auth_info: str, auth_meta: str) -> dict:
    return {"task_id": task_id, "auth_info": auth_info, "auth_meta": auth_meta}


def build_upload_finish_payload(task_id: str, obj_key: str | None = None) -> dict:
    payload = {"task_id": task_id}
    if obj_key:
        payload["obj_key"] = obj_key
    return payload


class QuarkUploadApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def preupload(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/file/upload/pre", json=payload)

    def update_hash(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/file/update/hash", json=payload)

    def get_upload_auth(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/file/upload/auth", json=payload)

    def finish(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/file/upload/finish", json=payload)
