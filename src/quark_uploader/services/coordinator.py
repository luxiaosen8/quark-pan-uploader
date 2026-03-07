from __future__ import annotations

from quark_uploader.models import FolderTask, FolderTaskStatus


def mark_share_success(task: FolderTask, share_url: str) -> None:
    task.status = FolderTaskStatus.COMPLETED
    task.share_url = share_url
