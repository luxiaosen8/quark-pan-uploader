from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_main_window_has_start_button(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.start_button.text() == "开始上传"
