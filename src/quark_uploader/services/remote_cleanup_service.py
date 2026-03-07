from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RemoteCleanupEntry(BaseModel):
    fid: str
    name: str
    status: str
    error_message: str = ""


class RemoteCleanupResult(BaseModel):
    deleted_names: list[str] = Field(default_factory=list)
    entries: list[RemoteCleanupEntry] = Field(default_factory=list)


class RemoteCleanupService:
    def __init__(self, file_api, prefixes: tuple[str, ...] = ("codex-small-", "codex-large-"), result_writer=None, logger=None) -> None:
        self.file_api = file_api
        self.prefixes = prefixes
        self.result_writer = result_writer
        self.logger = logger

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger(message)

    def cleanup_test_directories(self) -> RemoteCleanupResult:
        payload = self.file_api.list_directory("0")
        matched = []
        for item in payload.get("data", {}).get("list", []):
            name = str(item.get("file_name") or "")
            if item.get("dir") and any(name.startswith(prefix) for prefix in self.prefixes):
                matched.append((str(item.get("fid")), name))
        entries: list[RemoteCleanupEntry] = []
        try:
            if matched:
                self.file_api.delete_files([fid for fid, _ in matched])
            for fid, name in matched:
                entry = RemoteCleanupEntry(fid=fid, name=name, status="deleted")
                entries.append(entry)
                self._write_cleanup_result(entry)
            return RemoteCleanupResult(deleted_names=[name for _, name in matched], entries=entries)
        except Exception as exc:
            for fid, name in matched:
                entry = RemoteCleanupEntry(fid=fid, name=name, status="failed", error_message=str(exc))
                entries.append(entry)
                self._write_cleanup_result(entry)
            return RemoteCleanupResult(deleted_names=[], entries=entries)

    def _write_cleanup_result(self, entry: RemoteCleanupEntry) -> None:
        if self.result_writer is None:
            return
        self.result_writer.append_cleanup_result({
            "run_id": self.result_writer.run_id,
            "deleted_name": entry.name,
            "deleted_fid": entry.fid,
            "status": entry.status,
            "error_message": entry.error_message,
            "finished_at": datetime.now().isoformat(),
        })
