from quark_uploader.app import create_app
from quark_uploader.main import build_cleanup_service, build_main_window, build_upload_executor
from quark_uploader.settings import AppSettings


def test_build_upload_executor_returns_engine_with_execute_job():
    engine = build_upload_executor("sid=123")
    assert hasattr(engine, "execute_job")
    assert engine.share_service is not None
    assert engine.share_service.result_writer is not None


def test_build_main_window_keeps_controller_alive():
    create_app()
    window = build_main_window()
    assert hasattr(window, "_controller")
    assert window._controller is not None


def test_build_upload_executor_accepts_logger_callback():
    logs = []
    engine = build_upload_executor("sid=123", logger=logs.append)
    engine.uploader._log("hello-uploader")
    engine.share_service._log("hello-share")
    assert logs == ["hello-uploader", "hello-share"]


def test_build_upload_executor_applies_runtime_settings():
    settings = AppSettings(
        output_dir="custom-output",
        request_timeout_seconds=45,
        file_retry_limit=2,
        share_retry_limit=3,
        share_poll_max_retries=4,
        retry_backoff_base_seconds=0.25,
        share_poll_interval_seconds=0.75,
    )
    engine = build_upload_executor("sid=123", settings=settings)

    assert engine.result_writer.output_dir.name == "custom-output"
    assert engine.file_retry_limit == 2
    assert engine.share_retry_limit == 3
    assert engine.retry_backoff_base_seconds == 0.25
    assert engine.share_service.max_retries == 4
    assert engine.share_service.poll_interval_seconds == 0.75


def test_build_cleanup_service_includes_result_writer():
    service = build_cleanup_service("sid=123")
    assert service.result_writer is not None


def test_build_cleanup_service_uses_configured_output_dir():
    settings = AppSettings(output_dir="cleanup-output")
    service = build_cleanup_service("sid=123", settings=settings)
    assert service.result_writer.output_dir.name == "cleanup-output"
