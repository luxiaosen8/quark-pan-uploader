from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from quark_uploader.paths import get_icon_path


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    icon_path = get_icon_path()
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    return app
