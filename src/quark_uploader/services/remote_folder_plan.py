from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel

from quark_uploader.models import FolderTask
from quark_uploader.services.file_manifest import LocalFileEntry


class RemoteFolderRequirement(BaseModel):
    local_name: str
    relative_dir: str
    remote_parent_fid: str


def build_remote_folder_requirements(
    task: FolderTask,
    remote_parent_fid: str,
    file_entries: list[LocalFileEntry],
) -> list[RemoteFolderRequirement]:
    seen: set[str] = set()
    requirements: list[RemoteFolderRequirement] = []
    dir_candidates: list[str] = []
    for entry in file_entries:
        path = PurePosixPath(entry.relative_path)
        for depth in range(1, len(path.parts)):
            dir_candidates.append(PurePosixPath(*path.parts[:depth]).as_posix())
    for relative_dir in sorted(set(dir_candidates), key=lambda item: (item.count('/'), item)):
        if relative_dir in seen:
            continue
        seen.add(relative_dir)
        requirements.append(
            RemoteFolderRequirement(
                local_name=task.local_name,
                relative_dir=relative_dir,
                remote_parent_fid=remote_parent_fid,
            )
        )
    return requirements
