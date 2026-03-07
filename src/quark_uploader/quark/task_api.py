from __future__ import annotations

from quark_uploader.quark.session import QuarkSession


class QuarkTaskApi:
    def __init__(self, session: QuarkSession) -> None:
        self.session = session

    def get_task(self, task_id: str, retry_index: int = 0) -> dict:
        return self.session.request(
            "GET",
            "/1/clouddrive/task",
            params={"task_id": task_id, "retry_index": retry_index},
        )
