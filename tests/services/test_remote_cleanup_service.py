from quark_uploader.services.remote_cleanup_service import RemoteCleanupService


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


def test_remote_cleanup_service_deletes_only_matching_test_directories():
    api = FakeFileApi()
    service = RemoteCleanupService(api)

    result = service.cleanup_test_directories()

    assert api.deleted == ["a", "c"]
    assert result.deleted_names == ["codex-small-111", "codex-large-222"]
