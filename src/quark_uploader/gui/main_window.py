from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.cookie_valid = False
        self.local_root = ""
        self.remote_folder_id = ""

        self.cookie_input = QLineEdit()
        self.status_label = QLabel("未连接")
        self.start_button = QPushButton("开始上传")
        self.stop_button = QPushButton("停止")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.start_button.setEnabled(False)

        layout = QVBoxLayout()
        layout.addWidget(self.cookie_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.log_output)
        self.setLayout(layout)
        self.setWindowTitle("夸克网盘批量上传分享工具")

    def recompute_start_enabled(self) -> None:
        ready = bool(self.cookie_valid and self.local_root and self.remote_folder_id)
        self.start_button.setEnabled(ready)
