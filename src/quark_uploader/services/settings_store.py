from __future__ import annotations

import json
from pathlib import Path

from quark_uploader.settings import AppSettings


class AppSettingsStore:
    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def load(self) -> AppSettings:
        if not self.settings_path.exists():
            return AppSettings()
        payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        return AppSettings.model_validate(payload)

    def save(self, settings: AppSettings) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
