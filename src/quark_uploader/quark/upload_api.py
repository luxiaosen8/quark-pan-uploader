from __future__ import annotations

import base64
import hashlib
import json
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


def build_put_auth_meta(
    mime_type: str,
    oss_date: str,
    bucket: str,
    obj_key: str,
    upload_id: str,
    part_number: int,
    user_agent: str,
    hash_ctx: str = "",
) -> str:
    lines = [
        "PUT",
        "",
        mime_type,
        oss_date,
        f"x-oss-date:{oss_date}",
    ]
    if hash_ctx:
        lines.append(f"x-oss-hash-ctx:{hash_ctx}")
    lines.append(f"x-oss-user-agent:{user_agent}")
    lines.append(f"/{bucket}/{obj_key}?partNumber={part_number}&uploadId={upload_id}")
    return "\n".join(lines)


def build_complete_multipart_xml(etags: list[str]) -> str:
    parts = [
        f'<Part><PartNumber>{index}</PartNumber><ETag>"{etag}"</ETag></Part>'
        for index, etag in enumerate(etags, start=1)
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<CompleteMultipartUpload>\n'
        + "\n".join(parts)
        + '\n</CompleteMultipartUpload>'
    )


def build_post_complete_auth_meta(
    oss_date: str,
    bucket: str,
    obj_key: str,
    upload_id: str,
    xml_data: str,
    callback_info: dict,
    user_agent: str,
) -> str:
    xml_md5 = base64.b64encode(hashlib.md5(xml_data.encode("utf-8")).digest()).decode("utf-8")
    callback_b64 = base64.b64encode(json.dumps(callback_info, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    lines = [
        "POST",
        xml_md5,
        "application/xml",
        oss_date,
        f"x-oss-callback:{callback_b64}",
        f"x-oss-date:{oss_date}",
        f"x-oss-user-agent:{user_agent}",
        f"/{bucket}/{obj_key}?uploadId={upload_id}",
    ]
    return "\n".join(lines)


def parse_upload_auth_result(
    auth_result: dict,
    bucket: str,
    obj_key: str,
    upload_id: str,
    mime_type: str,
    oss_date: str,
    user_agent: str,
    part_number: int = 1,
    hash_ctx: str = "",
) -> dict:
    auth_key = auth_result.get("data", {}).get("auth_key", "")
    headers = {
        "Content-Type": mime_type,
        "x-oss-date": oss_date,
        "x-oss-user-agent": user_agent,
    }
    if auth_key:
        headers["authorization"] = auth_key
    if hash_ctx:
        headers["X-Oss-Hash-Ctx"] = hash_ctx
    return {
        "upload_url": f"https://{bucket}.pds.quark.cn/{obj_key}?partNumber={part_number}&uploadId={upload_id}",
        "headers": headers,
    }


def parse_complete_upload_auth_result(
    auth_result: dict,
    bucket: str,
    obj_key: str,
    upload_id: str,
    xml_data: str,
    callback_info: dict,
    oss_date: str,
    user_agent: str,
) -> dict:
    auth_key = auth_result.get("data", {}).get("auth_key", "")
    callback_b64 = base64.b64encode(json.dumps(callback_info, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    xml_md5 = base64.b64encode(hashlib.md5(xml_data.encode("utf-8")).digest()).decode("utf-8")
    headers = {
        "Content-Type": "application/xml",
        "x-oss-date": oss_date,
        "x-oss-user-agent": user_agent,
        "x-oss-callback": callback_b64,
        "Content-MD5": xml_md5,
    }
    if auth_key:
        headers["authorization"] = auth_key
    return {
        "upload_url": f"https://{bucket}.pds.quark.cn/{obj_key}?uploadId={upload_id}",
        "headers": headers,
    }


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
