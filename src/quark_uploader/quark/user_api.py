from __future__ import annotations

from quark_uploader.quark.session import BASE_URL


def build_capacity_info_url() -> str:
    return f"{BASE_URL}/1/clouddrive/capacity/growth/info"
