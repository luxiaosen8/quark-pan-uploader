from __future__ import annotations

from time import sleep

from pydantic import BaseModel

from quark_uploader.services.cancellation import UploadCancellationToken
from quark_uploader.services.secrets import mask_share_url
from quark_uploader.services.share_policy import build_share_payload


class ShareCreationResult(BaseModel):
    share_id: str
    share_url: str


class QuarkShareService:
    def __init__(
        self,
        share_api,
        task_api,
        result_writer=None,
        max_retries: int = 10,
        poll_interval_seconds: float = 0.0,
        sleep_fn=sleep,
        logger=None,
    ) -> None:
        self.share_api = share_api
        self.task_api = task_api
        self.result_writer = result_writer
        self.max_retries = max_retries
        self.poll_interval_seconds = poll_interval_seconds
        self.sleep_fn = sleep_fn
        self.logger = logger

    def _log(self, message: str) -> None:
        if self.logger is not None:
            self.logger(message)

    def create_share_for_item(self, fid: str, title: str, cancel_token: UploadCancellationToken | None = None) -> ShareCreationResult:
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        self._log(f"[DEBUG] 开始创建分享：title={title} fid={fid}")
        create_result = self.share_api.create_share(build_share_payload(fid=fid, title=title))
        task_id = create_result.get("data", {}).get("task_id", "")
        self._log(f"[DEBUG] 分享任务已创建：task_id={task_id}")
        share_id = ""
        for retry_index in range(self.max_retries):
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            task_payload = self.task_api.get_task(task_id, retry_index=retry_index)
            task_data = task_payload.get("data", {})
            self._log(f"[DEBUG] 分享任务轮询：retry={retry_index} status={task_data.get('status')}")
            if task_data.get("status") == 2:
                share_id = task_data.get("share_id", "")
                self._log(f"[DEBUG] 分享轮询成功：share_id={share_id}")
                break
            if task_data.get("status") == 3:
                raise RuntimeError(task_data.get("message", "分享创建失败"))
            if retry_index < self.max_retries - 1 and self.poll_interval_seconds > 0:
                self.sleep_fn(self.poll_interval_seconds)
        if not share_id:
            raise RuntimeError("分享创建超时")
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        detail_result = self.share_api.get_share_detail(share_id)
        detail_data = detail_result.get("data", {})
        share_url = detail_data.get("share_url") or detail_data.get("url") or ""
        result = ShareCreationResult(share_id=share_id, share_url=share_url)
        if self.result_writer is not None and share_url:
            self.result_writer.append_share_url(share_url)
            self._log(f"[DEBUG] 分享链接已写入：share_url={mask_share_url(share_url)}")
        return result

    def create_share_for_folder(self, fid: str, title: str, cancel_token: UploadCancellationToken | None = None) -> ShareCreationResult:
        return self.create_share_for_item(fid=fid, title=title, cancel_token=cancel_token)
