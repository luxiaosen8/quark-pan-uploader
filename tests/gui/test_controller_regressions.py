from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import FolderTaskStatus


class FakeSyncExecutor:
    def __init__(self) -> None:
        self.executed_jobs: list[str] = []

    def execute_job(self, job, status_callback=None, **kwargs):
        self.executed_jobs.append(job.local_name)
        if status_callback is not None:
            status_callback(FolderTaskStatus.UPLOADING.value, retry_count=0)
            status_callback(
                FolderTaskStatus.COMPLETED.value,
                share_url=f"https://share/{job.local_name}",
                retry_count=0,
            )
        return SimpleNamespace(
            status=FolderTaskStatus.COMPLETED.value,
            share_url=f"https://share/{job.local_name}",
            retry_count=0,
            uploaded_files=max(1, job.file_count),
        )


def _build_controller(
    window: MainWindow, executor: FakeSyncExecutor
) -> MainWindowController:
    return MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: None,
        login_dialog_factory=lambda validator, parent=None: None,
        upload_executor_factory=lambda **kwargs: executor,
        use_async_upload=False,
    )


def _prepare_remote_target(window: MainWindow) -> None:
    window.remote_folder_id = "target-root"
    window.set_selected_remote_folder("root / target")


def test_single_file_upload_regression(qtbot, tmp_path: Path) -> None:
    file_path = tmp_path / "single.txt"
    file_path.write_text("hello", encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)
    executor = FakeSyncExecutor()
    controller = _build_controller(window, executor)
    _prepare_remote_target(window)

    controller.apply_single_target(str(file_path))
    controller.start_upload()

    assert executor.executed_jobs == ["single.txt"]
    assert window.task_table.item(0, 3).text() == FolderTaskStatus.COMPLETED.value
    assert window.task_table.item(0, 4).text() == "https://share/single.txt"


def test_single_folder_upload_regression(qtbot, tmp_path: Path) -> None:
    folder_path = tmp_path / "album"
    folder_path.mkdir()
    (folder_path / "a.txt").write_text("a", encoding="utf-8")
    (folder_path / "b.txt").write_text("b", encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)
    executor = FakeSyncExecutor()
    controller = _build_controller(window, executor)
    _prepare_remote_target(window)

    controller.apply_single_target(str(folder_path))
    controller.start_upload()

    assert executor.executed_jobs == ["album"]
    assert window.task_table.item(0, 1).text() == "2"
    assert window.task_table.item(0, 3).text() == FolderTaskStatus.COMPLETED.value


def test_batch_subfolder_upload_regression(qtbot, tmp_path: Path) -> None:
    root = tmp_path / "batch-root"
    root.mkdir()
    first = root / "first"
    second = root / "second"
    first.mkdir()
    second.mkdir()
    (first / "1.txt").write_text("1", encoding="utf-8")
    (second / "2.txt").write_text("2", encoding="utf-8")
    window = MainWindow()
    qtbot.addWidget(window)
    executor = FakeSyncExecutor()
    controller = _build_controller(window, executor)
    _prepare_remote_target(window)

    controller.apply_local_root(str(root))
    controller.start_upload()

    assert executor.executed_jobs == ["first", "second"]
    assert window.task_table.rowCount() == 2
    assert window.task_table.item(0, 3).text() == FolderTaskStatus.COMPLETED.value
    assert window.task_table.item(1, 3).text() == FolderTaskStatus.COMPLETED.value
