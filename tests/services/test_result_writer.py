from pathlib import Path
import json

from quark_uploader.services.logger import StructuredLogger
from quark_uploader.services.result_writer import ResultWriter


def test_result_writer_appends_urls_line_by_line(tmp_path: Path):
    writer = ResultWriter(tmp_path)
    writer.append_share_url("https://example.com/a")
    writer.append_share_url("https://example.com/b")

    content = (tmp_path / "share_links.txt").read_text(encoding="utf-8").splitlines()
    assert content == ["https://example.com/a", "https://example.com/b"]


def test_structured_logger_writes_jsonl_records(tmp_path: Path):
    logger = StructuredLogger(tmp_path / "logs.jsonl")
    logger.log("INFO", "scan", "folder-a", "started")

    rows = (tmp_path / "logs.jsonl").read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    assert payload["level"] == "INFO"
    assert payload["stage"] == "scan"
    assert payload["folder_name"] == "folder-a"
