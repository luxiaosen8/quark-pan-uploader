from quark_uploader.app import create_app
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import AccountSummary, DriveRefreshResult, RemoteFolderNode
from quark_uploader.settings import AppSettings


class FakeRefreshService:
    def refresh(self):
        return DriveRefreshResult(
            account=AccountSummary(nickname="测试用户", total_bytes=1000, used_bytes=400, available_bytes=600),
            root_nodes=[RemoteFolderNode(fid="folder-1", name="资料", parent_fid="0", has_children=False)],
        )

    def load_children(self, parent_fid: str):
        return []


class FakeSettingsStore:
    def __init__(self, settings: AppSettings | None = None):
        self.settings = settings or AppSettings()
        self.saved_settings = None

    def load(self):
        return self.settings.model_copy(deep=True)

    def save(self, settings: AppSettings):
        self.saved_settings = settings.model_copy(deep=True)


class FakeLoginDialog:
    def __init__(self, cookie_string=None):
        self.cookie_string = cookie_string

    def exec(self):
        return 1 if self.cookie_string else 0


def test_controller_applies_persisted_cookie_on_startup(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    store = FakeSettingsStore(AppSettings(save_cookie=True, persisted_cookie="sid=123"))

    MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success, parent=None: FakeLoginDialog(),
        settings_store=store,
    )

    assert window.cookie_input.text() == "sid=123"
    assert window.remember_cookie_checkbox.isChecked() is True


def test_controller_persists_cookie_after_refresh_success(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.cookie_input.setText("sid=123")
    store = FakeSettingsStore(AppSettings(save_cookie=True, persisted_cookie=""))
    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success, parent=None: FakeLoginDialog(),
        settings_store=store,
    )

    controller.refresh_drive()

    assert store.saved_settings is not None
    assert store.saved_settings.persisted_cookie == "sid=123"
    assert store.saved_settings.save_cookie is True
