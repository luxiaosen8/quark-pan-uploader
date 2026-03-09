from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QTreeWidgetItem

from quark_uploader.gui.main_window import MainWindow
from quark_uploader.gui.workers import UploadWorker, UploadWorkerHandle
from quark_uploader.models import FolderTaskStatus, UploadMode
from quark_uploader.paths import resolve_runtime_path
from quark_uploader.services.cancellation import UploadCancellationToken
from quark_uploader.services.invoke import (
    call_with_supported_kwargs,
    call_with_supported_positional_args,
)
from quark_uploader.services.remote_cleanup_service import RemoteCleanupService
from quark_uploader.services.result_writer import ResultWriter
from quark_uploader.services.scanner import (
    EMPTY_FOLDER_MESSAGE,
    build_single_target_task,
    scan_first_level_subfolders,
)
from quark_uploader.services.upload_workflow import build_upload_plan
from quark_uploader.settings import AppSettings


class MainWindowController:
    def __init__(
        self,
        window: MainWindow,
        refresh_service_factory: Callable[[str], object],
        login_dialog_factory: Callable[[Callable[[str], bool]], object],
        upload_executor_factory: Callable[[], object] | None = None,
        settings_store=None,
        cleanup_service_factory: Callable[[], object] | None = None,
        use_async_upload: bool = False,
        upload_worker_factory: Callable[[object, object], object] | None = None,
    ) -> None:
        self.window = window
        self.refresh_service_factory = refresh_service_factory
        self.login_dialog_factory = login_dialog_factory
        self.upload_executor_factory = upload_executor_factory
        self.settings_store = settings_store
        self.cleanup_service_factory = cleanup_service_factory
        self.use_async_upload = use_async_upload
        self.upload_worker_factory = upload_worker_factory
        self.current_cancel_token = None
        self.current_upload_handle = None
        self.current_refresh_service = None
        self.current_folder_tasks = []
        self.current_upload_plan = None
        self.current_settings = AppSettings()
        self.current_upload_mode = UploadMode.BATCH_SUBFOLDERS

        self.window.refresh_button.clicked.connect(self.refresh_drive)
        self.window.official_login_button.clicked.connect(self.open_official_login)
        self.window.select_local_folder_button.clicked.connect(self.browse_local_root)
        self.window.select_single_folder_button.clicked.connect(
            self.browse_single_target_folder
        )
        self.window.select_single_file_button.clicked.connect(
            self.browse_single_target_file
        )
        self.window.open_output_button.clicked.connect(self.open_output_directory)
        self.window.start_button.clicked.connect(self.start_upload)
        self.window.stop_button.clicked.connect(self.stop_upload)
        self.window.stop_button.setEnabled(False)
        self.window.remote_tree.itemSelectionChanged.connect(
            self.on_tree_selection_changed
        )
        self.window.upload_mode_batch_button.clicked.connect(
            lambda: self._set_upload_mode(UploadMode.BATCH_SUBFOLDERS)
        )
        self.window.upload_mode_single_button.clicked.connect(
            lambda: self._set_upload_mode(UploadMode.SINGLE_TARGET)
        )
        self._load_settings()
        self.window.remote_tree.itemExpanded.connect(self.on_tree_item_expanded)

    def _load_settings(self) -> None:
        if self.settings_store is None:
            self.current_settings = AppSettings()
            return
        self.current_settings = self.settings_store.load()
        self.window.remember_cookie_checkbox.setChecked(
            self.current_settings.save_cookie
        )
        if self.current_settings.persisted_cookie:
            self.window.cookie_input.setText(self.current_settings.persisted_cookie)
        self.window.set_upload_mode(self.current_upload_mode.value)

    def _persist_settings(self) -> None:
        if self.settings_store is None:
            return
        settings = self.current_settings.model_copy(
            update={
                "save_cookie": self.window.remember_cookie_checkbox.isChecked(),
                "persisted_cookie": self.window.cookie_input.text().strip()
                if self.window.remember_cookie_checkbox.isChecked()
                else "",
            }
        )
        self.settings_store.save(settings)
        self.current_settings = settings

    def _output_dir(self) -> Path:
        return resolve_runtime_path(self.current_settings.output_dir)

    def _clear_local_selection(self) -> None:
        self.current_folder_tasks = []
        self.current_upload_plan = None
        self.window.local_root = ""
        self.window.local_root_label.setText("本地来源：未选择")
        self.window.task_table.setRowCount(0)
        self.window.set_progress_summary(completed=0, total=0, failed=0)
        self.window.recompute_start_enabled()

    def _set_upload_mode(self, mode: UploadMode) -> None:
        if self.current_upload_mode is mode:
            self.window.set_upload_mode(mode.value)
            return
        self.current_upload_mode = mode
        self.window.set_upload_mode(mode.value)
        self._clear_local_selection()

    def browse_local_root(self) -> None:
        path = QFileDialog.getExistingDirectory(self.window, "选择本地文件夹")
        if path:
            self.apply_local_root(path)

    def browse_single_target_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self.window, "选择单个文件夹")
        if path:
            self.apply_single_target(path)

    def browse_single_target_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self.window, "选择单个文件")
        if path:
            self.apply_single_target(path)

    def open_output_directory(self) -> None:
        output_dir = self._output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_dir.resolve()))

    def cleanup_remote_test_directories(self) -> None:
        service = (
            self.cleanup_service_factory()
            if self.cleanup_service_factory is not None
            else None
        )
        if service is None:
            if self.current_refresh_service is None:
                self.window.append_log("[WARN] 请先刷新网盘后再清理测试目录")
                return
            service = RemoteCleanupService(self.current_refresh_service.file_api)
        result = service.cleanup_test_directories()
        self.window.append_log(f"[INFO] 已清理测试目录：{len(result.deleted_names)} 个")

    def apply_local_root(self, path: str) -> None:
        tasks = scan_first_level_subfolders(Path(path))
        self.current_folder_tasks = tasks
        executable_count = sum(1 for task in tasks if task.can_execute)
        skipped_count = len(tasks) - executable_count
        self.window.set_local_root(path)
        self.window.populate_task_table(tasks)
        self.window.set_progress_summary(completed=0, total=executable_count, failed=0)
        self.window.set_current_action("当前动作：等待上传")
        self.window.append_log(f"[INFO] 已扫描 {len(tasks)} 个一级子文件夹")
        self.window.append_log(f"[INFO] 可执行任务 {executable_count} 个")
        for task in tasks:
            if (
                task.status is FolderTaskStatus.SKIPPED
                and task.error_message == EMPTY_FOLDER_MESSAGE
            ):
                self.window.append_log(f"[INFO] 跳过空目录：{task.local_name}")
        if skipped_count:
            self.window.append_log(f"[INFO] 已跳过 {skipped_count} 个空目录")

    def apply_single_target(self, path: str) -> None:
        task = build_single_target_task(Path(path))
        self.current_folder_tasks = [task]
        self.window.set_local_root(path)
        self.window.populate_task_table([task])
        total = 1 if task.can_execute else 0
        self.window.set_progress_summary(completed=0, total=total, failed=0)
        self.window.set_current_action("当前动作：等待上传")
        self.window.append_log(f"[INFO] 已选择单目标上传源：{task.local_name}")
        if (
            task.status is FolderTaskStatus.SKIPPED
            and task.error_message == EMPTY_FOLDER_MESSAGE
        ):
            self.window.append_log(f"[INFO] 跳过空目录：{task.local_name}")

    def refresh_drive(self) -> None:
        cookie = self.window.cookie_input.text().strip()
        if not cookie:
            self.window.set_connection_state(False, "缺少 Cookie")
            self.window.append_log("[WARN] 请先输入 Cookie 或使用官方登录")
            return

        try:
            service = self.refresh_service_factory(cookie)
            result = service.refresh()
        except Exception as exc:
            self.current_refresh_service = None
            self.window.clear_remote_tree()
            self.window.set_connection_state(False, f"连接失败：{exc}")
            self.window.append_log(f"[ERROR] 网盘信息刷新失败：{exc}")
            return

        self.current_refresh_service = service
        self.window.set_connection_state(True, "已连接")
        self.window.set_account_summary(result.account)
        self.window.populate_remote_tree(result.root_nodes)
        self.window.append_log("[INFO] 网盘信息刷新成功")
        self._persist_settings()

    def open_official_login(self) -> None:
        self.window.append_log("[INFO] 正在打开官方登录窗口...")
        try:
            dialog = call_with_supported_positional_args(
                self.login_dialog_factory,
                self.validate_cookie_string,
                self.window,
            )
            if hasattr(dialog, "setWindowTitle"):
                dialog.setWindowTitle(
                    getattr(dialog, "windowTitle", lambda: "官方登录")()
                )
            if hasattr(dialog, "setModal"):
                dialog.setModal(True)
            if hasattr(dialog, "raise_"):
                dialog.raise_()
            if hasattr(dialog, "activateWindow"):
                dialog.activateWindow()
            accepted = bool(dialog.exec())
        except Exception as exc:
            self.window.status_label.setText("官方登录打开失败")
            self.window.append_log(f"[ERROR] 官方登录窗口打开失败：{exc}")
            return
        cookie_string = getattr(dialog, "cookie_string", "")
        if accepted and cookie_string:
            self.window.cookie_input.setText(cookie_string)
            self.window.append_log("[INFO] 已获取官方登录 Cookie")
            self._persist_settings()

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
        self.window.set_selected_remote_folder(self._build_remote_path(item))
        self.window.recompute_start_enabled()

    def _build_remote_path(self, item: QTreeWidgetItem | None) -> str | None:
        if item is None:
            return None
        parts: list[str] = []
        current = item
        while current is not None:
            parts.append(current.text(0))
            current = current.parent()
        return " / ".join(reversed(parts))

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

    def _build_worker_handle(self, plan):
        cancel_token = UploadCancellationToken()
        shared_result_writer = ResultWriter(
            resolve_runtime_path(self.current_settings.output_dir)
        )
        if self.upload_worker_factory is not None:
            handle = self.upload_worker_factory(plan, self.upload_executor_factory)
            self.current_cancel_token = cancel_token
            return handle
        worker = UploadWorker(
            plan=plan,
            executor_factory=self.upload_executor_factory,
            cancel_token=cancel_token,
            job_concurrency=self.current_settings.job_concurrency,
            ui_update_interval_ms=self.current_settings.ui_update_interval_ms,
            shared_result_writer=shared_result_writer,
        )
        handle = UploadWorkerHandle(worker)
        worker.task_status.connect(self.window.update_task_status)
        worker.progress_summary.connect(self.window.set_progress_summary)
        worker.current_action.connect(self.window.set_current_action)
        worker.log_message.connect(self.window.append_log)
        worker.run_finished.connect(self._on_upload_run_finished)
        self.current_cancel_token = cancel_token
        return handle

    def _on_upload_run_finished(self, final_state: str) -> None:
        self.window.stop_button.setEnabled(False)
        self.window.start_button.setEnabled(True)
        if hasattr(self.window, "set_upload_busy_state"):
            self.window.set_upload_busy_state(False)
        self.current_upload_handle = None
        self.current_cancel_token = None
        if final_state == "stopped":
            self.window.append_log("[WARN] 上传已停止")
        elif final_state == "completed_with_errors":
            self.window.append_log("[WARN] 上传已完成，但存在失败任务")

    def stop_upload(self) -> None:
        if self.current_upload_handle is None:
            self.window.append_log("[WARN] 当前没有正在执行的上传任务")
            return
        self.window.append_log("[WARN] 用户请求停止上传")
        self.window.set_current_action("当前动作：正在停止...")
        if hasattr(self.window, "set_upload_busy_state"):
            self.window.set_upload_busy_state(True, stopping=True)
        if hasattr(self.current_upload_handle, "request_stop"):
            self.current_upload_handle.request_stop()
        elif self.current_cancel_token is not None:
            self.current_cancel_token.request_stop()
        self.window.stop_button.setEnabled(False)

    def start_upload(self) -> None:
        executable_count = sum(
            1 for task in self.current_folder_tasks if task.can_execute
        )
        if executable_count == 0:
            warn_message = (
                "[WARN] 当前没有可上传的子文件夹"
                if self.current_upload_mode is UploadMode.BATCH_SUBFOLDERS
                else "[WARN] 当前没有可上传的单目标"
            )
            self.window.append_log(warn_message)
            return
        if not self.window.remote_folder_id:
            self.window.append_log("[WARN] 请先选择网盘目标目录")
            return
        self.current_upload_plan = build_upload_plan(
            self.window.remote_folder_id, self.current_folder_tasks
        )
        total = len(self.current_upload_plan.jobs)
        if total == 0:
            warn_message = (
                "[WARN] 当前没有可上传的子文件夹"
                if self.current_upload_mode is UploadMode.BATCH_SUBFOLDERS
                else "[WARN] 当前没有可上传的单目标"
            )
            self.window.append_log(warn_message)
            return
        for job in self.current_upload_plan.jobs:
            self.window.update_task_status(
                job.local_name, FolderTaskStatus.UPLOADING.value
            )
        self.window.set_progress_summary(completed=0, total=total, failed=0)
        if self.current_upload_mode is UploadMode.BATCH_SUBFOLDERS:
            self.window.append_log(
                f"[INFO] 已创建上传计划，共 {len(self.current_upload_plan.jobs)} 个子文件夹任务"
            )
        else:
            self.window.append_log(
                f"[INFO] 已创建上传计划，共 {len(self.current_upload_plan.jobs)} 个单目标任务"
            )
        self.window.start_button.setEnabled(False)
        self.window.stop_button.setEnabled(True)
        if hasattr(self.window, "set_upload_busy_state"):
            self.window.set_upload_busy_state(True)
        if self.upload_executor_factory is None:
            return
        if self.use_async_upload:
            self.current_upload_handle = self._build_worker_handle(
                self.current_upload_plan
            )
            self.current_upload_handle.start()
            return

        executor = self.upload_executor_factory()
        failed = 0
        completed = 0
        for job in self.current_upload_plan.jobs:
            self.window.set_current_action(f"当前任务：{job.local_name}")
            status_callback = (
                lambda status,
                share_url="",
                retry_count=0,
                local_name=job.local_name: self.window.update_task_status(
                    local_name,
                    status,
                    share_url,
                    retry_count,
                )
            )
            try:
                result = call_with_supported_kwargs(
                    executor.execute_job, job, status_callback=status_callback
                )
            except Exception as exc:
                failed += 1
                self.window.update_task_status(
                    job.local_name, FolderTaskStatus.FAILED.value
                )
                self.window.append_log(f"[ERROR] 上传失败：{job.local_name} -> {exc}")
                self.window.set_progress_summary(
                    completed=completed, total=total, failed=failed
                )
                continue
            completed += 1
            self.window.update_task_status(
                job.local_name,
                getattr(result, "status", FolderTaskStatus.COMPLETED.value),
                getattr(result, "share_url", ""),
                retry_count=getattr(result, "retry_count", 0),
            )
            self.window.append_log(
                f"[INFO] 上传骨架执行完成：{job.local_name} ({result.uploaded_files} 文件)"
            )
            if getattr(result, "share_url", ""):
                self.window.append_log(f"[INFO] 分享链接：{result.share_url}")
            self.window.set_progress_summary(
                completed=completed, total=total, failed=failed
            )
        self.window.set_current_action("当前动作：空闲")
        self.window.stop_button.setEnabled(False)
        self.window.start_button.setEnabled(True)
        if failed:
            self.window.append_log("[WARN] 上传已完成，但存在失败任务")
