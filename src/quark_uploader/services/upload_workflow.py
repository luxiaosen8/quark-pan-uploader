from __future__ import annotations

from pydantic import BaseModel, Field

from quark_uploader.models import FolderTask
from quark_uploader.services.file_manifest import LocalFileEntry, build_folder_file_manifest
from quark_uploader.services.remote_folder_plan import (
    RemoteFolderRequirement,
    build_remote_folder_requirements,
)


class UploadJob(BaseModel):
    local_name: str
    local_path: str
    file_count: int = 0
    total_size: int = 0
    remote_parent_fid: str
    file_entries: list[LocalFileEntry] = Field(default_factory=list)
    remote_dir_requirements: list[RemoteFolderRequirement] = Field(default_factory=list)


class UploadExecutionPlan(BaseModel):
    remote_parent_fid: str
    jobs: list[UploadJob] = Field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0


def build_upload_plan(remote_parent_fid: str, tasks: list[FolderTask]) -> UploadExecutionPlan:
    jobs: list[UploadJob] = []
    for task in tasks:
        if not task.can_execute:
            continue
        file_entries = build_folder_file_manifest(task)
        remote_dir_requirements = build_remote_folder_requirements(task, remote_parent_fid, file_entries)
        jobs.append(
            UploadJob(
                local_name=task.local_name,
                local_path=task.local_path,
                file_count=task.file_count,
                total_size=task.total_size,
                remote_parent_fid=remote_parent_fid,
                file_entries=file_entries,
                remote_dir_requirements=remote_dir_requirements,
            )
        )
    return UploadExecutionPlan(
        remote_parent_fid=remote_parent_fid,
        jobs=jobs,
        total_files=sum(job.file_count for job in jobs),
        total_bytes=sum(job.total_size for job in jobs),
    )
