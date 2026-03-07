from pathlib import Path

from quark_uploader.models import FolderTask
from quark_uploader.services.file_manifest import LocalFileEntry, build_folder_file_manifest


def test_build_folder_file_manifest_collects_recursive_files(tmp_path: Path):
    lesson = tmp_path / "课程A"
    nested = lesson / "chapter1"
    nested.mkdir(parents=True)
    (lesson / "cover.txt").write_text("12", encoding="utf-8")
    (nested / "video.mp4").write_text("1234", encoding="utf-8")

    entries = build_folder_file_manifest(FolderTask(local_name="课程A", local_path=str(lesson)))

    assert [entry.relative_path for entry in entries] == ["chapter1/video.mp4", "cover.txt"]
    assert all(isinstance(entry, LocalFileEntry) for entry in entries)
    assert sum(entry.size_bytes for entry in entries) == 6
