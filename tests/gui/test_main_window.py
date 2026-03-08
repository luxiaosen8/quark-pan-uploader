from PySide6.QtWidgets import QPlainTextEdit, QTabWidget
from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_main_window_has_start_button(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.start_button.text() == "开始上传"


def test_main_window_uses_controls_first_tabbed_workspace(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    root_layout = window.layout()
    assert root_layout.itemAt(0).widget() is window.controls_card
    assert root_layout.itemAt(1).widget() is window.workspace_tabs
    assert isinstance(window.workspace_tabs, QTabWidget)
    assert window.workspace_tabs.objectName() == "workspaceTabs"
    assert window.workspace_tabs.count() == 3
    assert window.workspace_tabs.tabText(0) == "上传任务"
    assert window.workspace_tabs.widget(0) is window.task_card
    assert window.workspace_tabs.tabText(1) == "目标网盘目录"
    assert window.workspace_tabs.widget(1) is window.remote_card
    assert window.workspace_tabs.tabText(2) == "运行日志"
    assert window.workspace_tabs.widget(2) is window.log_card
    assert window.workspace_tabs.currentIndex() == 0
    assert window.controls_card.isAncestorOf(window.selected_remote_label)


def test_controls_panel_does_not_need_scrollbar_at_default_size(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)

    assert window.controls_scroll.verticalScrollBar().maximum() <= 20
    assert window.upload_mode_batch_button.isVisible() is True
    assert window.upload_mode_single_button.isVisible() is True


def test_main_window_uses_plain_text_log_panel(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert isinstance(window.log_output, QPlainTextEdit)
    assert window.log_output.maximumBlockCount() == 1000


def test_main_window_exposes_upload_mode_switch_and_single_target_buttons(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.upload_mode_section_label.text() == "上传模式"
    assert window.upload_mode_batch_button.text() == "批量子文件夹"
    assert window.upload_mode_single_button.text() == "单文件/单文件夹"
    assert window.select_single_folder_button.text() == "选择单个文件夹"
    assert window.select_single_file_button.text() == "选择单个文件"
    assert window.upload_mode_batch_button.isChecked() is True


def test_start_button_returns_focus_to_task_tab(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    window.start_button.setEnabled(True)
    window.workspace_tabs.setCurrentWidget(window.log_card)

    window.start_button.click()

    assert window.workspace_tabs.currentWidget() is window.task_card
