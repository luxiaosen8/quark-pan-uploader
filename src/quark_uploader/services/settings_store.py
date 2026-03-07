from __future__ import annotations

import json
from pathlib import Path

from quark_uploader.services.secrets import protect_text, unprotect_text
from quark_uploader.settings import AppSettings


class AppSettingsStore:
    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def load(self) -> AppSettings:
        if not self.settings_path.exists():
            return AppSettings()
        payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        encrypted_cookie = payload.pop("persisted_cookie_encrypted", "")
        settings = AppSettings.model_validate(payload)
        if encrypted_cookie:
            settings.persisted_cookie = unprotect_text(encrypted_cookie)
        return settings

    def save(self, settings: AppSettings) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = settings.model_dump()
        raw_cookie = payload.pop("persisted_cookie", "")
        if raw_cookie:
            payload["persisted_cookie_encrypted"] = protect_text(raw_cookie)
        self.settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
