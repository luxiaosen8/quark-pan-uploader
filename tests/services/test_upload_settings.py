from __future__ import annotations

import json

from quark_uploader.services.settings_store import AppSettingsStore
from quark_uploader.settings import (
    AppSettings,
    DEFAULT_JOB_CONCURRENCY,
    DEFAULT_PART_CONCURRENCY,
    DEFAULT_UI_UPDATE_INTERVAL_MS,
)


def test_app_settings_uses_safe_defaults() -> None:
    settings = AppSettings()

    assert settings.job_concurrency == DEFAULT_JOB_CONCURRENCY
    assert settings.part_concurrency == DEFAULT_PART_CONCURRENCY
    assert settings.ui_update_interval_ms == DEFAULT_UI_UPDATE_INTERVAL_MS


def test_app_settings_invalid_values_fall_back_to_defaults() -> None:
    settings = AppSettings(
        job_concurrency=99, part_concurrency=0, ui_update_interval_ms=-1
    )

    assert settings.job_concurrency == DEFAULT_JOB_CONCURRENCY
    assert settings.part_concurrency == DEFAULT_PART_CONCURRENCY
    assert settings.ui_update_interval_ms == DEFAULT_UI_UPDATE_INTERVAL_MS


def test_settings_store_loads_legacy_payload_without_new_fields(tmp_path) -> None:
    settings_path = tmp_path / "app_settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "output_dir": "output",
                "save_cookie": False,
                "persisted_cookie_encrypted": "",
            }
        ),
        encoding="utf-8",
    )
    store = AppSettingsStore(settings_path)

    settings = store.load()

    assert settings.output_dir == "output"
    assert settings.job_concurrency == DEFAULT_JOB_CONCURRENCY
    assert settings.part_concurrency == DEFAULT_PART_CONCURRENCY
