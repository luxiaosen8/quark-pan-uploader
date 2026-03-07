from __future__ import annotations

from pydantic import BaseModel

from quark_uploader.services.share_policy import build_share_payload


class ShareCreationResult(BaseModel):
    share_id: str
    share_url: str


class QuarkShareService:
    def __init__(self, share_api, task_api, result_writer=None, max_retries: int = 10) -> None:
        self.share_api = share_api
        self.task_api = task_api
        self.result_writer = result_writer
        self.max_retries = max_retries

    def create_share_for_folder(self, fid: str, title: str) -> ShareCreationResult:
        create_result = self.share_api.create_share(build_share_payload(fid=fid, title=title))
        task_id = create_result.get("data", {}).get("task_id", "")
        share_id = ""
        for retry_index in range(self.max_retries):
            task_payload = self.task_api.get_task(task_id, retry_index=retry_index)
            task_data = task_payload.get("data", {})
            if task_data.get("status") == 2:
                share_id = task_data.get("share_id", "")
                break
            if task_data.get("status") == 3:
                raise RuntimeError(task_data.get("message", "分享创建失败"))
        if not share_id:
            raise RuntimeError("分享创建超时")
        detail_result = self.share_api.get_share_detail(share_id)
        detail_data = detail_result.get("data", {})
        share_url = detail_data.get("share_url") or detail_data.get("url") or ""
        result = ShareCreationResult(share_id=share_id, share_url=share_url)
        if self.result_writer is not None and share_url:
            self.result_writer.append_share_url(share_url)
        return result
