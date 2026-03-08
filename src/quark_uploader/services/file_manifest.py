from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from quark_uploader.models import FolderTask, TaskSourceType


class LocalFileEntry(BaseModel):
    local_name: str
    absolute_path: str
    relative_path: str
    size_bytes: int


def build_folder_file_manifest(task: FolderTask) -> list[LocalFileEntry]:
    folder = Path(task.local_path)
    entries: list[LocalFileEntry] = []
    for file_path in sorted((path for path in folder.rglob("*") if path.is_file()), key=lambda p: p.relative_to(folder).as_posix()):
        entries.append(
            LocalFileEntry(
                local_name=task.local_name,
                absolute_path=str(file_path),
                relative_path=file_path.relative_to(folder).as_posix(),
                size_bytes=file_path.stat().st_size,
            )
        )
    return entries


def build_task_file_manifest(task: FolderTask) -> list[LocalFileEntry]:
    source_path = Path(task.local_path)
    if task.source_type is TaskSourceType.FILE:
        return [
            LocalFileEntry(
                local_name=task.local_name,
                absolute_path=str(source_path),
                relative_path=source_path.name,
                size_bytes=source_path.stat().st_size,
            )
        ]
    return build_folder_file_manifest(task)
