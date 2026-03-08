# Single Target Upload Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a single-target upload mode that supports uploading one folder recursively or one file directly, while keeping the existing batch-subfolder mode intact.

**Architecture:** Extend the existing task model and upload plan to distinguish file and folder tasks. Keep the old batch scanner unchanged, add a new GUI mode switch and source selection entry points, and reuse the current executor/share pipeline with minimal branching for file tasks.

**Tech Stack:** Python 3.12, PySide6 Widgets, pydantic, pytest, pytest-qt

---

### Task 1: Add failing model and workflow tests for upload mode and task type

**Files:**
- Modify: `tests/test_models.py`
- Modify: `tests/services/test_file_manifest.py`
- Modify: `tests/services/test_upload_workflow.py`

**Step 1: Write the failing test**
- Add tests for upload mode enum, task source type, single file manifest, and single-target upload plan generation.

**Step 2: Run test to verify it fails**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\test_models.py tests\services\test_file_manifest.py tests\services\test_upload_workflow.py -q`
Expected: FAIL because the model and workflow do not support single file/folder tasks yet.

**Step 3: Write minimal implementation**
- Extend task model and manifest / upload workflow to support file and folder sources.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 2: Add failing GUI tests for mode switch and single-target source selection

**Files:**
- Modify: `tests/gui/test_main_window.py`
- Modify: `tests/gui/test_interactions.py`
- Modify: `tests/gui/test_controller.py`
- Modify: `tests/gui/test_controller_local_scan.py`

**Step 1: Write the failing test**
- Add tests that the UI exposes upload mode selection and single file / folder buttons.
- Add tests that controller can build one task from a selected folder or file in single-target mode.

**Step 2: Run test to verify it fails**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui\test_main_window.py tests\gui\test_interactions.py tests\gui\test_controller.py tests\gui\test_controller_local_scan.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**
- Add upload mode controls and single-target source selection handling.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 3: Add failing executor/share tests for file tasks

**Files:**
- Modify: `tests/services/test_upload_executor.py`
- Modify: `tests/services/test_share_service.py`

**Step 1: Write the failing test**
- Add tests that file tasks bypass recursive remote directory planning, upload directly to the selected parent folder, and still return share results.

**Step 2: Run test to verify it fails**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\services\test_upload_executor.py tests\services\test_share_service.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**
- Extend executor and result writing so file tasks are supported without regressing folder tasks.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 4: Full verification

**Files:**
- Modify: `AGENTS.md`

**Step 1: Run GUI tests**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui -q`
Expected: PASS

**Step 2: Run services and full tests**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest -q`
Expected: PASS
