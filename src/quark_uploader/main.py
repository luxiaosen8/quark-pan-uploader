from __future__ import annotations

import os
import traceback

from quark_uploader.app import create_app
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.official_login_dialog import OfficialLoginDialog
from quark_uploader.paths import get_bundle_root, get_runtime_root, get_settings_path, is_frozen_app, resolve_runtime_path
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
from quark_uploader.services.settings_store import AppSettingsStore
from quark_uploader.services.share_service import QuarkShareService
from quark_uploader.services.startup_diagnostics import write_startup_diagnostics
from quark_uploader.services.upload_executor import UploadExecutionEngine
from quark_uploader.settings import AppSettings


def _bootstrap_trace_enabled() -> bool:
    env_value = os.getenv("QUARK_UPLOADER_DEBUG", "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    try:
        return build_settings_store().load().debug_mode
    except Exception:
        return False


def _write_bootstrap_trace(stage: str, **extra: object) -> None:
    if not _bootstrap_trace_enabled():
        return
    try:
        trace_path = get_runtime_root() / 'bootstrap_trace.log'
        with trace_path.open('a', encoding='utf-8') as handle:
            handle.write(f"[{stage}] cwd={os.getcwd()} frozen={is_frozen_app()} runtime_root={get_runtime_root()} bundle_root={get_bundle_root()} extra={extra}\n")
    except Exception:
        pass


def build_refresh_service(cookie: str, settings: AppSettings | None = None) -> DriveRefreshService:
    runtime_settings = settings or AppSettings()
    session = QuarkSession(cookie=cookie, timeout_seconds=runtime_settings.request_timeout_seconds)
    return DriveRefreshService(user_api=QuarkUserApi(session), file_api=QuarkFileApi(session))


def build_upload_executor(cookie: str, settings: AppSettings | None = None, logger=None) -> UploadExecutionEngine:
    runtime_settings = settings or AppSettings()
    session = QuarkSession(cookie=cookie, timeout_seconds=runtime_settings.request_timeout_seconds)
    file_api = QuarkFileApi(session)
    upload_api = QuarkUploadApi(session)
    share_api = QuarkShareApi(session)
    task_api = QuarkTaskApi(session)
    result_writer = ResultWriter(resolve_runtime_path(runtime_settings.output_dir))
    share_service = QuarkShareService(
        share_api=share_api,
        task_api=task_api,
        result_writer=result_writer,
        max_retries=runtime_settings.share_poll_max_retries,
        poll_interval_seconds=runtime_settings.share_poll_interval_seconds,
        logger=logger,
    )
    return UploadExecutionEngine(
        directory_sync_service=RemoteDirectorySyncService(file_api),
        uploader=QuarkFileUploader(upload_api=upload_api, logger=logger),
        share_service=share_service,
        result_writer=result_writer,
        logger=logger,
        file_retry_limit=runtime_settings.file_retry_limit,
        share_retry_limit=runtime_settings.share_retry_limit,
        retry_backoff_base_seconds=runtime_settings.retry_backoff_base_seconds,
    )


def build_login_dialog(cookie_validator, parent=None):
    return OfficialLoginDialog(cookie_validator=cookie_validator, parent=parent)


def build_settings_store() -> AppSettingsStore:
    return AppSettingsStore(get_settings_path())


def build_cleanup_service(cookie: str, settings: AppSettings | None = None, logger=None) -> RemoteCleanupService:
    runtime_settings = settings or AppSettings()
    session = QuarkSession(cookie=cookie, timeout_seconds=runtime_settings.request_timeout_seconds)
    file_api = QuarkFileApi(session)
    result_writer = ResultWriter(resolve_runtime_path(runtime_settings.output_dir))
    return RemoteCleanupService(file_api, result_writer=result_writer, logger=logger)


def build_main_window() -> MainWindow:
    settings_store = build_settings_store()
    current_settings = settings_store.ensure_exists()
    output_dir = resolve_runtime_path(current_settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_startup_diagnostics(output_dir, settings_store.settings_path)

    window = MainWindow()
    window._controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: build_refresh_service(cookie, settings=settings_store.load()),
        login_dialog_factory=build_login_dialog,
        upload_executor_factory=lambda logger_callback=None: build_upload_executor(
            window.cookie_input.text().strip(),
            settings=settings_store.load(),
            logger=logger_callback or window.append_log,
        ),
        settings_store=settings_store,
        cleanup_service_factory=lambda: build_cleanup_service(
            window.cookie_input.text().strip(),
            settings=settings_store.load(),
            logger=window.append_log,
        ),
        use_async_upload=True,
    )
    return window


def main() -> None:
    _write_bootstrap_trace('main_enter')
    try:
        app = create_app()
        _write_bootstrap_trace('app_created')
        window = build_main_window()
        _write_bootstrap_trace('window_built')
        window.show()
        _write_bootstrap_trace('window_shown')
        app.exec()
        _write_bootstrap_trace('app_exit')
    except Exception:
        _write_bootstrap_trace('error', traceback=traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
