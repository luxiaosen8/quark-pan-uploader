from __future__ import annotations

from quark_uploader.quark.session import BASE_URL, QuarkSession


def build_capacity_info_url() -> str:
    return f"{BASE_URL}/1/clouddrive/capacity/growth/info"


class QuarkUserApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def get_capacity_info(self) -> dict:
        return self.session.request("GET", "/1/clouddrive/capacity/growth/info")
