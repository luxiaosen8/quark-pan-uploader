from __future__ import annotations

from quark_uploader.quark.session import BASE_URL


def build_upload_pre_url() -> str:
    return f"{BASE_URL}/1/clouddrive/file/upload/pre"


def build_upload_finish_url() -> str:
    return f"{BASE_URL}/1/clouddrive/file/upload/finish"
