from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FolderTaskStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
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
