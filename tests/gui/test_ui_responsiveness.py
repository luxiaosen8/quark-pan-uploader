from __future__ import annotations

from PySide6.QtCore import Qt

from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import FolderTask, FolderTaskStatus, TaskSourceType


def test_ui_remains_interactive_under_high_frequency_updates(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
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

    for index in range(120):
        window.append_log(f"log-{index}")
        window.update_task_status(
            "demo",
            FolderTaskStatus.UPLOADING.value
            if index < 119
            else FolderTaskStatus.COMPLETED.value,
            retry_count=index % 3,
        )
        window.set_current_action(f"当前动作：任务 {index}")

    qtbot.wait(200)
    qtbot.mouseClick(
        window.workspace_tabs.tabBar(),
        Qt.MouseButton.LeftButton,
        pos=window.workspace_tabs.tabBar().tabRect(2).center(),
    )
    assert window.workspace_tabs.currentIndex() == 2

    window.stop_button.setEnabled(True)
    clicked: list[bool] = []
    window.stop_button.clicked.connect(lambda: clicked.append(True))
    qtbot.mouseClick(window.stop_button, Qt.MouseButton.LeftButton)

    assert clicked == [True]
    assert "log-0" in window.log_output.toPlainText()
    assert window.task_table.item(0, 3).text() == FolderTaskStatus.COMPLETED.value
