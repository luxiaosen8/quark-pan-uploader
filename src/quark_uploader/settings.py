from __future__ import annotations

from pydantic import BaseModel


DEFAULT_JOB_CONCURRENCY = 2
MAX_JOB_CONCURRENCY = 4
DEFAULT_FILE_CONCURRENCY = 2
MAX_FILE_CONCURRENCY = 6
DEFAULT_PART_CONCURRENCY = 3
MAX_PART_CONCURRENCY = 6
DEFAULT_UI_UPDATE_INTERVAL_MS = 120
MIN_UI_UPDATE_INTERVAL_MS = 50
MAX_UI_UPDATE_INTERVAL_MS = 1000


def _clamp_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return default
    if candidate < minimum or candidate > maximum:
        return default
    return candidate


def _clamp_float(
    value: object, default: float, minimum: float, maximum: float
) -> float:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return default
    if candidate < minimum or candidate > maximum:
        return default
    return candidate


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
    job_concurrency: int = DEFAULT_JOB_CONCURRENCY
    file_concurrency: int = DEFAULT_FILE_CONCURRENCY
    part_concurrency: int = DEFAULT_PART_CONCURRENCY
    ui_update_interval_ms: int = DEFAULT_UI_UPDATE_INTERVAL_MS

    def model_post_init(self, __context) -> None:
        self.request_timeout_seconds = _clamp_int(
            self.request_timeout_seconds, 30, 1, 600
        )
        self.file_retry_limit = _clamp_int(self.file_retry_limit, 1, 0, 10)
        self.share_retry_limit = _clamp_int(self.share_retry_limit, 1, 0, 10)
        self.share_poll_max_retries = _clamp_int(
            self.share_poll_max_retries, 10, 1, 120
        )
        self.retry_backoff_base_seconds = _clamp_float(
            self.retry_backoff_base_seconds, 0.5, 0.0, 60.0
        )
        self.share_poll_interval_seconds = _clamp_float(
            self.share_poll_interval_seconds, 0.5, 0.0, 30.0
        )
        self.job_concurrency = _clamp_int(
            self.job_concurrency, DEFAULT_JOB_CONCURRENCY, 1, MAX_JOB_CONCURRENCY
        )
        self.file_concurrency = _clamp_int(
            self.file_concurrency, DEFAULT_FILE_CONCURRENCY, 1, MAX_FILE_CONCURRENCY
        )
        self.part_concurrency = _clamp_int(
            self.part_concurrency, DEFAULT_PART_CONCURRENCY, 1, MAX_PART_CONCURRENCY
        )
        self.ui_update_interval_ms = _clamp_int(
            self.ui_update_interval_ms,
            DEFAULT_UI_UPDATE_INTERVAL_MS,
            MIN_UI_UPDATE_INTERVAL_MS,
            MAX_UI_UPDATE_INTERVAL_MS,
        )
