from quark_uploader.app import create_app


def test_create_app_returns_qapplication(qtbot):
    app = create_app()
    assert app is not None
