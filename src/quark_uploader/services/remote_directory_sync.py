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
        self._directory_cache: dict[str, list[dict]] = {}

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

    def _list_directory_cached(self, parent_fid: str) -> list[dict]:
        if parent_fid not in self._directory_cache:
            payload = self.file_api.list_directory(parent_fid)
            self._directory_cache[parent_fid] = list(payload.get("data", {}).get("list", []))
        return self._directory_cache[parent_fid]

    def _ensure_child_directory(self, parent_fid: str, folder_name: str) -> str:
        for item in self._list_directory_cached(parent_fid):
            if item.get("dir") and str(item.get("file_name") or item.get("title") or "") == folder_name:
                return str(item.get("fid"))
        created = self.file_api.create_directory(parent_fid, folder_name)
        created_fid = str(created.get("data", {}).get("fid", ""))
        if created_fid:
            self._directory_cache.setdefault(parent_fid, []).append({"fid": created_fid, "file_name": folder_name, "dir": True})
            self._directory_cache.setdefault(created_fid, [])
        return created_fid
