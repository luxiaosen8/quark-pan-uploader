from quark_uploader.models import FolderTask, FolderTaskStatus
from quark_uploader.settings import AppSettings


def test_folder_task_defaults_to_pending_status():
    task = FolderTask(local_name="demo", local_path="C:/demo")
    assert task.status is FolderTaskStatus.PENDING


def test_app_settings_default_output_dir():
    settings = AppSettings()
    assert settings.output_dir == "output"


def test_app_settings_debug_mode_defaults_to_false():
    from quark_uploader.settings import AppSettings

    settings = AppSettings()
    assert settings.debug_mode is False
