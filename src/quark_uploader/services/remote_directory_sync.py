from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel, Field

from quark_uploader.services.upload_workflow import UploadJob


class ResolvedRemoteDirectory(BaseModel):
    root_folder_fid: str
    relative_dir_fids: dict[str, str] = Field(default_factory=dict)


class RemoteDirectorySyncService:
    def __init__(self, file_api) -> None:
        self.file_api = file_api

    def ensure_job_directories(self, job: UploadJob) -> ResolvedRemoteDirectory:
        root_fid = self._ensure_child_directory(job.remote_parent_fid, job.local_name)
        relative_dir_fids: dict[str, str] = {}
        for requirement in job.remote_dir_requirements:
            current_parent_fid = root_fid
            current_relative = ""
            for segment in PurePosixPath(requirement.relative_dir).parts:
                current_relative = segment if not current_relative else f"{current_relative}/{segment}"
                if current_relative in relative_dir_fids:
                    current_parent_fid = relative_dir_fids[current_relative]
                    continue
                current_parent_fid = self._ensure_child_directory(current_parent_fid, segment)
                relative_dir_fids[current_relative] = current_parent_fid
        return ResolvedRemoteDirectory(root_folder_fid=root_fid, relative_dir_fids=relative_dir_fids)

    def _ensure_child_directory(self, parent_fid: str, folder_name: str) -> str:
        payload = self.file_api.list_directory(parent_fid)
        for item in payload.get("data", {}).get("list", []):
            if item.get("dir") and str(item.get("file_name") or item.get("title") or "") == folder_name:
                return str(item.get("fid"))
        created = self.file_api.create_directory(parent_fid, folder_name)
        return str(created.get("data", {}).get("fid", ""))
