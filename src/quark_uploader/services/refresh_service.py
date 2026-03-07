from __future__ import annotations

from quark_uploader.models import AccountSummary, DriveRefreshResult, RemoteFolderNode


def extract_account_summary(payload: dict) -> AccountSummary:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    member = data.get("member") or data.get("members") or data.get("user") or {}
    capacity = data.get("capacity") or {}
    total = int(capacity.get("total") or data.get("total") or 0)
    used = int(capacity.get("used") or data.get("used") or 0)
    nickname = str(member.get("nickname") or member.get("name") or data.get("nickname") or "")
    return AccountSummary(
        nickname=nickname,
        total_bytes=total,
        used_bytes=used,
        available_bytes=max(total - used, 0),
    )


def extract_folder_nodes(parent_fid: str, payload: dict) -> list[RemoteFolderNode]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    rows = data.get("list", []) if isinstance(data, dict) else []
    nodes: list[RemoteFolderNode] = []
    for row in rows:
        if not row.get("dir"):
            continue
        file_count = int(row.get("file_count") or row.get("dir_file_count") or 0)
        nodes.append(
            RemoteFolderNode(
                fid=str(row.get("fid", "")),
                name=str(row.get("file_name") or row.get("title") or ""),
                parent_fid=parent_fid,
                has_children=file_count > 0,
            )
        )
    return nodes


class DriveRefreshService:
    def __init__(self, user_api, file_api, root_fid: str = "0") -> None:
        self.user_api = user_api
        self.file_api = file_api
        self.root_fid = root_fid

    def refresh(self) -> DriveRefreshResult:
        account_payload = self.user_api.get_capacity_info()
        folder_payload = self.file_api.list_directory(self.root_fid)
        return DriveRefreshResult(
            account=extract_account_summary(account_payload),
            root_nodes=extract_folder_nodes(self.root_fid, folder_payload),
        )

    def load_children(self, parent_fid: str) -> list[RemoteFolderNode]:
        return extract_folder_nodes(parent_fid, self.file_api.list_directory(parent_fid))
