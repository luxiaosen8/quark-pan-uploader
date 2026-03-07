from __future__ import annotations


def decide_upload_mode(preupload_data: dict) -> str:
    if preupload_data.get("rapid_upload"):
        return "instant"
    if preupload_data.get("multipart"):
        return "multipart"
    return "single"
