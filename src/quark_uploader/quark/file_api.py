from __future__ import annotations


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
