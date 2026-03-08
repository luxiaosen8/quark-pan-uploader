from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

import quark_uploader.gui.official_login_dialog as dialog_module
from quark_uploader.app import create_app
from quark_uploader.gui.official_login_dialog import OfficialLoginDialog


class FakeCookieStore(QObject):
    cookieAdded = Signal(object)


class FakeProfile(QObject):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._store = FakeCookieStore()

    def cookieStore(self):
        return self._store


class FakePage(QObject):
    def __init__(self, profile, parent=None) -> None:
        super().__init__(parent)
        self.profile = profile


class FakeView(QWidget):
    loadFinished = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.page = None

    def setPage(self, page) -> None:
        self.page = page

    def setUrl(self, url) -> None:
        self.loadFinished.emit(True)


def test_official_login_dialog_validates_cookie_asynchronously(qtbot, monkeypatch):
    create_app()
    monkeypatch.setattr(dialog_module, "QWebEngineProfile", FakeProfile)
    monkeypatch.setattr(dialog_module, "QWebEnginePage", FakePage)
    monkeypatch.setattr(dialog_module, "QWebEngineView", FakeView)

    validator_threads = []

    def slow_validator(cookie: str) -> bool:
        validator_threads.append(threading.get_ident())
        time.sleep(0.2)
        return False

    dialog = OfficialLoginDialog(cookie_validator=slow_validator)
    qtbot.addWidget(dialog)
    dialog._cookies["sid"] = "abc123"

    started_at = time.perf_counter()
    dialog._validate_and_finish()
    elapsed = time.perf_counter() - started_at

    assert elapsed < 0.05
    qtbot.waitUntil(lambda: dialog.status_label.text() == "已捕获部分 Cookie，等待完成登录…", timeout=3000)
    assert validator_threads
    assert validator_threads[0] != threading.get_ident()
