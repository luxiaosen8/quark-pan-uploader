from __future__ import annotations

from collections import OrderedDict
from typing import Callable

from PySide6.QtCore import QObject, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from quark_uploader.services.cookie_capture import format_cookie_header, is_quark_cookie_domain
from quark_uploader.services.official_login import OFFICIAL_LOGIN_PAGE_URL, OFFICIAL_MOBILE_LOGIN_URL


class CookieValidationWorker(QObject):
    finished = Signal(str, bool)

    def __init__(self, cookie_validator: Callable[[str], bool], candidate: str) -> None:
        super().__init__()
        self.cookie_validator = cookie_validator
        self.candidate = candidate

    @Slot()
    def run(self) -> None:
        self.finished.emit(self.candidate, bool(self.cookie_validator(self.candidate)))


class OfficialLoginDialog(QDialog):
    def __init__(self, cookie_validator: Callable[[str], bool], parent=None) -> None:
        super().__init__(parent)
        self.cookie_validator = cookie_validator
        self.cookie_string = ""
        self._cookies: OrderedDict[str, str] = OrderedDict()
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(800)
        self._validation_timer.timeout.connect(self._validate_and_finish)
        self._validation_thread: QThread | None = None
        self._validation_worker: CookieValidationWorker | None = None
        self._validation_in_progress = False
        self._pending_candidate = ""

        self.setWindowTitle("官方登录")
        self.resize(960, 720)

        self.info_label = QLabel("请在下方官方页面中完成扫码或手机号登录。登录成功后将自动提取 Cookie。")
        self.status_label = QLabel("等待登录中…")
        self.copy_mobile_login_button = QPushButton("复制官方手机登录链接")
        self.copy_mobile_login_button.clicked.connect(self.copy_mobile_login_url)

        self.profile = QWebEngineProfile(self)
        self.page = QWebEnginePage(self.profile, self)
        self.view = QWebEngineView(self)
        self.view.setPage(self.page)
        self.view.loadFinished.connect(self._on_load_finished)
        self.profile.cookieStore().cookieAdded.connect(self._on_cookie_added)

        button_row = QHBoxLayout()
        button_row.addWidget(self.copy_mobile_login_button)

        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.view.setUrl(QUrl(OFFICIAL_LOGIN_PAGE_URL))

    def copy_mobile_login_url(self) -> None:
        QGuiApplication.clipboard().setText(OFFICIAL_MOBILE_LOGIN_URL)
        self.status_label.setText("已复制官方手机登录链接")

    def _on_load_finished(self, ok: bool) -> None:
        if ok:
            self.status_label.setText("官方登录页已加载，请扫码或完成手机号登录")
        else:
            self.status_label.setText("官方登录页加载失败，请检查网络")

    def _on_cookie_added(self, cookie) -> None:
        domain = cookie.domain()
        if not is_quark_cookie_domain(domain):
            return
        name = bytes(cookie.name()).decode("utf-8", errors="ignore")
        value = bytes(cookie.value()).decode("utf-8", errors="ignore")
        if not name or not value:
            return
        self._cookies[name] = value
        self.status_label.setText("检测到登录态变化，正在准备验证 Cookie…")
        self._validation_timer.start()

    def _validate_and_finish(self) -> None:
        candidate = format_cookie_header(self._cookies)
        if not candidate:
            return
        self._pending_candidate = candidate
        if self._validation_in_progress:
            return
        self._start_pending_validation()

    def _start_pending_validation(self) -> None:
        candidate = self._pending_candidate
        if not candidate or self._validation_in_progress:
            return
        self._pending_candidate = ""
        self._validation_in_progress = True
        self.status_label.setText("正在验证 Cookie…")

        thread = QThread(self)
        worker = CookieValidationWorker(self.cookie_validator, candidate)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_validation_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_validation_thread)
        self._validation_thread = thread
        self._validation_worker = worker
        thread.start()

    @Slot(str, bool)
    def _on_validation_finished(self, candidate: str, is_valid: bool) -> None:
        self._validation_in_progress = False
        latest_candidate = format_cookie_header(self._cookies)
        if is_valid and candidate == latest_candidate:
            self.cookie_string = candidate
            self.status_label.setText("登录成功，已自动获取 Cookie")
            self.accept()
            return
        if latest_candidate and latest_candidate != candidate:
            self._pending_candidate = latest_candidate
            self.status_label.setText("检测到新的登录态变化，继续验证…")
            self._start_pending_validation()
            return
        self.status_label.setText("已捕获部分 Cookie，等待完成登录…")

    def _clear_validation_thread(self) -> None:
        self._validation_thread = None
        self._validation_worker = None
