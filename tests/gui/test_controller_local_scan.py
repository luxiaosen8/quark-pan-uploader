from pathlib import Path

from quark_uploader.app import create_app
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import AccountSummary, DriveRefreshResult, RemoteFolderNode


class FakeRefreshService:
    def refresh(self):
        return DriveRefreshResult(
            account=AccountSummary(nickname="测试用户", total_bytes=1000, used_bytes=400, available_bytes=600),
            root_nodes=[RemoteFolderNode(fid="folder-1", name="资料", parent_fid="0", has_children=False)],
        )

    def load_children(self, parent_fid: str):
        return []


class FakeLoginDialog:
    cookie_string = None

    def exec(self):
        return 0


def test_controller_select_local_folder_scans_first_level_subfolders(qtbot, tmp_path: Path):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    (tmp_path / "root-file.txt").write_text("x", encoding="utf-8")
    lesson = tmp_path / "课程A"
    lesson.mkdir()
    (lesson / "video.mp4").write_text("demo", encoding="utf-8")

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog(),
    )

    controller.apply_local_root(str(tmp_path))

    assert window.local_root == str(tmp_path)
    assert window.task_table.rowCount() == 1
    assert window.task_table.item(0, 0).text() == "课程A"
    assert "已扫描 1 个一级子文件夹" in window.log_output.toPlainText()


def test_controller_start_upload_builds_execution_plan_with_manifest(qtbot, tmp_path: Path):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    lesson = tmp_path / "课程A"
    nested = lesson / "chapter1"
    nested.mkdir(parents=True)
    (lesson / "cover.txt").write_text("12", encoding="utf-8")
    (nested / "video.mp4").write_text("1234", encoding="utf-8")

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog(),
    )
    window.cookie_valid = True
    window.remote_folder_id = "folder-1"
    controller.apply_local_root(str(tmp_path))

    controller.start_upload()

    assert controller.current_upload_plan is not None
    job = controller.current_upload_plan.jobs[0]
    assert controller.current_upload_plan.remote_parent_fid == "folder-1"
    assert job.file_entries[0].relative_path == "chapter1/video.mp4"
    assert job.file_entries[1].relative_path == "cover.txt"
    assert job.remote_dir_requirements[0].relative_dir == "chapter1"
    assert window.task_table.item(0, 3).text() == "uploading"
    assert "已创建上传计划，共 1 个子文件夹任务" in window.log_output.toPlainText()


class FakeExecutor:
    def __init__(self):
        self.jobs = []

    def execute_job(self, job):
        self.jobs.append(job.local_name)
        return type("Result", (), {"root_folder_fid": "root-fid", "uploaded_files": len(job.file_entries)})()


def test_controller_start_upload_can_execute_with_injected_executor(qtbot, tmp_path: Path):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    lesson = tmp_path / "课程A"
    lesson.mkdir()
    (lesson / "cover.txt").write_text("12", encoding="utf-8")

    executor = FakeExecutor()
    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog(),
        upload_executor_factory=lambda: executor,
    )
    window.cookie_valid = True
    window.remote_folder_id = "folder-1"
    controller.apply_local_root(str(tmp_path))

    controller.start_upload()

    assert executor.jobs == ["课程A"]
    assert window.task_table.item(0, 3).text() == "completed"
    assert "上传骨架执行完成：课程A (1 文件)" in window.log_output.toPlainText()



class FailingExecutor:
    def execute_job(self, job):
        raise RuntimeError("upload failed")


def test_controller_marks_task_failed_when_executor_raises(qtbot, tmp_path: Path):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    lesson = tmp_path / "课程A"
    lesson.mkdir()
    (lesson / "cover.txt").write_text("12", encoding="utf-8")

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog(),
        upload_executor_factory=lambda: FailingExecutor(),
    )
    window.cookie_valid = True
    window.remote_folder_id = "folder-1"
    controller.apply_local_root(str(tmp_path))

    controller.start_upload()

    assert window.task_table.item(0, 3).text() == "failed"
    assert "上传失败：课程A -> upload failed" in window.log_output.toPlainText()



class ShareExecutor:
    def execute_job(self, job):
        return type("Result", (), {"uploaded_files": len(job.file_entries), "share_url": "https://pan.quark.cn/s/abc123"})()


def test_controller_updates_share_link_when_executor_returns_share(qtbot, tmp_path: Path):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    lesson = tmp_path / "课程A"
    lesson.mkdir()
    (lesson / "cover.txt").write_text("12", encoding="utf-8")

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog(),
        upload_executor_factory=lambda: ShareExecutor(),
    )
    window.cookie_valid = True
    window.remote_folder_id = "folder-1"
    controller.apply_local_root(str(tmp_path))

    controller.start_upload()

    assert window.task_table.item(0, 3).text() == "completed"
    assert window.task_table.item(0, 4).text() == "https://pan.quark.cn/s/abc123"



class FakeCleanupResult:
    deleted_names = ["codex-small-111", "codex-large-222"]


class FakeCleanupService:
    def cleanup_test_directories(self):
        return FakeCleanupResult()


def test_controller_updates_progress_and_retry_count_when_executor_returns_retrying_result(qtbot, tmp_path: Path):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    lesson = tmp_path / "课程A"
    lesson.mkdir()
    (lesson / "cover.txt").write_text("12", encoding="utf-8")

    class RetryExecutor:
        def execute_job(self, job):
            return type("Result", (), {"uploaded_files": 1, "share_url": "", "retry_count": 2, "status": "completed"})()

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success, parent=None: FakeLoginDialog(),
        upload_executor_factory=lambda: RetryExecutor(),
    )
    window.cookie_valid = True
    window.remote_folder_id = "folder-1"
    controller.apply_local_root(str(tmp_path))

    controller.start_upload()

    assert window.task_table.item(0, 5).text() == "2"
    assert window.overall_progress_bar.value() == 100
    assert "任务进度：1/1，失败 0" == window.progress_summary_label.text()


def test_controller_can_cleanup_remote_test_directories(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success, parent=None: FakeLoginDialog(),
        cleanup_service_factory=lambda: FakeCleanupService(),
    )

    controller.cleanup_remote_test_directories()

    assert "已清理测试目录：2 个" in window.log_output.toPlainText()
