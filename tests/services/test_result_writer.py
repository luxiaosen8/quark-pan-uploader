from pathlib import Path
import csv
import json

from quark_uploader.services.logger import StructuredLogger
from quark_uploader.services.result_writer import ResultWriter


def test_result_writer_appends_urls_line_by_line(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-1")
    writer.append_share_url("https://example.com/a")
    writer.append_share_url("https://example.com/b")

    content = (tmp_path / "share_links.txt").read_text(encoding="utf-8").splitlines()
    assert content == ["https://example.com/a", "https://example.com/b"]


def test_result_writer_writes_share_result_jsonl_and_csv(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-1")
    writer.append_share_result({
        "run_id": "run-1",
        "local_folder_name": "课程A",
        "status": "completed",
        "share_url": "https://example.com/a",
        "retry_count": 1,
        "error_message": "",
    })

    jsonl_rows = (tmp_path / "runs" / "run-1" / "share_results.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(jsonl_rows[0])
    assert payload["local_folder_name"] == "课程A"
    assert payload["retry_count"] == 1

    with (tmp_path / "runs" / "run-1" / "share_results.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["status"] == "completed"
    assert rows[0]["share_url"] == "https://example.com/a"


def test_result_writer_writes_event_jsonl(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-1")
    writer.append_event("INFO", "upload", "开始上传", folder_name="课程A", file_name="a.txt")

    rows = (tmp_path / "runs" / "run-1" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    assert payload["level"] == "INFO"
    assert payload["phase"] == "upload"
    assert payload["folder_name"] == "课程A"


def test_structured_logger_writes_jsonl_records(tmp_path: Path):
    logger = StructuredLogger(tmp_path / "logs.jsonl")
    logger.log("INFO", "scan", "folder-a", "started")

    rows = (tmp_path / "logs.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    assert payload["level"] == "INFO"
    assert payload["stage"] == "scan"
    assert payload["folder_name"] == "folder-a"



def test_result_writer_event_file_created_even_with_multiple_entries(tmp_path: Path):
    writer = ResultWriter(tmp_path, run_id="run-2")
    writer.append_event("INFO", "job", "start", folder_name="课程A")
    writer.append_event("INFO", "job", "done", folder_name="课程A")

    rows = (tmp_path / "runs" / "run-2" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
