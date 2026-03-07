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
