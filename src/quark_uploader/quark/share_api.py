from __future__ import annotations

from quark_uploader.quark.session import BASE_URL


def build_share_create_url() -> str:
    return f"{BASE_URL}/1/clouddrive/share"


def build_share_password_url() -> str:
    return f"{BASE_URL}/1/clouddrive/share/password"
