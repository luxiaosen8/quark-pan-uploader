import csv
import json
from pathlib import Path

from quark_uploader.services.remote_cleanup_service import RemoteCleanupService
from quark_uploader.services.result_writer import ResultWriter


class FakeFileApi:
    def __init__(self):
        self.deleted = []

    def list_directory(self, parent_fid: str):
        return {
            "data": {
                "list": [
                    {"fid": "a", "file_name": "codex-small-111", "dir": True},
                    {"fid": "b", "file_name": "keep-me", "dir": True},
                    {"fid": "c", "file_name": "codex-large-222", "dir": True},
                ]
            }
        }

    def delete_files(self, file_ids: list[str]):
        self.deleted.extend(file_ids)
        return {"data": {"task_id": "cleanup-task"}}


class FailingFileApi(FakeFileApi):
    def delete_files(self, file_ids: list[str]):
        raise RuntimeError("delete failed")


def test_remote_cleanup_service_deletes_only_matching_test_directories():
    api = FakeFileApi()
    service = RemoteCleanupService(api)

    result = service.cleanup_test_directories()

    assert api.deleted == ["a", "c"]
    assert result.deleted_names == ["codex-small-111", "codex-large-222"]
    assert [entry.fid for entry in result.entries] == ["a", "c"]


def test_remote_cleanup_service_writes_cleanup_results(tmp_path: Path):
    api = FakeFileApi()
    writer = ResultWriter(tmp_path, run_id="cleanup-run")
    service = RemoteCleanupService(api, result_writer=writer)

    service.cleanup_test_directories()

    jsonl_rows = (tmp_path / "runs" / "cleanup-run" / "cleanup_results.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(jsonl_rows[0])
    assert payload["deleted_name"] == "codex-small-111"
    assert payload["status"] == "deleted"

    with (tmp_path / "runs" / "cleanup-run" / "cleanup_results.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[1]["deleted_name"] == "codex-large-222"


def test_remote_cleanup_service_records_delete_failures(tmp_path: Path):
    api = FailingFileApi()
    writer = ResultWriter(tmp_path, run_id="cleanup-run")
    service = RemoteCleanupService(api, result_writer=writer)

    result = service.cleanup_test_directories()

    assert result.deleted_names == []
    jsonl_rows = (tmp_path / "runs" / "cleanup-run" / "cleanup_results.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(jsonl_rows[0])
    assert payload["status"] == "failed"
    assert payload["error_message"] == "delete failed"
