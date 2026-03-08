from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_main_window_has_start_button(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.start_button.text() == "开始上传"


def test_main_window_exposes_professional_layout_sections(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.summary_card.objectName() == "summaryCard"
    assert window.controls_card.objectName() == "controlsCard"
    assert window.remote_card.objectName() == "remoteCard"
    assert window.task_card.objectName() == "taskCard"
    assert window.log_card.objectName() == "logCard"
    assert window.window_title_label.text() == "夸克网盘批量上传分享工具"
