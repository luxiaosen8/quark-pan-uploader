from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_main_window_has_remember_cookie_checkbox_checked_by_default(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.remember_cookie_checkbox.text() == "记住 Cookie"
    assert window.remember_cookie_checkbox.isChecked() is True
