from __future__ import annotations

from pydantic import BaseModel, Field

from quark_uploader.models import FolderTask


class UploadJob(BaseModel):
    local_name: str
    local_path: str
    file_count: int = 0
    total_size: int = 0
    remote_parent_fid: str


class UploadExecutionPlan(BaseModel):
    remote_parent_fid: str
    jobs: list[UploadJob] = Field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0


def build_upload_plan(remote_parent_fid: str, tasks: list[FolderTask]) -> UploadExecutionPlan:
    jobs = [
        UploadJob(
            local_name=task.local_name,
            local_path=task.local_path,
            file_count=task.file_count,
            total_size=task.total_size,
            remote_parent_fid=remote_parent_fid,
        )
        for task in tasks
    ]
    return UploadExecutionPlan(
        remote_parent_fid=remote_parent_fid,
        jobs=jobs,
        total_files=sum(job.file_count for job in jobs),
        total_bytes=sum(job.total_size for job in jobs),
    )
