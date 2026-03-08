from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import FolderTask, FolderTaskStatus


def test_main_window_has_progress_controls_and_task_table(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.select_local_folder_button.text() == "选择本地文件夹"
    assert window.open_output_button.text() == "打开输出目录"
    assert window.task_table.columnCount() == 6
    assert window.overall_progress_bar.value() == 0
    assert window.selected_remote_label.text() == "当前选择：未选择"


def test_main_window_populates_task_table_and_retry_count(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_local_root("C:/素材")
    window.populate_task_table([
        FolderTask(local_name="课程A", local_path="C:/素材/课程A", file_count=2, total_size=1024, status=FolderTaskStatus.PENDING),
    ])
    window.update_task_status("课程A", FolderTaskStatus.RETRYING.value, retry_count=2)
    window.set_progress_summary(completed=0, total=1, failed=0)
    window.set_current_action("当前文件：cover.txt")
    window.set_selected_remote_folder("资料 / 课程A")

    assert "C:/素材" in window.local_root_label.text()
    assert window.task_table.rowCount() == 1
    assert window.task_table.item(0, 0).text() == "课程A"
    assert window.task_table.item(0, 3).text() == FolderTaskStatus.RETRYING.value
    assert window.task_table.item(0, 5).text() == "2"
    assert window.progress_summary_label.text() == "任务进度：0/1，失败 0"
    assert window.current_action_label.text() == "当前文件：cover.txt"
    assert window.selected_remote_label.text() == "当前选择：资料 / 课程A"
