from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quark_uploader.models import AccountSummary, RemoteFolderNode


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.cookie_valid = False
        self.local_root = ""
        self.remote_folder_id = ""

        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText("请粘贴 Cookie，或点击‘官方登录’")
        self.official_login_button = QPushButton("官方登录")
        self.refresh_button = QPushButton("刷新网盘")
        self.status_label = QLabel("未连接")
        self.account_label = QLabel("账号：未加载")
        self.start_button = QPushButton("开始上传")
        self.stop_button = QPushButton("停止")
        self.remote_tree = QTreeWidget()
        self.remote_tree.setHeaderLabels(["网盘目录", "FID"])
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.start_button.setEnabled(False)

        button_row = QHBoxLayout()
        button_row.addWidget(self.official_login_button)
        button_row.addWidget(self.refresh_button)

        layout = QVBoxLayout()
        layout.addWidget(self.cookie_input)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.account_label)
        layout.addWidget(self.remote_tree)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.log_output)
        self.setLayout(layout)
        self.setWindowTitle("夸克网盘批量上传分享工具")

    def recompute_start_enabled(self) -> None:
        ready = bool(self.cookie_valid and self.local_root and self.remote_folder_id)
        self.start_button.setEnabled(ready)

    def set_account_summary(self, summary: AccountSummary) -> None:
        self.account_label.setText(
            f"账号：{summary.nickname or '未知'} | 已用 {summary.used_bytes} / 总量 {summary.total_bytes}"
        )

    def populate_remote_tree(self, nodes: list[RemoteFolderNode]) -> None:
        self.remote_tree.clear()
        for node in nodes:
            item = QTreeWidgetItem([node.name, node.fid])
            item.setData(0, 256, node.fid)
            item.setData(0, 257, node.parent_fid)
            if node.has_children:
                item.addChild(QTreeWidgetItem(["加载中...", ""]))
            self.remote_tree.addTopLevelItem(item)

    def append_log(self, message: str) -> None:
        self.log_output.append(message)
