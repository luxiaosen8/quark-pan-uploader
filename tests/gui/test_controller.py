from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.controller import MainWindowController
from quark_uploader.models import AccountSummary, DriveRefreshResult, RemoteFolderNode


class FakeRefreshService:
    def refresh(self):
        return DriveRefreshResult(
            account=AccountSummary(nickname="测试用户", total_bytes=1000, used_bytes=400, available_bytes=600),
            root_nodes=[RemoteFolderNode(fid="folder-1", name="资料", parent_fid="0", has_children=True)],
        )


class FakeLoginDialog:
    def __init__(self, cookie_string: str | None):
        self.cookie_string = cookie_string

    def exec(self):
        return 1 if self.cookie_string else 0


def test_controller_refresh_updates_window(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.cookie_input.setText("sid=123")

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog(None),
    )

    controller.refresh_drive()

    assert window.cookie_valid is True
    assert window.status_label.text() == "已连接"
    assert window.remote_tree.topLevelItemCount() == 1


def test_controller_applies_cookie_from_login_dialog(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: FakeLoginDialog("sid=123; kps=abc"),
    )

    controller.open_official_login()

    assert window.cookie_input.text() == "sid=123; kps=abc"
    assert "已获取官方登录 Cookie" in window.log_output.toPlainText()


class FakeNestedRefreshService(FakeRefreshService):
    def __init__(self):
        self.child_calls = []

    def load_children(self, parent_fid: str):
        self.child_calls.append(parent_fid)
        return [RemoteFolderNode(fid="child-1", name="子目录", parent_fid=parent_fid, has_children=False)]


def test_controller_loads_children_when_tree_item_expands(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.cookie_input.setText("sid=123")
    service = FakeNestedRefreshService()

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: service,
        login_dialog_factory=lambda on_success: FakeLoginDialog(None),
    )

    controller.refresh_drive()
    item = window.remote_tree.topLevelItem(0)
    controller.on_tree_item_expanded(item)

    assert service.child_calls == ["folder-1"]
    assert item.childCount() == 1
    assert item.child(0).text(0) == "子目录"



class TrackingLoginDialog(FakeLoginDialog):
    def __init__(self, cookie_string=None):
        super().__init__(cookie_string)
        self.exec_called = False
        self._parent = None

    def setParent(self, parent):
        self._parent = parent

    def parent(self):
        return self._parent

    def exec(self):
        self.exec_called = True
        return super().exec()


def test_official_login_button_click_invokes_dialog_factory(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    dialog = TrackingLoginDialog(None)

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: dialog,
    )

    qtbot.mouseClick(window.official_login_button, __import__('PySide6.QtCore').QtCore.Qt.MouseButton.LeftButton)

    assert dialog.exec_called is True



def test_open_official_login_logs_error_when_dialog_factory_raises(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=lambda on_success: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    controller.open_official_login()

    assert window.status_label.text() == "官方登录打开失败"
    assert "官方登录窗口打开失败：boom" in window.log_output.toPlainText()


def test_open_official_login_passes_window_to_dialog_factory(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    record = {}

    def login_factory(on_success, parent=None):
        record["parent"] = parent
        return TrackingLoginDialog(None)

    controller = MainWindowController(
        window=window,
        refresh_service_factory=lambda cookie: FakeRefreshService(),
        login_dialog_factory=login_factory,
    )

    controller.open_official_login()

    assert record["parent"] is window
