from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import FolderTask, FolderTaskStatus


def test_main_window_has_local_folder_controls_and_task_table(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.select_local_folder_button.text() == "选择本地文件夹"
    assert window.task_table.columnCount() == 5


def test_main_window_populates_task_table(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_local_root("C:/素材")
    window.populate_task_table([
        FolderTask(local_name="课程A", local_path="C:/素材/课程A", file_count=2, total_size=1024, status=FolderTaskStatus.PENDING),
    ])

    assert "C:/素材" in window.local_root_label.text()
    assert window.task_table.rowCount() == 1
    assert window.task_table.item(0, 0).text() == "课程A"
    assert window.task_table.item(0, 3).text() == FolderTaskStatus.PENDING.value
