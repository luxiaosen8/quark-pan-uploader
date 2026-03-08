from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_start_button_disabled_until_required_inputs_selected(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.start_button.isEnabled() is False

    window.cookie_valid = True
    window.local_root = "C:/demo"
    window.remote_folder_id = "fid-demo"
    window.recompute_start_enabled()

    assert window.start_button.isEnabled() is True


def test_single_target_mode_shows_single_target_actions(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_upload_mode("single_target")

    assert window.select_local_folder_button.isHidden() is True
    assert window.select_single_folder_button.isHidden() is False
    assert window.select_single_file_button.isHidden() is False
