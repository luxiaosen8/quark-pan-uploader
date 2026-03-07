from pathlib import Path

from quark_uploader.services.result_writer import ResultWriter
from quark_uploader.services.share_service import QuarkShareService


class FakeShareApi:
    def __init__(self):
        self.calls = []

    def create_share(self, payload):
        self.calls.append(("create_share", payload))
        return {"data": {"task_id": "task-1"}}

    def get_share_detail(self, share_id: str):
        self.calls.append(("get_share_detail", {"share_id": share_id}))
        return {"data": {"share_url": "https://pan.quark.cn/s/abc123", "share_id": share_id}}


class FakeTaskApi:
    def __init__(self):
        self.calls = []

    def get_task(self, task_id: str, retry_index: int = 0):
        self.calls.append((task_id, retry_index))
        return {"data": {"status": 2, "share_id": "share-1"}}


def test_quark_share_service_creates_share_polls_task_and_writes_link(tmp_path: Path):
    writer = ResultWriter(tmp_path)
    service = QuarkShareService(share_api=FakeShareApi(), task_api=FakeTaskApi(), result_writer=writer)

    result = service.create_share_for_folder(fid="root-fid", title="课程A")

    assert result.share_id == "share-1"
    assert result.share_url == "https://pan.quark.cn/s/abc123"
    assert (tmp_path / "share_links.txt").read_text(encoding="utf-8").splitlines() == ["https://pan.quark.cn/s/abc123"]
