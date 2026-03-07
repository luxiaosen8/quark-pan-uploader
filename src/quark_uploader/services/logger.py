from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path


class StructuredLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, stage: str, folder_name: str, message: str, **extra: object) -> None:
        payload = {
            "time": datetime.now(UTC).isoformat(),
            "level": level,
            "stage": stage,
            "folder_name": folder_name,
            "message": message,
            "extra": extra,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
