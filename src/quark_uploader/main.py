from __future__ import annotations

from quark_uploader.app import create_app
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.official_login_dialog import OfficialLoginDialog
from quark_uploader.quark.file_api import QuarkFileApi
from quark_uploader.quark.session import QuarkSession
from quark_uploader.quark.user_api import QuarkUserApi
from quark_uploader.services.refresh_service import DriveRefreshService


def build_refresh_service(cookie: str) -> DriveRefreshService:
    session = QuarkSession(cookie=cookie)
    return DriveRefreshService(user_api=QuarkUserApi(session), file_api=QuarkFileApi(session))


def build_login_dialog(cookie_validator):
    return OfficialLoginDialog(cookie_validator=cookie_validator)


def main() -> None:
    app = create_app()
    window = MainWindow()
    MainWindowController(
        window=window,
        refresh_service_factory=build_refresh_service,
        login_dialog_factory=build_login_dialog,
    )
    window.show()
    app.exec()
