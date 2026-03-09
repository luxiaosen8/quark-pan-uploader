from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from time import sleep

from pydantic import BaseModel

from quark_uploader.models import FolderTaskStatus, TaskSourceType
from quark_uploader.services.cancellation import (
    UploadCancellationToken,
    UploadCancelled,
)
from quark_uploader.services.invoke import call_with_supported_kwargs
from quark_uploader.services.remote_directory_sync import ResolvedRemoteDirectory
from quark_uploader.services.upload_workflow import UploadJob


class UploadExecutionResult(BaseModel):
    root_folder_fid: str
    remote_item_fid: str = ""
    remote_item_type: str = TaskSourceType.FOLDER.value
    uploaded_files: int = 0
    share_url: str = ""
    share_id: str = ""
    retry_count: int = 0
    status: str = FolderTaskStatus.COMPLETED.value
    error_message: str = ""
    started_at: str = ""
    finished_at: str = ""


class UploadExecutionEngine:
    def __init__(
        self,
        directory_sync_service,
        uploader,
        share_service=None,
        result_writer=None,
        logger=None,
        file_retry_limit: int = 1,
        share_retry_limit: int = 1,
        retry_backoff_base_seconds: float = 0.0,
        sleep_fn=sleep,
    ) -> None:
        self.directory_sync_service = directory_sync_service
        self.uploader = uploader
        self.share_service = share_service
        self.result_writer = result_writer
        self.logger = logger
        self.file_retry_limit = file_retry_limit
        self.share_retry_limit = share_retry_limit
        self.retry_backoff_base_seconds = retry_backoff_base_seconds
        self.sleep_fn = sleep_fn

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger(message)

    def _append_event(
        self, level: str, phase: str, message: str, **extra: object
    ) -> None:
        if self.result_writer is not None:
            self.result_writer.append_event(level, phase, message, **extra)

    def _sleep_for_retry(self, attempt: int) -> None:
        delay = self.retry_backoff_base_seconds * attempt
        if delay > 0:
            self.sleep_fn(delay)

    def execute_job(
        self,
        job: UploadJob,
        cancel_token: UploadCancellationToken | None = None,
        progress_callback=None,
        status_callback=None,
    ) -> UploadExecutionResult:
        started_at = datetime.now().isoformat()
        retry_count = 0
        uploaded_files = 0
        root_folder_fid = ""
        remote_item_fid = ""
        self._append_event(
            "INFO",
            "job",
            "job start",
            folder_name=job.local_name,
            total_files=len(job.file_entries),
        )
        if status_callback is not None:
            status_callback(FolderTaskStatus.UPLOADING.value, retry_count=retry_count)
        try:
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            if job.source_type is TaskSourceType.FILE:
                resolved = ResolvedRemoteDirectory(
                    root_folder_fid=job.remote_parent_fid
                )
                root_folder_fid = job.remote_parent_fid
            else:
                resolved = self.directory_sync_service.ensure_job_directories(job)
                root_folder_fid = resolved.root_folder_fid
                remote_item_fid = root_folder_fid

            for entry in job.file_entries:
                parent_fid = self._resolve_target_parent_fid(
                    entry.relative_path, resolved
                )
                attempts = 0
                while True:
                    if cancel_token is not None:
                        cancel_token.raise_if_cancelled()
                    try:
                        upload_result = call_with_supported_kwargs(
                            self.uploader.upload_file,
                            entry,
                            parent_fid,
                            cancel_token=cancel_token,
                            progress_callback=progress_callback,
                        )
                        uploaded_files += 1
                        if job.source_type is TaskSourceType.FILE:
                            remote_item_fid = str(
                                upload_result.get("finish", {})
                                .get("data", {})
                                .get("fid", "")
                            )
                        if status_callback is not None:
                            status_callback(
                                FolderTaskStatus.UPLOADING.value,
                                retry_count=retry_count,
                            )
                        break
                    except UploadCancelled:
                        raise
                    except Exception as exc:
                        if attempts >= self.file_retry_limit:
                            raise
                        attempts += 1
                        retry_count += 1
                        if status_callback is not None:
                            status_callback(
                                FolderTaskStatus.RETRYING.value, retry_count=retry_count
                            )
                        self._log(
                            f"[WARN] 重试上传文件：job={job.local_name} file={entry.relative_path} attempt={attempts} error={exc}"
                        )
                        self._append_event(
                            "WARN",
                            "upload",
                            "retry file upload",
                            folder_name=job.local_name,
                            file_name=entry.relative_path,
                            attempt=attempts,
                            retry_count=retry_count,
                            error=str(exc),
                        )
                        self._sleep_for_retry(attempts)

            share_id = ""
            share_url = ""
            if self.share_service is not None:
                if status_callback is not None:
                    status_callback(
                        FolderTaskStatus.SHARING.value, retry_count=retry_count
                    )
                share_attempt = 0
                while True:
                    if cancel_token is not None:
                        cancel_token.raise_if_cancelled()
                    try:
                        share_target_fid = remote_item_fid or resolved.root_folder_fid
                        share_callable = (
                            self.share_service.create_share_for_item
                            if job.source_type is TaskSourceType.FILE
                            else self.share_service.create_share_for_folder
                        )
                        share_result = call_with_supported_kwargs(
                            share_callable,
                            fid=share_target_fid,
                            title=job.local_name,
                            cancel_token=cancel_token,
                        )
                        share_id = share_result.share_id
                        share_url = share_result.share_url
                        break
                    except UploadCancelled:
                        raise
                    except Exception as exc:
                        if share_attempt >= self.share_retry_limit:
                            raise
                        share_attempt += 1
                        retry_count += 1
                        if status_callback is not None:
                            status_callback(
                                FolderTaskStatus.RETRYING.value, retry_count=retry_count
                            )
                        self._log(
                            f"[WARN] 重试创建分享：folder={job.local_name} attempt={share_attempt} error={exc}"
                        )
                        self._append_event(
                            "WARN",
                            "share",
                            "retry share creation",
                            folder_name=job.local_name,
                            attempt=share_attempt,
                            retry_count=retry_count,
                            error=str(exc),
                        )
                        self._sleep_for_retry(share_attempt)
                        if status_callback is not None:
                            status_callback(
                                FolderTaskStatus.SHARING.value, retry_count=retry_count
                            )

            result = UploadExecutionResult(
                root_folder_fid=root_folder_fid,
                remote_item_fid=remote_item_fid or root_folder_fid,
                remote_item_type=job.source_type.value,
                uploaded_files=uploaded_files,
                share_id=share_id,
                share_url=share_url,
                retry_count=retry_count,
                status=FolderTaskStatus.COMPLETED.value,
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
            )
            self._append_event(
                "INFO",
                "job",
                "job completed",
                folder_name=job.local_name,
                uploaded_files=result.uploaded_files,
                share_url=result.share_url,
            )
            self._write_result(job, result)
            return result
        except UploadCancelled as exc:
            result = UploadExecutionResult(
                root_folder_fid=root_folder_fid,
                remote_item_fid=remote_item_fid or root_folder_fid,
                remote_item_type=job.source_type.value,
                uploaded_files=uploaded_files,
                retry_count=retry_count,
                status=FolderTaskStatus.STOPPED.value,
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
            )
            self._append_event(
                "WARN",
                "job",
                "job stopped",
                folder_name=job.local_name,
                error=result.error_message,
            )
            self._write_result(job, result)
            return result
        except Exception as exc:
            result = UploadExecutionResult(
                root_folder_fid=root_folder_fid,
                remote_item_fid=remote_item_fid or root_folder_fid,
                remote_item_type=job.source_type.value,
                uploaded_files=uploaded_files,
                retry_count=retry_count + 1,
                status=FolderTaskStatus.FAILED.value,
                error_message=str(exc),
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
            )
            self._append_event(
                "ERROR",
                "job",
                "job failed",
                folder_name=job.local_name,
                error=result.error_message,
            )
            self._write_result(job, result)
            raise

    def _write_result(self, job: UploadJob, result: UploadExecutionResult) -> None:
        if self.result_writer is None:
            return
        self.result_writer.append_share_result(
            {
                "run_id": self.result_writer.run_id,
                "local_folder_name": job.local_name,
                "local_folder_path": job.local_path,
                "remote_folder_name": job.local_name,
                "remote_parent_fid": job.remote_parent_fid,
                "remote_folder_fid": result.root_folder_fid,
                "remote_root_fid": result.root_folder_fid,
                "remote_item_fid": result.remote_item_fid,
                "remote_item_type": result.remote_item_type,
                "total_files": len(job.file_entries),
                "uploaded_files": result.uploaded_files,
                "share_id": result.share_id,
                "share_url": result.share_url,
                "status": result.status,
                "retry_count": result.retry_count,
                "error_message": result.error_message,
                "created_at": result.finished_at,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
            }
        )

    def _resolve_target_parent_fid(
        self, relative_path: str, resolved: ResolvedRemoteDirectory
    ) -> str:
        parent_dir = PurePosixPath(relative_path).parent.as_posix()
        if parent_dir in {".", ""}:
            return resolved.root_folder_fid
        return resolved.relative_dir_fids[parent_dir]
