# Quark Pan Uploader Share Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Windows desktop GUI app that uploads each first-level local subfolder into a chosen Quark drive folder, creates a share for each uploaded remote folder, and appends share URLs to a local text file.

**Architecture:** Use a thin `PySide6` GUI over a service layer that coordinates scanning, uploading, sharing, and persistence. Keep all Quark HTTP behavior inside dedicated client modules so reverse-engineered API changes stay isolated from the GUI and task engine.

**Tech Stack:** Python 3.12+, PySide6, requests, pydantic, pytest, pytest-qt, pyinstaller

---

### Task 1: Bootstrap project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/quark_uploader/__init__.py`
- Create: `src/quark_uploader/main.py`
- Create: `src/quark_uploader/app.py`
- Create: `tests/test_smoke_import.py`

**Step 1: Write the failing test**

```python
from quark_uploader.app import create_app


def test_create_app_returns_qapplication(qtbot):
    app = create_app()
    assert app is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_smoke_import.py -v`
Expected: FAIL with import error because package files do not exist yet.

**Step 3: Write minimal implementation**

```python
# src/quark_uploader/app.py
from PySide6.QtWidgets import QApplication


def create_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_smoke_import.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml README.md src/quark_uploader tests/test_smoke_import.py
git commit -m "chore: bootstrap quark uploader project"
```

### Task 2: Define typed domain models and settings

**Files:**
- Create: `src/quark_uploader/models.py`
- Create: `src/quark_uploader/settings.py`
- Create: `tests/test_models.py`

**Step 1: Write the failing test**

```python
from quark_uploader.models import FolderTask, FolderTaskStatus


def test_folder_task_defaults_to_pending_status():
    task = FolderTask(local_name="demo", local_path="C:/demo")
    assert task.status is FolderTaskStatus.PENDING
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL because models are missing.

**Step 3: Write minimal implementation**

```python
from enum import Enum
from pydantic import BaseModel


class FolderTaskStatus(str, Enum):
    PENDING = "pending"


class FolderTask(BaseModel):
    local_name: str
    local_path: str
    status: FolderTaskStatus = FolderTaskStatus.PENDING
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/models.py src/quark_uploader/settings.py tests/test_models.py
git commit -m "feat: add typed models and settings"
```

### Task 3: Build file-system scanner for first-level subfolders

**Files:**
- Create: `src/quark_uploader/services/scanner.py`
- Create: `tests/services/test_scanner.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from quark_uploader.services.scanner import scan_first_level_subfolders


def test_scan_first_level_subfolders_ignores_root_files(tmp_path: Path):
    (tmp_path / "root.txt").write_text("x", encoding="utf-8")
    lesson = tmp_path / "lesson-a"
    lesson.mkdir()
    (lesson / "video.mp4").write_text("x", encoding="utf-8")

    tasks = scan_first_level_subfolders(tmp_path)

    assert [task.local_name for task in tasks] == ["lesson-a"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_scanner.py -v`
Expected: FAIL because scanner module is missing.

**Step 3: Write minimal implementation**

```python
from pathlib import Path

from quark_uploader.models import FolderTask


def scan_first_level_subfolders(root: Path) -> list[FolderTask]:
    tasks = []
    for entry in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if entry.is_dir():
            tasks.append(FolderTask(local_name=entry.name, local_path=str(entry)))
    return tasks
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_scanner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/services/scanner.py tests/services/test_scanner.py
git commit -m "feat: add first-level folder scanner"
```

### Task 4: Add result writers and structured logging

**Files:**
- Create: `src/quark_uploader/services/result_writer.py`
- Create: `src/quark_uploader/services/logger.py`
- Create: `tests/services/test_result_writer.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from quark_uploader.services.result_writer import ResultWriter


def test_result_writer_appends_urls_line_by_line(tmp_path: Path):
    writer = ResultWriter(tmp_path)
    writer.append_share_url("https://example.com/a")
    writer.append_share_url("https://example.com/b")

    content = (tmp_path / "share_links.txt").read_text(encoding="utf-8").splitlines()
    assert content == ["https://example.com/a", "https://example.com/b"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_result_writer.py -v`
Expected: FAIL because writer module is missing.

**Step 3: Write minimal implementation**

```python
from pathlib import Path


class ResultWriter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.share_links_path = self.output_dir / "share_links.txt"

    def append_share_url(self, url: str) -> None:
        with self.share_links_path.open("a", encoding="utf-8") as handle:
            handle.write(url + "\n")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_result_writer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/services/result_writer.py src/quark_uploader/services/logger.py tests/services/test_result_writer.py
git commit -m "feat: add output writers and logging"
```

### Task 5: Implement shared HTTP session and request helpers

**Files:**
- Create: `src/quark_uploader/quark/session.py`
- Create: `tests/quark/test_session.py`

**Step 1: Write the failing test**

```python
from quark_uploader.quark.session import build_cookie_headers


def test_build_cookie_headers_includes_cookie_header():
    headers = build_cookie_headers("sid=123")
    assert headers["Cookie"] == "sid=123"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/quark/test_session.py -v`
Expected: FAIL because session helper is missing.

**Step 3: Write minimal implementation**

```python
def build_cookie_headers(cookie: str) -> dict[str, str]:
    return {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/quark/test_session.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/quark/session.py tests/quark/test_session.py
git commit -m "feat: add quark session helpers"
```

### Task 6: Implement user and file APIs for refresh flow

**Files:**
- Create: `src/quark_uploader/quark/user_api.py`
- Create: `src/quark_uploader/quark/file_api.py`
- Create: `tests/quark/test_user_api.py`
- Create: `tests/quark/test_file_api.py`

**Step 1: Write the failing test**

```python
from quark_uploader.quark.file_api import build_sort_params


def test_build_sort_params_uses_expected_parent_id():
    params = build_sort_params("root-fid")
    assert params["pdir_fid"] == "root-fid"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/quark/test_file_api.py -v`
Expected: FAIL because file API module is missing.

**Step 3: Write minimal implementation**

```python
def build_sort_params(parent_fid: str) -> dict[str, str | int]:
    return {
        "pr": "ucpro",
        "fr": "pc",
        "uc_param_str": "",
        "pdir_fid": parent_fid,
        "_page": 1,
        "_size": 50,
        "_fetch_total": 1,
        "_fetch_sub_dirs": 1,
        "_sort": "file_type:asc,updated_at:desc",
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/quark/test_file_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/quark/user_api.py src/quark_uploader/quark/file_api.py tests/quark/test_user_api.py tests/quark/test_file_api.py
git commit -m "feat: add refresh flow APIs"
```

### Task 7: Implement remote folder resolution and creation logic

**Files:**
- Create: `src/quark_uploader/services/remote_paths.py`
- Create: `tests/services/test_remote_paths.py`

**Step 1: Write the failing test**

```python
from quark_uploader.services.remote_paths import split_relative_parts


def test_split_relative_parts_normalizes_nested_paths():
    assert split_relative_parts("chapter1/video/part1.mp4") == ["chapter1", "video"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_remote_paths.py -v`
Expected: FAIL because remote path helper is missing.

**Step 3: Write minimal implementation**

```python
from pathlib import PurePosixPath


def split_relative_parts(relative_file_path: str) -> list[str]:
    path = PurePosixPath(relative_file_path)
    return list(path.parts[:-1])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_remote_paths.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/services/remote_paths.py tests/services/test_remote_paths.py
git commit -m "feat: add remote path helpers"
```

### Task 8: Implement upload API abstractions and upload strategy state machine

**Files:**
- Create: `src/quark_uploader/quark/upload_api.py`
- Create: `src/quark_uploader/services/upload_strategy.py`
- Create: `tests/quark/test_upload_api.py`
- Create: `tests/services/test_upload_strategy.py`

**Step 1: Write the failing test**

```python
from quark_uploader.services.upload_strategy import decide_upload_mode


def test_decide_upload_mode_returns_instant_when_preupload_hits():
    mode = decide_upload_mode({"rapid_upload": True})
    assert mode == "instant"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_upload_strategy.py -v`
Expected: FAIL because upload strategy module is missing.

**Step 3: Write minimal implementation**

```python
def decide_upload_mode(preupload_data: dict) -> str:
    if preupload_data.get("rapid_upload"):
        return "instant"
    if preupload_data.get("multipart"):
        return "multipart"
    return "single"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_upload_strategy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/quark/upload_api.py src/quark_uploader/services/upload_strategy.py tests/quark/test_upload_api.py tests/services/test_upload_strategy.py
git commit -m "feat: add upload strategy abstractions"
```

### Task 9: Implement share API and share policy handling

**Files:**
- Create: `src/quark_uploader/quark/share_api.py`
- Create: `src/quark_uploader/services/share_policy.py`
- Create: `tests/quark/test_share_api.py`
- Create: `tests/services/test_share_policy.py`

**Step 1: Write the failing test**

```python
from quark_uploader.services.share_policy import build_share_payload


def test_build_share_payload_uses_folder_id_and_title():
    payload = build_share_payload(fid="abc", title="lesson-a")
    assert payload["fid_list"] == ["abc"]
    assert payload["title"] == "lesson-a"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_share_policy.py -v`
Expected: FAIL because share policy module is missing.

**Step 3: Write minimal implementation**

```python
def build_share_payload(fid: str, title: str) -> dict:
    return {
        "fid_list": [fid],
        "title": title,
        "url_type": 2,
        "expired_type": 1,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_share_policy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/quark/share_api.py src/quark_uploader/services/share_policy.py tests/quark/test_share_api.py tests/services/test_share_policy.py
git commit -m "feat: add share API and policy layer"
```

### Task 10: Implement coordinator for folder upload-share workflow

**Files:**
- Create: `src/quark_uploader/services/coordinator.py`
- Create: `tests/services/test_coordinator.py`

**Step 1: Write the failing test**

```python
from quark_uploader.models import FolderTask, FolderTaskStatus
from quark_uploader.services.coordinator import mark_share_success


def test_mark_share_success_updates_status_and_url():
    task = FolderTask(local_name="lesson-a", local_path="C:/lesson-a")
    mark_share_success(task, "https://example.com/share")
    assert task.status is FolderTaskStatus.COMPLETED
    assert task.share_url == "https://example.com/share"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_coordinator.py -v`
Expected: FAIL because coordinator module or completed status is missing.

**Step 3: Write minimal implementation**

```python
from quark_uploader.models import FolderTask, FolderTaskStatus


def mark_share_success(task: FolderTask, share_url: str) -> None:
    task.status = FolderTaskStatus.COMPLETED
    task.share_url = share_url
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_coordinator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/services/coordinator.py tests/services/test_coordinator.py
git commit -m "feat: add upload-share coordinator core"
```

### Task 11: Build worker thread and signal bridge for responsive GUI

**Files:**
- Create: `src/quark_uploader/gui/workers.py`
- Create: `tests/gui/test_workers.py`

**Step 1: Write the failing test**

```python
from quark_uploader.gui.workers import WorkerState


def test_worker_state_defaults_to_idle():
    state = WorkerState()
    assert state.running is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/gui/test_workers.py -v`
Expected: FAIL because workers module is missing.

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass


@dataclass
class WorkerState:
    running: bool = False
    stop_requested: bool = False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/gui/test_workers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/gui/workers.py tests/gui/test_workers.py
git commit -m "feat: add GUI worker infrastructure"
```

### Task 12: Build main window widgets and interactions

**Files:**
- Create: `src/quark_uploader/gui/main_window.py`
- Create: `src/quark_uploader/gui/models.py`
- Create: `tests/gui/test_main_window.py`
- Modify: `src/quark_uploader/app.py`
- Modify: `src/quark_uploader/main.py`

**Step 1: Write the failing test**

```python
from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_main_window_has_start_button(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.start_button.text() == "开始上传"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/gui/test_main_window.py -v`
Expected: FAIL because main window is missing.

**Step 3: Write minimal implementation**

```python
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.start_button = QPushButton("开始上传")
        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        self.setLayout(layout)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/gui/test_main_window.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/gui/main_window.py src/quark_uploader/gui/models.py src/quark_uploader/app.py src/quark_uploader/main.py tests/gui/test_main_window.py
git commit -m "feat: add main window shell"
```

### Task 13: Wire refresh, scan, start, stop, and log updates into the GUI

**Files:**
- Modify: `src/quark_uploader/gui/main_window.py`
- Modify: `src/quark_uploader/gui/workers.py`
- Modify: `src/quark_uploader/services/coordinator.py`
- Create: `tests/gui/test_interactions.py`

**Step 1: Write the failing test**

```python
from quark_uploader.app import create_app
from quark_uploader.gui.main_window import MainWindow


def test_start_button_disabled_until_required_inputs_selected(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.start_button.isEnabled() is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/gui/test_interactions.py -v`
Expected: FAIL because validation logic is missing.

**Step 3: Write minimal implementation**

```python
def recompute_start_enabled(self) -> None:
    ready = bool(self.cookie_valid and self.local_root and self.remote_folder_id)
    self.start_button.setEnabled(ready)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/gui/test_interactions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/quark_uploader/gui/main_window.py src/quark_uploader/gui/workers.py src/quark_uploader/services/coordinator.py tests/gui/test_interactions.py
git commit -m "feat: wire GUI interactions and validation"
```

### Task 14: Add packaging, sample config, and user docs

**Files:**
- Modify: `README.md`
- Create: `scripts/build_windows.ps1`
- Create: `quark_uploader.spec`
- Create: `.gitignore`

**Step 1: Write the failing test**

No automated test required. Verify documentation and packaging scripts manually.

**Step 2: Run manual check to verify it fails**

Run: `pyinstaller --version`
Expected: If missing, install dependency first.

**Step 3: Write minimal implementation**

```powershell
python -m PyInstaller quark_uploader.spec --noconfirm
```

**Step 4: Run manual check to verify it passes**

Run: `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`
Expected: A Windows executable is produced under `dist/`.

**Step 5: Commit**

```bash
git add README.md scripts/build_windows.ps1 quark_uploader.spec .gitignore
git commit -m "docs: add packaging and usage instructions"
```

### Task 15: Run focused and full verification

**Files:**
- Modify: `README.md`

**Step 1: Run focused tests**

Run: `pytest tests/services -v`
Expected: PASS

**Step 2: Run Quark API unit tests**

Run: `pytest tests/quark -v`
Expected: PASS

**Step 3: Run GUI tests**

Run: `pytest tests/gui -v`
Expected: PASS

**Step 4: Run full test suite**

Run: `pytest -v`
Expected: PASS

**Step 5: Smoke test the app manually**

Run: `python -m quark_uploader.main`
Expected: Main window opens, refresh works with a valid Cookie, local scan populates the grid, and successful mock/manual flow appends links to `output/share_links.txt`.

**Step 6: Commit**

```bash
git add README.md
git commit -m "test: verify quark uploader workflow"
```
