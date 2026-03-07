from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QTreeWidgetItem

from quark_uploader.gui.main_window import MainWindow
from quark_uploader.services.scanner import scan_first_level_subfolders
from quark_uploader.services.upload_workflow import build_upload_plan


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
        self.current_folder_tasks = []
        self.current_upload_plan = None

        self.window.refresh_button.clicked.connect(self.refresh_drive)
        self.window.official_login_button.clicked.connect(self.open_official_login)
        self.window.select_local_folder_button.clicked.connect(self.browse_local_root)
        self.window.start_button.clicked.connect(self.start_upload)
        self.window.remote_tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        self.window.remote_tree.itemExpanded.connect(self.on_tree_item_expanded)

    def browse_local_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self.window, "选择本地文件夹")
        if path:
            self.apply_local_root(path)

    def apply_local_root(self, path: str) -> None:
        tasks = scan_first_level_subfolders(Path(path))
        self.current_folder_tasks = tasks
        self.window.set_local_root(path)
        self.window.populate_task_table(tasks)
        self.window.append_log(f"[INFO] 已扫描 {len(tasks)} 个一级子文件夹")

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

    def start_upload(self) -> None:
        if not self.current_folder_tasks:
            self.window.append_log("[WARN] 当前没有可上传的子文件夹")
            return
        if not self.window.remote_folder_id:
            self.window.append_log("[WARN] 请先选择网盘目标目录")
            return
        self.current_upload_plan = build_upload_plan(self.window.remote_folder_id, self.current_folder_tasks)
        self.window.append_log(
            f"[INFO] 已创建上传计划，共 {len(self.current_upload_plan.jobs)} 个子文件夹任务"
        )
