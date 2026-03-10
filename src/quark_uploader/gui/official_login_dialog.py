from __future__ import annotations

from collections import OrderedDict
from threading import Thread
from typing import Callable

from PySide6.QtCore import Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from quark_uploader.services.cookie_capture import (
    format_cookie_header,
    is_quark_cookie_domain,
)
from quark_uploader.services.official_login import (
    OFFICIAL_LOGIN_PAGE_URL,
    OFFICIAL_MOBILE_LOGIN_URL,
)


class OfficialLoginDialog(QDialog):
    validation_finished = Signal(str, bool)

    def __init__(self, cookie_validator: Callable[[str], bool], parent=None) -> None:
        super().__init__(parent)
        self.cookie_validator = cookie_validator
        self.cookie_string = ""
        self._cookies: OrderedDict[str, str] = OrderedDict()
        self._validation_timer = QTimer(self)
        self._validation_timer.setSingleShot(True)
        self._validation_timer.setInterval(800)
        self._validation_timer.timeout.connect(self._validate_and_finish)
        self._validation_in_progress = False
        self._pending_candidate = ""
        self.validation_finished.connect(self._on_validation_finished)

        self.setWindowTitle("官方登录")
        self.resize(1280, 900)
        self.setMinimumSize(1080, 800)

        self.title_label = QLabel("官方登录")
        self.title_label.setObjectName("loginTitleLabel")
        self.info_label = QLabel(
            "请在下方官方页面完成扫码或手机号登录，成功后会自动校验 Cookie。"
        )
        self.info_label.setObjectName("loginInfoLabel")
        self.info_label.setWordWrap(True)

        self.status_label = QLabel("等待登录中…")
        self.status_label.setObjectName("loginStatusLabel")
        self.status_label.setProperty("state", "waiting")

        self.copy_mobile_login_button = QPushButton("复制官方手机登录链接")
        self.copy_mobile_login_button.setObjectName("secondaryButton")
        self.copy_mobile_login_button.clicked.connect(self.copy_mobile_login_url)
        self.copy_mobile_login_button.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )

        self.profile = QWebEngineProfile(self)
        self.page = QWebEnginePage(self.profile, self)
        self.view = QWebEngineView(self)
        self.view.setPage(self.page)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.view.loadStarted.connect(self._on_load_started)
        self.view.loadFinished.connect(self._on_load_finished)
        self.profile.cookieStore().cookieAdded.connect(self._on_cookie_added)

        self.header_card = QFrame(self)
        self.header_card.setObjectName("loginHeaderCard")
        self.header_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        header_layout = QVBoxLayout(self.header_card)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_column = QVBoxLayout()
        title_column.setSpacing(4)
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.info_label)
        title_row.addLayout(title_column, 1)
        title_row.addWidget(self.copy_mobile_login_button, 0, Qt.AlignmentFlag.AlignTop)
        header_layout.addLayout(title_row)
        header_layout.addWidget(self.status_label)

        self.web_container = QFrame(self)
        self.web_container.setObjectName("loginWebContainer")
        self.web_container.setProperty("state", "loading")
        self.web_container.setProperty("busy", False)
        self.web_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        web_layout = QVBoxLayout(self.web_container)
        web_layout.setContentsMargins(6, 6, 6, 6)
        web_layout.setSpacing(0)
        web_layout.addWidget(self.view, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        layout.addWidget(self.header_card, 0)
        layout.addWidget(self.web_container, 1)

        self._apply_styles()
        self.view.setUrl(QUrl(OFFICIAL_LOGIN_PAGE_URL))

    def copy_mobile_login_url(self) -> None:
        QGuiApplication.clipboard().setText(OFFICIAL_MOBILE_LOGIN_URL)
        self._set_status("已复制官方手机登录链接", "waiting")

    def _on_load_started(self) -> None:
        if self._validation_in_progress or self.cookie_string:
            return
        self._set_web_state("loading")
        self._set_status("正在加载官方登录页…", "busy")

    def _on_load_finished(self, ok: bool) -> None:
        if self._validation_in_progress or self.cookie_string:
            return
        self._set_web_state("ready" if ok else "error")
        if ok:
            self._set_status("官方登录页已加载，请扫码或完成手机号登录", "waiting")
        else:
            self._set_status("官方登录页加载失败，请检查网络", "error")

    def _on_cookie_added(self, cookie) -> None:
        domain = cookie.domain()
        if not is_quark_cookie_domain(domain):
            return
        name = bytes(cookie.name()).decode("utf-8", errors="ignore")
        value = bytes(cookie.value()).decode("utf-8", errors="ignore")
        if not name or not value:
            return
        self._cookies[name] = value
        self._set_status("检测到登录态变化，正在准备验证 Cookie…", "busy")
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
        self._set_busy_state(True)
        self._set_status("正在验证 Cookie…", "busy")

        def run_validation() -> None:
            result = bool(self.cookie_validator(candidate))
            self.validation_finished.emit(candidate, result)

        Thread(target=run_validation, daemon=True).start()

    @Slot(str, bool)
    def _on_validation_finished(self, candidate: str, is_valid: bool) -> None:
        self._validation_in_progress = False
        self._set_busy_state(False)
        latest_candidate = format_cookie_header(self._cookies)
        if is_valid and candidate == latest_candidate:
            self.cookie_string = candidate
            self._set_status("登录成功，已自动获取 Cookie", "success")
            self.accept()
            return
        if latest_candidate and latest_candidate != candidate:
            self._pending_candidate = latest_candidate
            self._set_status("检测到新的登录态变化，继续验证…", "busy")
            self._start_pending_validation()
            return
        self._set_status("已捕获部分 Cookie，等待完成登录…", "waiting")

    def _refresh_dynamic_style(self, widget) -> None:
        self.style().unpolish(widget)
        self.style().polish(widget)
        widget.update()

    def _set_status(self, text: str, state: str) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        self._refresh_dynamic_style(self.status_label)

    def _set_busy_state(self, busy: bool) -> None:
        self.copy_mobile_login_button.setProperty("busy", busy)
        self.web_container.setProperty("busy", busy)
        self._refresh_dynamic_style(self.copy_mobile_login_button)
        self._refresh_dynamic_style(self.web_container)

    def _set_web_state(self, state: str) -> None:
        self.web_container.setProperty("state", state)
        self._refresh_dynamic_style(self.web_container)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: #f3f6fb;
                color: #1f2937;
            }
            QFrame#loginHeaderCard {
                background: #f8fbff;
                border: 1px solid #d7e7ff;
                border-radius: 16px;
            }
            QLabel#loginTitleLabel {
                color: #0f172a;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#loginInfoLabel {
                color: #64748b;
                font-size: 12px;
            }
            QLabel#loginStatusLabel {
                padding: 8px 12px;
                border-radius: 11px;
                background: #eff6ff;
                color: #1d4ed8;
                border: 1px solid #bfdbfe;
                font-weight: 600;
            }
            QLabel#loginStatusLabel[state="success"] {
                background: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
            }
            QLabel#loginStatusLabel[state="error"] {
                background: #fef2f2;
                color: #b91c1c;
                border: 1px solid #fca5a5;
            }
            QLabel#loginStatusLabel[state="busy"] {
                background: #eff6ff;
                color: #1d4ed8;
                border: 1px solid #93c5fd;
            }
            QPushButton {
                min-height: 30px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                background: #ffffff;
                padding: 4px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f8fafc;
            }
            QPushButton:focus {
                border: 1px solid #2563eb;
            }
            QPushButton[busy="true"] {
                background: #dbeafe;
                color: #1d4ed8;
                border: 1px solid #60a5fa;
            }
            QPushButton:disabled {
                background: #e5e7eb;
                color: #94a3b8;
                border: 1px solid #cbd5e1;
            }
            QFrame#loginWebContainer {
                background: #ffffff;
                border: 1px solid #d8e1ec;
                border-radius: 18px;
            }
            QFrame#loginWebContainer[state="loading"],
            QFrame#loginWebContainer[busy="true"] {
                border: 1px solid #93c5fd;
                background: #f8fbff;
            }
            QFrame#loginWebContainer[state="error"] {
                border: 1px solid #fca5a5;
                background: #fff7f7;
            }
            QWebEngineView {
                background: #ffffff;
                border: none;
                border-radius: 14px;
            }
            """
        )
