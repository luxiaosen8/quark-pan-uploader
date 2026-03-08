from quark_uploader.paths import get_bundle_root, get_runtime_root, get_settings_path, resolve_runtime_path


def test_runtime_paths_resolve_under_project_root():
    runtime_root = get_runtime_root()
    bundle_root = get_bundle_root()

    assert runtime_root.exists()
    assert bundle_root.exists()
    assert resolve_runtime_path("output").parent == runtime_root
    assert get_settings_path().parent.parent == runtime_root
