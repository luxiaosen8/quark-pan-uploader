from __future__ import annotations

from quark_uploader.app import create_app
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.official_login_dialog import OfficialLoginDialog
from quark_uploader.quark.file_api import QuarkFileApi
from quark_uploader.quark.session import QuarkSession
from quark_uploader.quark.upload_api import QuarkUploadApi
from quark_uploader.quark.user_api import QuarkUserApi
from quark_uploader.services.quark_file_uploader import QuarkFileUploader
from quark_uploader.services.refresh_service import DriveRefreshService
from quark_uploader.services.remote_directory_sync import RemoteDirectorySyncService
from quark_uploader.services.upload_executor import UploadExecutionEngine


def build_refresh_service(cookie: str) -> DriveRefreshService:
    session = QuarkSession(cookie=cookie)
    return DriveRefreshService(user_api=QuarkUserApi(session), file_api=QuarkFileApi(session))


def build_upload_executor(cookie: str) -> UploadExecutionEngine:
    session = QuarkSession(cookie=cookie)
    file_api = QuarkFileApi(session)
    upload_api = QuarkUploadApi(session)
    return UploadExecutionEngine(
        directory_sync_service=RemoteDirectorySyncService(file_api),
        uploader=QuarkFileUploader(upload_api=upload_api),
    )


def build_login_dialog(cookie_validator):
    return OfficialLoginDialog(cookie_validator=cookie_validator)


def main() -> None:
    app = create_app()
    window = MainWindow()
    MainWindowController(
        window=window,
        refresh_service_factory=build_refresh_service,
        login_dialog_factory=build_login_dialog,
        upload_executor_factory=lambda: build_upload_executor(window.cookie_input.text().strip()),
    )
    window.show()
    app.exec()
