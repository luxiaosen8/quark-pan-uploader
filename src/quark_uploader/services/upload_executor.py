from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel

from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.upload_workflow import UploadJob


class UploadExecutionResult(BaseModel):
    root_folder_fid: str
    uploaded_files: int = 0


class UploadExecutionEngine:
    def __init__(self, directory_sync_service, uploader) -> None:
        self.directory_sync_service = directory_sync_service
        self.uploader = uploader

    def execute_job(self, job: UploadJob) -> UploadExecutionResult:
        resolved = self.directory_sync_service.ensure_job_directories(job)
        uploaded_files = 0
        for entry in job.file_entries:
            parent_fid = self._resolve_target_parent_fid(entry.relative_path, resolved)
            self.uploader.upload_file(entry, parent_fid)
            uploaded_files += 1
        return UploadExecutionResult(root_folder_fid=resolved.root_folder_fid, uploaded_files=uploaded_files)

    def _resolve_target_parent_fid(self, relative_path: str, resolved: ResolvedRemoteDirectory) -> str:
        parent_dir = PurePosixPath(relative_path).parent.as_posix()
        if parent_dir in {'.', ''}:
            return resolved.root_folder_fid
        return resolved.relative_dir_fids[parent_dir]
