from PySide6.QtWidgets import QApplication


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
