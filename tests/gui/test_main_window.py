from PySide6.QtWidgets import QPlainTextEdit
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
    assert window.controls_card.minimumWidth() >= 420
    assert window.content_splitter.objectName() == "contentSplitter"


def test_controls_panel_does_not_need_scrollbar_at_default_size(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)

    assert window.controls_scroll.verticalScrollBar().maximum() == 0


def test_main_window_uses_plain_text_log_panel(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert isinstance(window.log_output, QPlainTextEdit)
    assert window.log_output.maximumBlockCount() == 1000
