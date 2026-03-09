from __future__ import annotations

from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.official_login_dialog import OfficialLoginDialog


def test_main_window_and_login_dialog_share_interaction_contract(qtbot) -> None:
    window = MainWindow()
    dialog = OfficialLoginDialog(lambda cookie: True)
    qtbot.addWidget(window)
    qtbot.addWidget(dialog)

    assert "QLineEdit:focus" in window.styleSheet()
    assert 'QPushButton[busy="true"]' in window.styleSheet()
    assert 'QLabel#loginStatusLabel[state="busy"]' in dialog.styleSheet()
    assert "QFrame#loginWebContainer" in dialog.styleSheet()
