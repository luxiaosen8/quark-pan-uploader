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


def build_create_directory_payload(parent_fid: str, folder_name: str) -> dict[str, str | bool]:
    return {
        "pdir_fid": parent_fid,
        "file_name": folder_name,
        "dir_init_lock": False,
        "dir_path": "",
    }


class QuarkFileApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def list_directory(self, parent_fid: str) -> dict:
        return self.session.request("GET", "/1/clouddrive/file/sort", params=build_sort_params(parent_fid))

    def create_directory(self, parent_fid: str, folder_name: str) -> dict:
        return self.session.request(
            "POST",
            "/1/clouddrive/file",
            json=build_create_directory_payload(parent_fid, folder_name),
        )
