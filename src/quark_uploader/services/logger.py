from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from quark_uploader.services.secrets import sanitize_log_extra


class StructuredLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def log(
        self, level: str, stage: str, folder_name: str, message: str, **extra: object
    ) -> None:
        payload = {
            "time": datetime.now(UTC).isoformat(),
            "level": level,
            "stage": stage,
            "folder_name": folder_name,
            "message": message,
            "extra": sanitize_log_extra(extra),
        }
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
