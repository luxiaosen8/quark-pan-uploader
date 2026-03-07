from __future__ import annotations

from pathlib import Path

from quark_uploader.app import create_app
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.official_login_dialog import OfficialLoginDialog
from quark_uploader.quark.file_api import QuarkFileApi
from quark_uploader.quark.session import QuarkSession
from quark_uploader.quark.share_api import QuarkShareApi
from quark_uploader.quark.task_api import QuarkTaskApi
from quark_uploader.quark.upload_api import QuarkUploadApi
from quark_uploader.quark.user_api import QuarkUserApi
from quark_uploader.services.quark_file_uploader import QuarkFileUploader
from quark_uploader.services.refresh_service import DriveRefreshService
from quark_uploader.services.remote_cleanup_service import RemoteCleanupService
from quark_uploader.services.remote_directory_sync import RemoteDirectorySyncService
from quark_uploader.services.result_writer import ResultWriter
from quark_uploader.services.share_service import QuarkShareService
from quark_uploader.services.settings_store import AppSettingsStore
from quark_uploader.services.upload_executor import UploadExecutionEngine


def build_refresh_service(cookie: str) -> DriveRefreshService:
    session = QuarkSession(cookie=cookie)
    return DriveRefreshService(user_api=QuarkUserApi(session), file_api=QuarkFileApi(session))


def build_upload_executor(cookie: str, logger=None) -> UploadExecutionEngine:
    session = QuarkSession(cookie=cookie)
    file_api = QuarkFileApi(session)
    upload_api = QuarkUploadApi(session)
    share_api = QuarkShareApi(session)
    task_api = QuarkTaskApi(session)
    result_writer = ResultWriter(Path("output"))
    share_service = QuarkShareService(share_api=share_api, task_api=task_api, result_writer=result_writer, logger=logger)
    return UploadExecutionEngine(
        directory_sync_service=RemoteDirectorySyncService(file_api),
        uploader=QuarkFileUploader(upload_api=upload_api, logger=logger),
        share_service=share_service,
        result_writer=result_writer,
        logger=logger,
    )


def build_login_dialog(cookie_validator, parent=None):
    return OfficialLoginDialog(cookie_validator=cookie_validator, parent=parent)


def build_settings_store() -> AppSettingsStore:
    return AppSettingsStore(Path(".local") / "app_settings.json")


def build_cleanup_service(cookie: str, logger=None) -> RemoteCleanupService:
    session = QuarkSession(cookie=cookie)
    file_api = QuarkFileApi(session)
    result_writer = ResultWriter(Path("output"))
    return RemoteCleanupService(file_api, result_writer=result_writer, logger=logger)


def build_main_window() -> MainWindow:
    window = MainWindow()
    window._controller = MainWindowController(
        window=window,
        refresh_service_factory=build_refresh_service,
        login_dialog_factory=build_login_dialog,
        upload_executor_factory=lambda: build_upload_executor(window.cookie_input.text().strip(), logger=window.append_log),
        settings_store=build_settings_store(),
        cleanup_service_factory=lambda: build_cleanup_service(window.cookie_input.text().strip(), logger=window.append_log),
        use_async_upload=True,
    )
    return window


def main() -> None:
    app = create_app()
    window = build_main_window()
    window.show()
    app.exec()
