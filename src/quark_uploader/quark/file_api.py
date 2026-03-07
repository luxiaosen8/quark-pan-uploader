from __future__ import annotations

from quark_uploader.quark.session import QuarkSession


def build_sort_params(parent_fid: str) -> dict[str, str | int]:
    return {
        "pr": "ucpro",
        "fr": "pc",
        "uc_param_str": "",
        "pdir_fid": parent_fid,
        "_page": 1,
        "_size": 50,
        "_fetch_total": 1,
        "_fetch_sub_dirs": 1,
        "_sort": "file_type:asc,updated_at:desc",
    }


class QuarkFileApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def list_directory(self, parent_fid: str) -> dict:
        return self.session.request("GET", "/1/clouddrive/file/sort", params=build_sort_params(parent_fid))
