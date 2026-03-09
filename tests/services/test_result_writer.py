from __future__ import annotations

from quark_uploader.services.result_writer import ResultWriter


def test_result_writer_uses_unique_run_ids_for_same_output_dir(tmp_path) -> None:
    first = ResultWriter(tmp_path)
    second = ResultWriter(tmp_path)

    assert first.run_id != second.run_id
