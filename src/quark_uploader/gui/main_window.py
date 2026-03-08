from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quark_uploader.models import AccountSummary, FolderTask, RemoteFolderNode
from quark_uploader.paths import get_icon_path


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.cookie_valid = False
        self.local_root = ""
        self.remote_folder_id = ""

        self.cookie_input = QLineEdit()
        self.cookie_input.setPlaceholderText("请粘贴 Cookie，或点击‘官方登录’")
        self.official_login_button = QPushButton("官方登录")
        self.remember_cookie_checkbox = QCheckBox("记住 Cookie")
        self.remember_cookie_checkbox.setChecked(True)
        self.refresh_button = QPushButton("刷新网盘")
        self.select_local_folder_button = QPushButton("选择本地文件夹")
        self.open_output_button = QPushButton("打开输出目录")
        self.status_label = QLabel("未连接")
        self.account_label = QLabel("账号：未加载")
        self.local_root_label = QLabel("本地目录：未选择")
        self.progress_summary_label = QLabel("任务进度：0/0，失败 0")
        self.current_action_label = QLabel("当前动作：空闲")
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.start_button = QPushButton("开始上传")
        self.stop_button = QPushButton("停止")
        self.remote_tree = QTreeWidget()
        self.remote_tree.setHeaderLabels(["网盘目录", "FID"])
        self.task_table = QTableWidget(0, 6)
        self.task_table.setHorizontalHeaderLabels(["子文件夹", "文件数", "总大小", "状态", "分享链接", "重试"])
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.start_button.setEnabled(False)

        self.window_title_label = QLabel("夸克网盘批量上传分享工具")
        self.window_title_label.setObjectName("windowTitleLabel")
        self.summary_hint_label = QLabel("连接账号、选择目录并批量执行上传与分享任务")
        self.summary_hint_label.setObjectName("sectionSubtitle")
        self.selected_remote_label = QLabel("当前选择：未选择")
        self.selected_remote_label.setObjectName("selectedRemoteLabel")

        self.summary_card, self.summary_layout, self.summary_card_title = self._create_card(
            "summaryCard", "任务摘要", "当前连接与执行状态"
        )
        self.controls_card, self.controls_layout, self.controls_card_title = self._create_card(
            "controlsCard", "操作区", "连接账号、选择本地目录并控制任务"
        )
        self.remote_card, self.remote_layout, self.remote_section_title = self._create_card(
            "remoteCard", "目标网盘目录", "选择上传目标目录"
        )
        self.task_card, self.task_layout, self.task_section_title = self._create_card(
            "taskCard", "上传任务", "查看每个一级子文件夹的执行状态"
        )
        self.log_card, self.log_layout, self.log_section_title = self._create_card(
            "logCard", "运行日志", "记录刷新、上传、分享与重试信息"
        )
        self.controls_scroll = QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.controls_body = QWidget()
        self.controls_body_layout = QVBoxLayout(self.controls_body)
        self.controls_body_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_body_layout.setSpacing(8)
        self.controls_scroll.setWidget(self.controls_body)

        self._configure_widgets()
        self._build_layout()
        self._apply_styles()

        self.setWindowTitle("夸克网盘批量上传分享工具")
        icon_path = get_icon_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _create_card(self, object_name: str, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
        card = QFrame()
        card.setObjectName(object_name)
        card.setProperty("card", True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("sectionSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return card, layout, title_label

    def _configure_widgets(self) -> None:
        self.setObjectName("rootWidget")
        self.resize(1280, 860)
        self.setMinimumSize(1100, 760)

        self.status_label.setObjectName("statusChip")
        self.status_label.setProperty("state", "idle")
        self.account_label.setObjectName("metaValue")
        self.local_root_label.setObjectName("metaValue")
        self.progress_summary_label.setObjectName("metaValueStrong")
        self.current_action_label.setObjectName("metaValue")

        self.start_button.setObjectName("primaryButton")
        self.stop_button.setObjectName("dangerButton")
        self.refresh_button.setObjectName("secondaryButton")
        self.official_login_button.setObjectName("secondaryButton")
        self.select_local_folder_button.setObjectName("secondaryButton")
        self.open_output_button.setObjectName("secondaryButton")

        self.cookie_input.setClearButtonEnabled(True)
        self.cookie_input.setMinimumHeight(38)

        self.remote_tree.setAlternatingRowColors(True)
        self.remote_tree.setMinimumHeight(260)
        self.remote_tree.setColumnWidth(0, 260)
        self.remote_tree.setRootIsDecorated(True)

        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setMinimumHeight(140)
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)

        self.controls_card.setMinimumWidth(430)
        self.remote_card.setMinimumWidth(520)
        self.remote_tree.setMinimumHeight(220)
        self.log_output.setMinimumHeight(90)
        self.log_output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_output.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))

    def _build_layout(self) -> None:
        summary_top_row = QHBoxLayout()
        summary_top_row.setSpacing(12)
        title_column = QVBoxLayout()
        title_column.setSpacing(4)
        title_column.addWidget(self.window_title_label)
        title_column.addWidget(self.summary_hint_label)
        summary_top_row.addLayout(title_column, 1)
        summary_top_row.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignTop)
        self.summary_layout.addLayout(summary_top_row)

        summary_meta_row = QHBoxLayout()
        summary_meta_row.setSpacing(18)
        summary_meta_row.addWidget(self.account_label, 1)
        summary_meta_row.addWidget(self.current_action_label, 1)
        summary_meta_row.addWidget(self.progress_summary_label, 1)
        self.summary_layout.addLayout(summary_meta_row)
        self.summary_layout.addWidget(self.overall_progress_bar)

        self.controls_layout.addWidget(self.controls_scroll, 1)

        self.controls_body_layout.addWidget(self._create_subsection_label("账号连接"))
        self.controls_body_layout.addWidget(self.cookie_input)
        auth_button_row = QHBoxLayout()
        auth_button_row.setSpacing(10)
        auth_button_row.addWidget(self.official_login_button)
        auth_button_row.addWidget(self.refresh_button)
        self.controls_body_layout.addLayout(auth_button_row)
        self.controls_body_layout.addWidget(self.remember_cookie_checkbox)

        self.controls_body_layout.addSpacing(2)
        self.controls_body_layout.addWidget(self._create_subsection_label("本地与输出"))
        self.controls_body_layout.addWidget(self.local_root_label)
        local_button_column = QVBoxLayout()
        local_button_column.setSpacing(10)
        local_button_column.addWidget(self.select_local_folder_button)
        local_button_column.addWidget(self.open_output_button)
        self.controls_body_layout.addLayout(local_button_column)

        self.controls_body_layout.addSpacing(2)
        self.controls_body_layout.addWidget(self._create_subsection_label("任务控制"))
        action_button_row = QHBoxLayout()
        action_button_row.setSpacing(10)
        action_button_row.addWidget(self.start_button, 1)
        action_button_row.addWidget(self.stop_button, 1)
        self.controls_body_layout.addLayout(action_button_row)
        self.controls_body_layout.addStretch(1)

        self.remote_layout.addWidget(self.selected_remote_label)
        self.remote_layout.addWidget(self.remote_tree, 1)

        self.task_layout.addWidget(self.task_table)
        self.log_layout.addWidget(self.log_output)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)
        self.top_splitter.addWidget(self.controls_card)
        self.top_splitter.addWidget(self.remote_card)
        self.top_splitter.setStretchFactor(0, 0)
        self.top_splitter.setStretchFactor(1, 1)
        self.top_splitter.setSizes([430, 820])

        self.lower_splitter = QSplitter(Qt.Orientation.Vertical)
        self.lower_splitter.setChildrenCollapsible(False)
        self.lower_splitter.addWidget(self.task_card)
        self.lower_splitter.addWidget(self.log_card)
        self.lower_splitter.setStretchFactor(0, 3)
        self.lower_splitter.setStretchFactor(1, 1)
        self.lower_splitter.setSizes([180, 90])

        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setObjectName("contentSplitter")
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.addWidget(self.top_splitter)
        self.content_splitter.addWidget(self.lower_splitter)
        self.content_splitter.setStretchFactor(0, 7)
        self.content_splitter.setStretchFactor(1, 3)
        self.content_splitter.setSizes([560, 160])

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)
        layout.addWidget(self.summary_card)
        layout.addWidget(self.content_splitter, 1)
        self.setLayout(layout)

    def _create_subsection_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("subsectionLabel")
        return label

    def _apply_styles(self) -> None:
        self.setStyleSheet('''
            QWidget#rootWidget {
                background: #f3f6fb;
                color: #1f2937;
            }
            QFrame[card="true"] {
                background: #ffffff;
                border: 1px solid #d8e1ec;
                border-radius: 14px;
            }
            QLabel#windowTitleLabel {
                font-size: 24px;
                font-weight: 700;
                color: #0f172a;
            }
            QLabel#sectionTitle {
                font-size: 16px;
                font-weight: 700;
                color: #0f172a;
            }
            QLabel#sectionSubtitle {
                color: #64748b;
                font-size: 12px;
            }
            QLabel#subsectionLabel {
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                margin-top: 4px;
            }
            QLabel#metaValue {
                color: #334155;
                font-size: 13px;
            }
            QLabel#metaValueStrong {
                color: #0f172a;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#selectedRemoteLabel {
                color: #2563eb;
                font-size: 13px;
                font-weight: 600;
                padding: 4px 0 8px 0;
            }
            QLabel#statusChip {
                padding: 6px 12px;
                border-radius: 12px;
                background: #e2e8f0;
                color: #334155;
                font-weight: 700;
                border: 1px solid #cbd5e1;
            }
            QLabel#statusChip[state="connected"] {
                background: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
            }
            QLabel#statusChip[state="warning"] {
                background: #fff7ed;
                color: #c2410c;
                border: 1px solid #fdba74;
            }
            QLabel#statusChip[state="error"] {
                background: #fef2f2;
                color: #b91c1c;
                border: 1px solid #fca5a5;
            }
            QLineEdit, QTreeWidget, QTableWidget, QTextEdit {
                background: #fbfdff;
                border: 1px solid #cfd8e3;
                border-radius: 10px;
                padding: 6px 8px;
            }
            QTreeWidget, QTableWidget, QTextEdit {
                gridline-color: #e2e8f0;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #334155;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                font-weight: 600;
            }
            QPushButton {
                min-height: 36px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                background: #f8fafc;
                padding: 6px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f1f5f9;
            }
            QPushButton#secondaryButton {
                background: #ffffff;
            }
            QPushButton#primaryButton {
                background: #2563eb;
                color: white;
                border: 1px solid #2563eb;
            }
            QPushButton#primaryButton:hover {
                background: #1d4ed8;
            }
            QPushButton#dangerButton {
                background: #fff7ed;
                color: #b45309;
                border: 1px solid #fdba74;
            }
            QPushButton#dangerButton:hover {
                background: #ffedd5;
            }
            QPushButton:disabled {
                background: #e5e7eb;
                color: #94a3b8;
                border: 1px solid #cbd5e1;
            }
            QProgressBar {
                min-height: 18px;
                border-radius: 9px;
                background: #e2e8f0;
                border: none;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 9px;
                background: #2563eb;
            }
            QCheckBox {
                color: #334155;
            }
        ''')

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

    def set_progress_summary(self, completed: int, total: int, failed: int) -> None:
        self.progress_summary_label.setText(f"任务进度：{completed}/{total}，失败 {failed}")
        self.overall_progress_bar.setValue(0 if total == 0 else int(completed / total * 100))

    def set_current_action(self, text: str) -> None:
        self.current_action_label.setText(text)

    def set_selected_remote_folder(self, path: str | None) -> None:
        self.selected_remote_label.setText(f"当前选择：{path}" if path else "当前选择：未选择")

    def _update_status_chip_style(self, state: str) -> None:
        self.status_label.setProperty("state", state)
        self.style().unpolish(self.status_label)
        self.style().polish(self.status_label)

    def set_connection_state(self, connected: bool, message: str) -> None:
        self.cookie_valid = connected
        self.status_label.setText(message)
        if connected:
            self._update_status_chip_style("connected")
        elif message.startswith("连接失败"):
            self._update_status_chip_style("error")
        else:
            self._update_status_chip_style("warning")
        if not connected:
            self.remote_folder_id = ""
            self.set_selected_remote_folder(None)
        self.recompute_start_enabled()

    def clear_remote_tree(self) -> None:
        self.remote_tree.clear()
        self.set_selected_remote_folder(None)

    def _status_color(self, status: str) -> QColor:
        palette = {
            "skipped": QColor("#64748b"),
            "uploading": QColor("#2563eb"),
            "retrying": QColor("#d97706"),
            "sharing": QColor("#0891b2"),
            "completed": QColor("#15803d"),
            "failed": QColor("#b91c1c"),
            "stopped": QColor("#475569"),
            "pending": QColor("#334155"),
        }
        return palette.get(status, QColor("#334155"))

    def _style_task_row(self, row_index: int, status: str) -> None:
        item = self.task_table.item(row_index, 3)
        if item is not None:
            item.setForeground(self._status_color(status))

    def populate_task_table(self, tasks: list[FolderTask]) -> None:
        self.task_table.setRowCount(len(tasks))
        for row_index, task in enumerate(tasks):
            self.task_table.setItem(row_index, 0, QTableWidgetItem(task.local_name))
            self.task_table.setItem(row_index, 1, QTableWidgetItem(str(task.file_count)))
            self.task_table.setItem(row_index, 2, QTableWidgetItem(str(task.total_size)))
            self.task_table.setItem(row_index, 3, QTableWidgetItem(task.status.value))
            self.task_table.setItem(row_index, 4, QTableWidgetItem(task.share_url or ""))
            self.task_table.setItem(row_index, 5, QTableWidgetItem("0"))
            self._style_task_row(row_index, task.status.value)

    def update_task_status(self, local_name: str, status: str, share_url: str = "", retry_count: int = 0) -> None:
        for row_index in range(self.task_table.rowCount()):
            name_item = self.task_table.item(row_index, 0)
            if name_item and name_item.text() == local_name:
                self.task_table.setItem(row_index, 3, QTableWidgetItem(status))
                self.task_table.setItem(row_index, 5, QTableWidgetItem(str(retry_count)))
                if share_url:
                    self.task_table.setItem(row_index, 4, QTableWidgetItem(share_url))
                self._style_task_row(row_index, status)
                break

    def populate_remote_tree(self, nodes: list[RemoteFolderNode]) -> None:
        self.remote_tree.clear()
        self.set_selected_remote_folder(None)
        for node in nodes:
            item = QTreeWidgetItem([node.name, node.fid])
            item.setData(0, 256, node.fid)
            item.setData(0, 257, node.parent_fid)
            if node.has_children:
                item.addChild(QTreeWidgetItem(["加载中...", ""]))
            self.remote_tree.addTopLevelItem(item)

    def append_log(self, message: str) -> None:
        self.log_output.append(message)
