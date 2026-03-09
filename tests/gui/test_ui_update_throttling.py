from __future__ import annotations

from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import FolderTask, FolderTaskStatus, TaskSourceType


def test_main_window_batches_log_updates(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.append_log("line-1")
    window.append_log("line-2")
    window.append_log("line-3")

    assert "line-1" not in window.log_output.toPlainText()
    qtbot.wait(180)
    output = window.log_output.toPlainText()
    assert "line-1" in output
    assert "line-3" in output


def test_update_task_status_reuses_existing_table_items(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.populate_task_table(
        [
            FolderTask(
                local_name="demo",
                local_path="demo",
                file_count=1,
                total_size=1,
                status=FolderTaskStatus.PENDING,
                source_type=TaskSourceType.FILE,
            )
        ]
    )

    status_item = window.task_table.item(0, 3)
    retry_item = window.task_table.item(0, 5)

    window.update_task_status("demo", FolderTaskStatus.UPLOADING.value, retry_count=1)

    assert window.task_table.item(0, 3) is status_item
    assert window.task_table.item(0, 5) is retry_item
    assert status_item.text() == FolderTaskStatus.UPLOADING.value
    assert retry_item.text() == "1"
