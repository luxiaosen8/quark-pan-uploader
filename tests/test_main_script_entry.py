from pathlib import Path


def test_main_module_has_script_entry_guard():
    main_file = Path(__file__).resolve().parents[1] / "src" / "quark_uploader" / "main.py"
    text = main_file.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in text


def test_bootstrap_trace_is_guarded_by_debug_flag():
    from quark_uploader.main import _bootstrap_trace_enabled

    assert _bootstrap_trace_enabled() is False
