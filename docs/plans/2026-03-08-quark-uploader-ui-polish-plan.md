# Quark Uploader UI Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the PySide6 desktop UI into a professional desktop-tool style layout while preserving existing upload behavior.

**Architecture:** Keep existing widget instances and controller bindings, but reorganize `MainWindow` into card-based sections with a top summary, dual-pane middle area, task table workspace, and bottom log panel. Use small controller changes only for view text updates.

**Tech Stack:** Python 3.12, PySide6 Widgets, pytest, pytest-qt

---

### Task 1: Add failing GUI structure tests for the new layout

**Files:**
- Modify: `tests/gui/test_main_window.py`
- Modify: `tests/gui/test_local_scan_ui.py`
- Modify: `tests/gui/test_refresh_ui.py`

**Step 1: Write the failing test**
- Assert the window exposes card-like sections for summary, controls, remote tree, task table, and logs.
- Assert the remote selection summary label exists.

**Step 2: Run test to verify it fails**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui\test_main_window.py tests\gui\test_local_scan_ui.py tests\gui\test_refresh_ui.py -q`
Expected: FAIL because the new containers and selection label do not exist yet.

**Step 3: Write minimal implementation**
- Rebuild `MainWindow` layout with reusable section containers and object names.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 2: Rebuild the main window into a professional desktop-tool layout

**Files:**
- Modify: `src/quark_uploader/gui/main_window.py`

**Step 1: Write the failing test**
- Verify the current selection label updates when set.
- Verify task/log/remote areas are placed in dedicated containers.

**Step 2: Run test to verify it fails**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui\test_local_scan_ui.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**
- Add summary header, left control cards, right remote card, task card, and log card.
- Apply QSS styling and header behavior improvements.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 3: Add small controller linkage for remote selection display

**Files:**
- Modify: `src/quark_uploader/gui/controller.py`
- Modify: `tests/gui/test_controller.py`

**Step 1: Write the failing test**
- Assert selecting a remote folder updates the summary label text.

**Step 2: Run test to verify it fails**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui\test_controller.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**
- Add one small view update in `on_tree_selection_changed`.

**Step 4: Run test to verify it passes**

Run: same command as Step 2
Expected: PASS

### Task 4: Full verification

**Files:**
- Modify: `README.md` only if behavior wording needs refresh

**Step 1: Run GUI tests**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest tests\gui -q`
Expected: PASS

**Step 2: Run full suite**

Run: `C:\Users\78221\Desktop\workspace\trae-cn\号池\wangpan\.venv\Scripts\python.exe -m pytest -q`
Expected: PASS
