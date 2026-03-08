from __future__ import annotations

import sys
from pathlib import Path


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_runtime_root() -> Path:
    if is_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def get_bundle_root() -> Path:
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parents[2]


def resolve_runtime_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return get_runtime_root() / path


def get_settings_path() -> Path:
    return get_runtime_root() / '.local' / 'app_settings.json'


def get_default_output_dir() -> Path:
    return resolve_runtime_path('output')


def get_icon_path() -> Path:
    return get_bundle_root() / 'assets' / 'app_icon.ico'
