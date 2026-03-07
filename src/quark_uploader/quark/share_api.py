from __future__ import annotations

from quark_uploader.quark.session import BASE_URL, QuarkSession


def build_share_create_url() -> str:
    return f"{BASE_URL}/1/clouddrive/share"


def build_share_password_url() -> str:
    return f"{BASE_URL}/1/clouddrive/share/password"


class QuarkShareApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def create_share(self, payload: dict) -> dict:
        return self.session.request("POST", "/1/clouddrive/share", json=payload)

    def get_share_detail(self, share_id: str) -> dict:
        return self.session.request("POST", "/1/clouddrive/share/password", json={"share_id": share_id})
