from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QTreeWidgetItem

from quark_uploader.gui.main_window import MainWindow


class MainWindowController:
    def __init__(
        self,
        window: MainWindow,
        refresh_service_factory: Callable[[str], object],
        login_dialog_factory: Callable[[Callable[[str], bool]], object],
    ) -> None:
        self.window = window
        self.refresh_service_factory = refresh_service_factory
        self.login_dialog_factory = login_dialog_factory
        self.current_refresh_service = None

        self.window.refresh_button.clicked.connect(self.refresh_drive)
        self.window.official_login_button.clicked.connect(self.open_official_login)
        self.window.remote_tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        self.window.remote_tree.itemExpanded.connect(self.on_tree_item_expanded)

    def refresh_drive(self) -> None:
        cookie = self.window.cookie_input.text().strip()
        if not cookie:
            self.window.status_label.setText("缺少 Cookie")
            self.window.append_log("[WARN] 请先输入 Cookie 或使用官方登录")
            return

        service = self.refresh_service_factory(cookie)
        result = service.refresh()
        self.current_refresh_service = service
        self.window.cookie_valid = True
        self.window.status_label.setText("已连接")
        self.window.set_account_summary(result.account)
        self.window.populate_remote_tree(result.root_nodes)
        self.window.append_log("[INFO] 网盘信息刷新成功")
        self.window.recompute_start_enabled()

    def open_official_login(self) -> None:
        dialog = self.login_dialog_factory(self.validate_cookie_string)
        accepted = bool(dialog.exec())
        cookie_string = getattr(dialog, "cookie_string", "")
        if accepted and cookie_string:
            self.window.cookie_input.setText(cookie_string)
            self.window.append_log("[INFO] 已获取官方登录 Cookie")

    def validate_cookie_string(self, cookie_string: str) -> bool:
        try:
            service = self.refresh_service_factory(cookie_string)
            service.refresh()
        except Exception:
            return False
        return True

    def on_tree_selection_changed(self) -> None:
        item = self.window.remote_tree.currentItem()
        self.window.remote_folder_id = item.text(1) if item else ""
        self.window.recompute_start_enabled()

    def on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if self.current_refresh_service is None:
            return
        if item.childCount() == 1 and item.child(0).text(0) == "加载中...":
            children = self.current_refresh_service.load_children(item.text(1))
            item.takeChildren()
            for node in children:
                child_item = QTreeWidgetItem([node.name, node.fid])
                child_item.setData(0, 256, node.fid)
                child_item.setData(0, 257, node.parent_fid)
                if node.has_children:
                    child_item.addChild(QTreeWidgetItem(["加载中...", ""]))
                item.addChild(child_item)
