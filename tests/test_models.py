from quark_uploader.models import FolderTask, FolderTaskStatus, TaskSourceType, UploadMode
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


def test_folder_task_defaults_to_folder_source_type():
    task = FolderTask(local_name="demo", local_path="C:/demo")
    assert task.source_type is TaskSourceType.FOLDER


def test_upload_mode_enum_contains_single_target():
    assert UploadMode.SINGLE_TARGET.value == "single_target"
