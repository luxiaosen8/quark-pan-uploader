from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLibraryInfo

from quark_uploader.paths import get_bundle_root, get_runtime_root, is_frozen_app
from quark_uploader.services.logger import StructuredLogger


def collect_qt_webengine_diagnostics() -> dict[str, object]:
    data_root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath))
    translations_root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    checks = {
        'qtwebengine_process': data_root / 'QtWebEngineProcess.exe',
        'qtwebengine_resources_pak': data_root / 'resources' / 'qtwebengine_resources.pak',
        'qtwebengine_resources_100p_pak': data_root / 'resources' / 'qtwebengine_resources_100p.pak',
        'qtwebengine_resources_200p_pak': data_root / 'resources' / 'qtwebengine_resources_200p.pak',
        'qtwebengine_devtools_resources_pak': data_root / 'resources' / 'qtwebengine_devtools_resources.pak',
        'qtwebengine_icudtl': data_root / 'resources' / 'icudtl.dat',
        'qtwebengine_locale_en_us': translations_root / 'qtwebengine_locales' / 'en-US.pak',
    }
    return {
        'data_root': str(data_root),
        'translations_root': str(translations_root),
        'resources': {name: path.exists() for name, path in checks.items()},
    }


def write_startup_diagnostics(output_dir: Path, settings_path: Path) -> Path:
    logs_dir = output_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    logger = StructuredLogger(log_path)
    logger.log(
        'INFO',
        'startup',
        '',
        'application startup',
        runtime_root=str(get_runtime_root()),
        bundle_root=str(get_bundle_root()),
        cwd=os.getcwd(),
        frozen=is_frozen_app(),
        output_dir=str(output_dir),
        settings_path=str(settings_path),
        settings_exists=settings_path.exists(),
        qt_webengine=collect_qt_webengine_diagnostics(),
    )
    return log_path
