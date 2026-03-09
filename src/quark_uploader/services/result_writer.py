from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from quark_uploader.services.logger import StructuredLogger
from quark_uploader.services.secrets import sanitize_log_extra


class ResultWriter:
    _global_lock = Lock()

    def __init__(self, output_dir: Path, run_id: str | None = None) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = (
            run_id
            or f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')}_{uuid4().hex[:6]}"
        )
        self.run_dir = self.output_dir / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = self.output_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.share_links_path = self.output_dir / "share_links.txt"
        self.share_results_jsonl_path = self.run_dir / "share_results.jsonl"
        self.share_results_csv_path = self.run_dir / "share_results.csv"
        self.share_results_root_csv_path = self.output_dir / "share_results.csv"
        self.events_jsonl_path = self.run_dir / "events.jsonl"
        self.cleanup_results_jsonl_path = self.run_dir / "cleanup_results.jsonl"
        self.cleanup_results_csv_path = self.run_dir / "cleanup_results.csv"
        daily_log_path = self.logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        self.daily_logger = StructuredLogger(daily_log_path)
        self._lock = Lock()

    def append_share_url(self, url: str) -> None:
        with self._global_lock:
            with self.share_links_path.open("a", encoding="utf-8") as handle:
                handle.write(url + "\n")

    def append_share_result(self, record: dict) -> None:
        with self._global_lock:
            with self.share_results_jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._append_csv_record(self.share_results_csv_path, record)
            self._append_csv_record(self.share_results_root_csv_path, record)

    def append_cleanup_result(self, record: dict) -> None:
        with self._global_lock:
            with self.cleanup_results_jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._append_csv_record(self.cleanup_results_csv_path, record)

    def append_event(
        self, level: str, phase: str, message: str, **extra: object
    ) -> None:
        sanitized_extra = sanitize_log_extra(extra)
        payload = {
            "time": datetime.now().isoformat(),
            "level": level,
            "phase": phase,
            "message": message,
            **sanitized_extra,
        }
        with self._global_lock:
            with self.events_jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            daily_extra = dict(sanitized_extra)
            folder_name = str(daily_extra.pop("folder_name", ""))
            self.daily_logger.log(level, phase, folder_name, message, **daily_extra)

    def _append_csv_record(self, path: Path, record: dict) -> None:
        write_header = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(record)
