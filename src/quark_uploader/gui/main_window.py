from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quark_uploader.models import AccountSummary, FolderTask, RemoteFolderNode


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
        self.select_local_folder_button = QPushButton("选择本地文件夹")
        self.status_label = QLabel("未连接")
        self.account_label = QLabel("账号：未加载")
        self.local_root_label = QLabel("本地目录：未选择")
        self.start_button = QPushButton("开始上传")
        self.stop_button = QPushButton("停止")
        self.remote_tree = QTreeWidget()
        self.remote_tree.setHeaderLabels(["网盘目录", "FID"])
        self.task_table = QTableWidget(0, 5)
        self.task_table.setHorizontalHeaderLabels(["子文件夹", "文件数", "总大小", "状态", "分享链接"])
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.start_button.setEnabled(False)

        auth_button_row = QHBoxLayout()
        auth_button_row.addWidget(self.official_login_button)
        auth_button_row.addWidget(self.refresh_button)

        local_button_row = QHBoxLayout()
        local_button_row.addWidget(self.select_local_folder_button)

        layout = QVBoxLayout()
        layout.addWidget(self.cookie_input)
        layout.addLayout(auth_button_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.account_label)
        layout.addWidget(self.local_root_label)
        layout.addLayout(local_button_row)
        layout.addWidget(self.task_table)
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

    def set_local_root(self, path: str) -> None:
        self.local_root = path
        self.local_root_label.setText(f"本地目录：{path}")
        self.recompute_start_enabled()

    def populate_task_table(self, tasks: list[FolderTask]) -> None:
        self.task_table.setRowCount(len(tasks))
        for row_index, task in enumerate(tasks):
            self.task_table.setItem(row_index, 0, QTableWidgetItem(task.local_name))
            self.task_table.setItem(row_index, 1, QTableWidgetItem(str(task.file_count)))
            self.task_table.setItem(row_index, 2, QTableWidgetItem(str(task.total_size)))
            self.task_table.setItem(row_index, 3, QTableWidgetItem(task.status.value))
            self.task_table.setItem(row_index, 4, QTableWidgetItem(task.share_url or ""))

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
