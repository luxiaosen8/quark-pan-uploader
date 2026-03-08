from __future__ import annotations

from pydantic import BaseModel


class AppSettings(BaseModel):
    output_dir: str = "output"
    save_cookie: bool = True
    persisted_cookie: str = ""
    request_timeout_seconds: int = 30
    file_retry_limit: int = 1
    share_retry_limit: int = 1
    share_poll_max_retries: int = 10
    retry_backoff_base_seconds: float = 0.5
    share_poll_interval_seconds: float = 0.5
    debug_mode: bool = False
