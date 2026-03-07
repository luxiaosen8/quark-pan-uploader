from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FolderTaskStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    RETRYING = "retrying"
    SHARING = "sharing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    STOPPED = "stopped"


class FolderTask(BaseModel):
    local_name: str
    local_path: str
    file_count: int = 0
    total_size: int = 0
    status: FolderTaskStatus = FolderTaskStatus.PENDING
    share_url: str | None = None
    remote_folder_fid: str | None = None
    error_message: str | None = None

    @property
    def can_execute(self) -> bool:
        return self.file_count > 0 and self.status is not FolderTaskStatus.SKIPPED


class AccountSummary(BaseModel):
    nickname: str = ""
    total_bytes: int = 0
    used_bytes: int = 0
    available_bytes: int = 0


class RemoteFolderNode(BaseModel):
    fid: str
    name: str
    parent_fid: str
    has_children: bool = False
    children_loaded: bool = False


class DriveRefreshResult(BaseModel):
    account: AccountSummary = Field(default_factory=AccountSummary)
    root_nodes: list[RemoteFolderNode] = Field(default_factory=list)
