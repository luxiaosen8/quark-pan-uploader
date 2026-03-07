from pathlib import Path

from quark_uploader.services.settings_store import AppSettingsStore


def test_settings_store_returns_defaults_when_file_missing(tmp_path: Path):
    store = AppSettingsStore(tmp_path / "app_settings.json")
    settings = store.load()

    assert settings.save_cookie is True
    assert settings.persisted_cookie == ""


def test_settings_store_persists_cookie_and_reload(tmp_path: Path):
    store = AppSettingsStore(tmp_path / "app_settings.json")
    settings = store.load()
    settings.persisted_cookie = "sid=123; kps=abc"
    settings.save_cookie = True
    store.save(settings)

    reloaded = store.load()
    assert reloaded.persisted_cookie == "sid=123; kps=abc"
    assert reloaded.save_cookie is True
