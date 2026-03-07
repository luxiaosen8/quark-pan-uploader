from pathlib import Path
import json

from quark_uploader.services.settings_store import AppSettingsStore


def test_settings_store_returns_defaults_when_file_missing(tmp_path: Path):
    store = AppSettingsStore(tmp_path / "app_settings.json")
    settings = store.load()

    assert settings.save_cookie is True
    assert settings.persisted_cookie == ""
    assert settings.output_dir == "output"


def test_settings_store_persists_cookie_and_reload(tmp_path: Path):
    settings_path = tmp_path / "app_settings.json"
    store = AppSettingsStore(settings_path)
    settings = store.load()
    settings.persisted_cookie = "sid=123; kps=abc"
    settings.save_cookie = True
    store.save(settings)

    raw_payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "persisted_cookie" not in raw_payload
    assert raw_payload["persisted_cookie_encrypted"]

    reloaded = store.load()
    assert reloaded.persisted_cookie == "sid=123; kps=abc"
    assert reloaded.save_cookie is True
