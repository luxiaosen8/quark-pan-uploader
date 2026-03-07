from __future__ import annotations

from pathlib import Path

from quark_uploader.models import FolderTask, FolderTaskStatus

EMPTY_FOLDER_MESSAGE = "empty folder"


def _collect_folder_stats(folder: Path) -> tuple[int, int]:
    file_count = 0
    total_size = 0
    for file_path in folder.rglob("*"):
        if file_path.is_file():
            file_count += 1
            total_size += file_path.stat().st_size
    return file_count, total_size


def scan_first_level_subfolders(root: Path) -> list[FolderTask]:
    tasks: list[FolderTask] = []
    for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not entry.is_dir():
            continue
        file_count, total_size = _collect_folder_stats(entry)
        status = FolderTaskStatus.PENDING
        error_message = None
        if file_count == 0:
            status = FolderTaskStatus.SKIPPED
            error_message = EMPTY_FOLDER_MESSAGE
        tasks.append(
            FolderTask(
                local_name=entry.name,
                local_path=str(entry),
                file_count=file_count,
                total_size=total_size,
                status=status,
                error_message=error_message,
            )
        )
    return tasks
