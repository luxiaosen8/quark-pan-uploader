from __future__ import annotations

from pathlib import Path

from quark_uploader.models import FolderTask, FolderTaskStatus, TaskSourceType

EMPTY_FOLDER_MESSAGE = "empty folder"


def _collect_folder_stats(folder: Path) -> tuple[int, int]:
    file_count = 0
    total_size = 0
    for file_path in folder.rglob("*"):
        if file_path.is_file():
            file_count += 1
            total_size += file_path.stat().st_size
    return file_count, total_size


def _build_folder_task(path: Path) -> FolderTask:
    file_count, total_size = _collect_folder_stats(path)
    status = FolderTaskStatus.PENDING
    error_message = None
    if file_count == 0:
        status = FolderTaskStatus.SKIPPED
        error_message = EMPTY_FOLDER_MESSAGE
    return FolderTask(
        local_name=path.name,
        local_path=str(path),
        file_count=file_count,
        total_size=total_size,
        status=status,
        source_type=TaskSourceType.FOLDER,
        error_message=error_message,
    )


def scan_first_level_subfolders(root: Path) -> list[FolderTask]:
    tasks: list[FolderTask] = []
    for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not entry.is_dir():
            continue
        tasks.append(_build_folder_task(entry))
    return tasks


def build_single_target_task(path: Path) -> FolderTask:
    if path.is_dir():
        return _build_folder_task(path)
    return FolderTask(
        local_name=path.name,
        local_path=str(path),
        file_count=1,
        total_size=path.stat().st_size,
        status=FolderTaskStatus.PENDING,
        source_type=TaskSourceType.FILE,
    )
