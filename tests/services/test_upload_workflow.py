from quark_uploader.models import FolderTask, FolderTaskStatus
from quark_uploader.services.file_manifest import LocalFileEntry
from quark_uploader.services.remote_folder_plan import RemoteFolderRequirement
from quark_uploader.services.upload_workflow import UploadExecutionPlan, UploadJob, build_upload_plan


def test_build_upload_plan_creates_one_job_per_folder_task():
    plan = build_upload_plan(
        remote_parent_fid="remote-root",
        tasks=[
            FolderTask(local_name="课程A", local_path="C:/A", file_count=2, total_size=10),
            FolderTask(local_name="课程B", local_path="C:/B", file_count=1, total_size=5),
        ],
    )

    assert isinstance(plan, UploadExecutionPlan)
    assert plan.remote_parent_fid == "remote-root"
    assert [job.local_name for job in plan.jobs] == ["课程A", "课程B"]
    assert plan.total_files == 3


def test_build_upload_plan_can_attach_manifest_and_remote_dirs():
    job = UploadJob(
        local_name="课程A",
        local_path="C:/A",
        file_count=2,
        total_size=10,
        remote_parent_fid="remote-root",
        file_entries=[
            LocalFileEntry(local_name="课程A", absolute_path="C:/A/cover.txt", relative_path="cover.txt", size_bytes=2),
        ],
        remote_dir_requirements=[
            RemoteFolderRequirement(local_name="课程A", relative_dir="chapter1", remote_parent_fid="remote-root"),
        ],
    )

    assert job.file_entries[0].relative_path == "cover.txt"
    assert job.remote_dir_requirements[0].relative_dir == "chapter1"


def test_build_upload_plan_excludes_skipped_or_empty_tasks():
    plan = build_upload_plan(
        remote_parent_fid="remote-root",
        tasks=[
            FolderTask(local_name="空目录", local_path="C:/empty", file_count=0, total_size=0, status=FolderTaskStatus.SKIPPED),
            FolderTask(local_name="课程A", local_path="C:/A", file_count=1, total_size=5),
        ],
    )

    assert [job.local_name for job in plan.jobs] == ["课程A"]
