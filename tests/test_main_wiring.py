from quark_uploader.app import create_app
from quark_uploader.main import build_cleanup_service, build_main_window, build_upload_executor


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



def test_build_cleanup_service_includes_result_writer():
    service = build_cleanup_service("sid=123")
    assert service.result_writer is not None
