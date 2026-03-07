from quark_uploader.models import FolderTask
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_folder_plan import build_remote_folder_requirements


def test_build_remote_folder_requirements_extracts_nested_directories_only_once():
    task = FolderTask(local_name="课程A", local_path="C:/课程A")
    entries = [
        LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/chapter1/video.mp4", relative_path="chapter1/video.mp4", size_bytes=10),
        LocalFileEntry(local_name="课程A", absolute_path="C:/课程A/chapter1/docs/readme.txt", relative_path="chapter1/docs/readme.txt", size_bytes=5),
    ]

    requirements = build_remote_folder_requirements(task, remote_parent_fid="remote-root", file_entries=entries)

    assert [item.relative_dir for item in requirements] == ["chapter1", "chapter1/docs"]
    assert all(item.remote_parent_fid == "remote-root" for item in requirements)
