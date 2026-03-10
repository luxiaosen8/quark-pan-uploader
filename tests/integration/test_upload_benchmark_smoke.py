from __future__ import annotations

import importlib.util
from pathlib import Path


def test_benchmark_script_runs_and_reports_expected_sections() -> None:
    script_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "benchmark_upload_modes.py"
    )
    spec = importlib.util.spec_from_file_location("benchmark_upload_modes", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)

    report = module.run_benchmark_suite()

    assert set(report.keys()) == {"serial", "concurrent"}
    assert set(report["serial"].keys()) == set(report["concurrent"].keys())
    assert report["serial"]["small"]["total_bytes"] > 0
    assert report["serial"]["small"]["parts"] >= 1
    assert (
        report["concurrent"]["small"]["duration_seconds"]
        < report["serial"]["small"]["duration_seconds"]
    )
    assert report["concurrent"]["large"]["average_parts_per_second"] > 0
