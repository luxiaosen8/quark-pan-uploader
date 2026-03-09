from __future__ import annotations

from quark_uploader.gui.main_window import MainWindow


def test_main_window_styles_include_focus_and_busy_feedback(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    style_sheet = window.styleSheet()

    assert "QLineEdit:focus" in style_sheet
    assert "QTreeWidget:focus" in style_sheet
    assert "QTableWidget:focus" in style_sheet
    assert "QPlainTextEdit:focus" in style_sheet
    assert 'QPushButton[busy="true"]' in style_sheet
