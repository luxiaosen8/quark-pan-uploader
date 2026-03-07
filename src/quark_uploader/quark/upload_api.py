from __future__ import annotations

from quark_uploader.quark.session import BASE_URL, QuarkSession


def build_upload_pre_url() -> str:
    return f"{BASE_URL}/1/clouddrive/file/upload/pre"


def build_upload_finish_url() -> str:
    return f"{BASE_URL}/1/clouddrive/file/upload/finish"


class QuarkUploadApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def preupload(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/file/upload/pre", json=payload)

    def finish(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/file/upload/finish", json=payload)
