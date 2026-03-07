from pathlib import Path

from quark_uploader.models import FolderTaskStatus
from quark_uploader.services.scanner import EMPTY_FOLDER_MESSAGE, scan_first_level_subfolders


def test_scan_first_level_subfolders_ignores_root_files(tmp_path: Path):
    (tmp_path / "root.txt").write_text("x", encoding="utf-8")
    lesson = tmp_path / "lesson-a"
    lesson.mkdir()
    (lesson / "video.mp4").write_text("hello", encoding="utf-8")

    tasks = scan_first_level_subfolders(tmp_path)

    assert [task.local_name for task in tasks] == ["lesson-a"]


def test_scan_first_level_subfolders_collects_nested_stats(tmp_path: Path):
    lesson = tmp_path / "lesson-b"
    nested = lesson / "part-1"
    nested.mkdir(parents=True)
    (nested / "a.txt").write_text("1234", encoding="utf-8")
    (nested / "b.txt").write_text("12", encoding="utf-8")

    task = scan_first_level_subfolders(tmp_path)[0]

    assert task.file_count == 2
    assert task.total_size == 6


def test_scan_first_level_subfolders_marks_empty_folder_as_skipped(tmp_path: Path):
    empty_folder = tmp_path / "empty"
    empty_folder.mkdir()

    task = scan_first_level_subfolders(tmp_path)[0]

    assert task.status is FolderTaskStatus.SKIPPED
    assert task.error_message == EMPTY_FOLDER_MESSAGE
