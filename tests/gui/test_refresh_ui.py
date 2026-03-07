from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow
from quark_uploader.models import AccountSummary, RemoteFolderNode


def test_main_window_has_refresh_related_controls(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.refresh_button.text() == "刷新网盘"
    assert window.official_login_button.text() == "官方登录"


def test_main_window_populates_remote_tree(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_account_summary(AccountSummary(nickname="测试用户", total_bytes=1000, used_bytes=400, available_bytes=600))
    window.populate_remote_tree([RemoteFolderNode(fid="folder-1", name="资料", parent_fid="0", has_children=True)])

    assert "测试用户" in window.account_label.text()
    assert window.remote_tree.topLevelItemCount() == 1
    assert window.remote_tree.topLevelItem(0).text(0) == "资料"
