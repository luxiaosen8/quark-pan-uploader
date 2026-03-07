from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path


class ResultWriter:
    def __init__(self, output_dir: Path, run_id: str | None = None) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = self.output_dir / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.share_links_path = self.output_dir / "share_links.txt"
        self.share_results_jsonl_path = self.run_dir / "share_results.jsonl"
        self.share_results_csv_path = self.run_dir / "share_results.csv"
        self.events_jsonl_path = self.run_dir / "events.jsonl"
        self.cleanup_results_jsonl_path = self.run_dir / "cleanup_results.jsonl"
        self.cleanup_results_csv_path = self.run_dir / "cleanup_results.csv"

    def append_share_url(self, url: str) -> None:
        with self.share_links_path.open("a", encoding="utf-8") as handle:
            handle.write(url + "\n")

    def append_share_result(self, record: dict) -> None:
        with self.share_results_jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        write_header = not self.share_results_csv_path.exists()
        with self.share_results_csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(record)


    def append_cleanup_result(self, record: dict) -> None:
        with self.cleanup_results_jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        write_header = not self.cleanup_results_csv_path.exists()
        with self.cleanup_results_csv_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(record)

    def append_event(self, level: str, phase: str, message: str, **extra: object) -> None:
        payload = {"time": datetime.now().isoformat(), "level": level, "phase": phase, "message": message, **extra}
        with self.events_jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
