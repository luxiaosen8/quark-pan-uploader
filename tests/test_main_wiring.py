from quark_uploader.main import build_upload_executor


def test_build_upload_executor_returns_engine_with_execute_job():
    engine = build_upload_executor("sid=123")
    assert hasattr(engine, "execute_job")
