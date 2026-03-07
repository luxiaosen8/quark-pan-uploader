from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel

from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.upload_workflow import UploadJob


class UploadExecutionResult(BaseModel):
    root_folder_fid: str
    uploaded_files: int = 0
    share_url: str = ""
    share_id: str = ""


class UploadExecutionEngine:
    def __init__(self, directory_sync_service, uploader, share_service=None) -> None:
        self.directory_sync_service = directory_sync_service
        self.uploader = uploader
        self.share_service = share_service

    def execute_job(self, job: UploadJob) -> UploadExecutionResult:
        resolved = self.directory_sync_service.ensure_job_directories(job)
        uploaded_files = 0
        for entry in job.file_entries:
            parent_fid = self._resolve_target_parent_fid(entry.relative_path, resolved)
            self.uploader.upload_file(entry, parent_fid)
            uploaded_files += 1
        result = UploadExecutionResult(root_folder_fid=resolved.root_folder_fid, uploaded_files=uploaded_files)
        if self.share_service is not None:
            share_result = self.share_service.create_share_for_folder(fid=resolved.root_folder_fid, title=job.local_name)
            result.share_id = share_result.share_id
            result.share_url = share_result.share_url
        return result

    def _resolve_target_parent_fid(self, relative_path: str, resolved: ResolvedRemoteDirectory) -> str:
        parent_dir = PurePosixPath(relative_path).parent.as_posix()
        if parent_dir in {'.', ''}:
            return resolved.root_folder_fid
        return resolved.relative_dir_fids[parent_dir]
