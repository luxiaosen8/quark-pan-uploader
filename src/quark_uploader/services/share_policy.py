from __future__ import annotations


def build_share_payload(fid: str, title: str) -> dict:
    return {
        "fid_list": [fid],
        "title": title,
        "url_type": 2,
        "expired_type": 1,
    }
