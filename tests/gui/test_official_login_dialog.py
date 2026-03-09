from __future__ import annotations

from collections import OrderedDict

from quark_uploader.gui.official_login_dialog import OfficialLoginDialog


def test_official_login_dialog_validates_cookie_and_accepts(qtbot) -> None:
    dialog = OfficialLoginDialog(lambda cookie: cookie == "k=v")
    qtbot.addWidget(dialog)
    dialog._cookies = OrderedDict({"k": "v"})

    dialog._validate_and_finish()

    qtbot.waitUntil(lambda: dialog.cookie_string == "k=v", timeout=1000)
    assert dialog.status_label.text() == "登录成功，已自动获取 Cookie"
