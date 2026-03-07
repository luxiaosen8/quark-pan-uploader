from quark_uploader.models import FolderTask
from quark_uploader.services.upload_workflow import UploadExecutionPlan, build_upload_plan


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
