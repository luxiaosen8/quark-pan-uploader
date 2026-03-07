from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from quark_uploader.models import FolderTask


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
