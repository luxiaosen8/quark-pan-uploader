from __future__ import annotations

from pydantic import BaseModel, Field


class RemoteCleanupResult(BaseModel):
    deleted_names: list[str] = Field(default_factory=list)


class RemoteCleanupService:
    def __init__(self, file_api, prefixes: tuple[str, ...] = ("codex-small-", "codex-large-")) -> None:
        self.file_api = file_api
        self.prefixes = prefixes

    def cleanup_test_directories(self) -> RemoteCleanupResult:
        payload = self.file_api.list_directory("0")
        matched = []
        for item in payload.get("data", {}).get("list", []):
            name = str(item.get("file_name") or "")
            if item.get("dir") and any(name.startswith(prefix) for prefix in self.prefixes):
                matched.append((str(item.get("fid")), name))
        if matched:
            self.file_api.delete_files([fid for fid, _ in matched])
        return RemoteCleanupResult(deleted_names=[name for _, name in matched])
