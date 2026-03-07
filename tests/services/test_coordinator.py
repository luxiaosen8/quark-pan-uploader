from quark_uploader.models import FolderTask, FolderTaskStatus
from quark_uploader.services.coordinator import mark_share_success


def test_mark_share_success_updates_status_and_url():
    task = FolderTask(local_name="lesson-a", local_path="C:/lesson-a")
    mark_share_success(task, "https://example.com/share")
    assert task.status is FolderTaskStatus.COMPLETED
    assert task.share_url == "https://example.com/share"
