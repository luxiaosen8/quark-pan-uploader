from pathlib import Path
import json

from quark_uploader.services.startup_diagnostics import write_startup_diagnostics


def test_write_startup_diagnostics_creates_daily_log(tmp_path: Path):
    output_dir = tmp_path / "output"
    settings_path = tmp_path / ".local" / "app_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("{}", encoding="utf-8")

    log_path = write_startup_diagnostics(output_dir, settings_path)

    assert log_path.exists()
    rows = log_path.read_text(encoding="utf-8").splitlines()
    payload = json.loads(rows[0])
    assert payload["stage"] == "startup"
    assert payload["extra"]["settings_path"] == str(settings_path)
    assert payload["extra"]["qt_webengine"]["resources"]["qtwebengine_process"] in {True, False}
